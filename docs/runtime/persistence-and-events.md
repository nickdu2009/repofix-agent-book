# PostgreSQL、故障恢复与 SSE

数据库不仅保存最终状态，还要保证状态、事件和恢复决策可以重放。

## 本章契约

- **前置**：内存 Repository 的 Fake 全栈闭环已通过。
- **产物**：迁移、PostgreSQL Repository、Outbox/SSE、lease 故障处理器。
- **验收**：控制平面重启后保留所有事实；v1 对无法安全续跑的进行中 Run 明确置为失败并清理 Sandbox，不重复模型或工具动作。

!!! warning "设计蓝图"
    当前 DDL 和协议用于下一 Checkpoint 的实现审查；仓库尚无 PostgreSQL migration、Repository Adapter 或 SSE Server。只有 SQL 能在空库 migration 测试中执行、重放测试通过后，本章才算可运行。

## 最小表结构

```sql
create table tasks (
  id text primary key,
  repository_url text not null,
  issue_text text not null,
  created_at timestamptz not null default now()
);

create table runs (
  id text primary key,
  task_id text not null references tasks(id),
  retry_of_run_id text references runs(id),
  status text not null check (status in (
    'pending','provisioning','running','succeeded','failed','cancelled','timed_out'
  )),
  version bigint not null default 1,
  failure_code text,
  worker_id text,
  lease_expires_at timestamptz,
  cancel_requested_at timestamptz,
  sandbox_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table run_events (
  id text primary key,
  run_id text not null references runs(id),
  sequence bigint not null,
  type text not null check (type in (
    'run.started','sandbox.created','sandbox.deleted','sandbox.cleanup_failed','step.started',
    'tool.started','tool.completed','tests.completed','patch.created',
    'run.succeeded','run.failed','run.cancelled','run.timed_out'
  )),
  schema_version integer not null check (schema_version = 1),
  data jsonb not null,
  occurred_at timestamptz not null default now(),
  unique (run_id, sequence)
);

create table steps (
  id text primary key,
  run_id text not null references runs(id),
  number integer not null check (number > 0),
  tool_name text not null,
  arguments jsonb not null,
  result jsonb not null,
  workspace_revision bigint not null,
  created_at timestamptz not null default now(),
  unique (run_id, number)
);

create table artifacts (
  id text primary key,
  run_id text not null references runs(id),
  kind text not null check (kind in ('patch','test_report','log','trace')),
  content_type text not null,
  size_bytes bigint not null check (size_bytes >= 0),
  sha256 char(64) not null,
  storage_key text not null,
  created_at timestamptz not null default now()
);

create index runs_recovery_idx
  on runs (lease_expires_at)
  where status in ('provisioning','running');
```

这段 `up` migration 可以在空数据库执行；`down` migration 必须按 `artifacts → steps → run_events → runs → tasks` 的逆依赖顺序删除。默认不保存完整源文件、Secret 或无限日志，`arguments` 和 `result` 写入前仍要脱敏与截断。

## 事务边界

状态转换和对应事件必须在同一事务中：

1. `SELECT ... FOR UPDATE` 或带版本的条件更新。
2. 校验状态转换。
3. 更新 Run 和 `version`。
4. 插入下一 `sequence` 的事件。
5. 提交后通知 SSE broadcaster。

如果通知丢失，SSE 客户端仍可从 `run_events` 重放，因此数据库事件表是事实来源。

## Lease 与 v1 故障策略

Python v1 在一次长请求的内存中持有模型 history 和 AgentState，数据库中的 Step 摘要不足以精确续跑。因此 v1 采用 **fail-and-retry**，不声称从任意 Step 原地恢复。Worker 领取 Run 时写入 `worker_id` 和短 lease，并定期续租。服务重启后：

1. 查询 lease 已过期且非终态的 Run。
2. 通过条件更新抢占故障处理权，避免两个 Worker 同时处理。
3. 若 Run 尚未开始任何外部动作，可重新排队；否则标记为 `failed`，错误码为 `worker_lost`。
4. 查询并删除已记录的 `sandbox_id`，保存清理结果。
5. 写入唯一终态事件；用户需要继续时创建新的 Run，并记录 `retry_of_run_id`。

无法证明幂等的外部动作绝不自动重放。未来只有在持久化完整模型 history、Agent checkpoint、tool call ID 和幂等结果后，才能单独设计“原地续跑”版本。

## SSE 重放协议

第一版发送未命名 message：

```text
id: 42
data: {"id":"evt_...","run_id":"run_...","sequence":42,"type":"tool.completed",...}

```

客户端重连时浏览器发送 `Last-Event-ID: 42`。服务端流程：

1. 在事务快照中读取 `sequence > 42` 的历史事件。
2. 注册实时订阅。
3. 再读取一次注册期间产生的缺口并按序发送。
4. 定期发送注释心跳 `: keep-alive`。
5. 终态事件发出后关闭连接；客户端再 GET Run 快照确认。

Reducer 根据 `sequence` 去重。不得用“先查历史、再订阅”且没有缺口检查的实现，否则会丢事件。

## 测试矩阵

| 测试 | 证明什么 |
| --- | --- |
| 状态与事件事务回滚 | 不出现无事件状态或幽灵事件 |
| 两个 Worker 抢同一 Run | 只有一个 Claim 成功 |
| `Last-Event-ID` 重连 | 不丢失、不重复应用事件 |
| 服务在 tool.completed 后退出 | 原 Run 明确失败、Sandbox 被清理且工具不重放 |
| 慢客户端 | 不阻塞 Run 执行，超限后断开并允许重放 |

## 故障排查与验收

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 页面偶尔少一个 Step | 历史与实时订阅间有竞态 | 注册后补读缺口 |
| 重启后重复执行命令 | 故障处理器错误地重放内存 Loop | v1 标记原 Run 失败并新建重试 Run，不自动重放 |
| 多实例只能收到本机事件 | 使用内存 broadcaster | 用数据库轮询、LISTEN/NOTIFY 或专用消息层唤醒 |

验收命令应包含迁移测试、Repository 集成测试和“杀进程后明确失败并清理”场景；清单中的每一项都链接到具体测试文件。
