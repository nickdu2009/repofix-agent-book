# 第 12 章 · PostgreSQL、故障恢复与 SSE

数据库不仅保存最终状态，还要保证状态、事件和恢复决策可以重放。

## 快速开始

| 入口 | 内容 |
| --- | --- |
| Codespaces | [打开 RepoFix 通用工作区](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json) |
| 只读骨架 | `examples/repofix/labs/chapter-12/start/` |
| 准备工作副本 | `make chapter-prepare CHAPTER=chapter-12` |
| 工作副本 | `.work/chapter-12/` |
| 结构检查 | `make chapter-check CHAPTER=chapter-12` |
| 复盘参考 | `examples/repofix/labs/chapter-12/solution/` |

在 Codespaces 终端进入 `examples/repofix`，先运行 `chapter-prepare`，再只在 `.work/chapter-12/` 完成 TODO，最后运行 `chapter-check`。`start/` 始终只读；只有通过验收并记录自己的取舍后才用 `solution/` 复盘，不要从参考实现开始复制。

!!! warning "设计蓝图：尚无完整实现"
    当前仓库没有 PostgreSQL migration、Repository Adapter 或 SSE Server；本章参考实现只用于下一 Checkpoint 的设计审查。

## 本章契约

- **前置**：内存 Repository 的 Fake 全栈闭环已通过。
- **产物**：迁移、PostgreSQL Repository、Outbox/SSE、lease 故障处理器。
- **验收**：控制平面重启后保留所有事实；v1 对无法安全续跑的进行中 Run 明确置为失败并清理 Sandbox，不重复模型或工具动作。

## 最小表结构

```sql
create table runs (
  id text primary key,
  status text not null check (status in (
    'pending','provisioning','running','succeeded','failed','cancelled','timed_out'
  )),
  version bigint not null default 1,
  worker_id text,
  lease_expires_at timestamptz,
  sandbox_id text
);

create table run_events (
  id text primary key,
  run_id text not null references runs(id),
  sequence bigint not null check (sequence > 0),
  type text not null,
  data jsonb not null,
  occurred_at timestamptz not null default now(),
  unique (run_id, sequence)
);

create index runs_recovery_idx
  on runs (lease_expires_at)
  where status in ('provisioning','running');
```

这是用于解释约束的关键片段，不是可执行的完整 migration。完整设计还需要：`tasks` 保存仓库与 Issue；`steps` 保存工具参数、结果和 revision；`artifacts` 只保存 patch、测试报告、日志和 trace 的元数据。状态与事件字面量必须来自[共享契约源码](https://github.com/nickdu2009/repofix-agent-book/tree/main/examples/repofix/contracts)，不要在 SQL 中另造一套。

在 `.work/chapter-12/` 中完成 `up` 与 `down` migration；删除顺序必须是 `artifacts → steps → run_events → runs → tasks`。默认不保存完整源文件、Secret 或无限日志，`arguments` 和 `result` 写入前仍要脱敏与截断。完成后用空数据库迁移测试验证，而不是把本页片段直接复制成“参考实现”。

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
