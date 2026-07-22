# 第 08 章 · 跨语言共享契约

Python、Go 和 TypeScript 不应分别手写三套 **Wire RunStatus 与 RunEvent**。伴随代码在 `examples/repofix/contracts/` 保存机器可验证的 JSON Schema。Python 内部 `AgentStatus.CANDIDATE_READY` 是不同领域概念，绝不能序列化成最终 Run `succeeded`。

## 快速开始

| 入口 | 内容 |
| --- | --- |
| Codespaces | [打开 RepoFix 通用工作区](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json) |
| 只读骨架 | `examples/repofix/labs/chapter-08/start/` |
| 准备工作副本 | `make chapter-prepare CHAPTER=chapter-08` |
| 工作副本 | `.work/chapter-08/` |
| 结构检查 | `make chapter-check CHAPTER=chapter-08` |
| 复盘参考 | `examples/repofix/labs/chapter-08/solution/` |

在 Codespaces 终端进入 `examples/repofix`，先运行 `chapter-prepare`，再只在 `.work/chapter-08/` 完成 TODO，最后运行 `chapter-check`。`start/` 始终只读；只有通过验收并记录自己的取舍后才用 `solution/` 复盘，不要从参考实现开始复制。

## 本章契约

- **前置**：阅读运行时架构决策。
- **产物**：Run、Event、Error、Artifact、Tool Call 和 Tool Result Schema。
- **验收**：三种语言使用相同 JSON 字面量，非法事件在进入领域层前被拒绝。

## Run 状态

```text
pending → provisioning → running → succeeded
                             ├──→ failed
                             ├──→ cancelled
                             └──→ timed_out
```

`testing` 不作为 Run 状态。测试属于 `tool.started`、`tool.completed` 或 `tests.completed` 事件，避免状态机在每次测试前后往返。

清理事件也使用精确语义：`sandbox.deleted` 只表示删除成功，`sandbox.cleanup_failed` 表示删除尝试失败；两者都必须先于唯一终态事件。

统一状态值：

```json
["pending", "provisioning", "running", "succeeded", "failed", "cancelled", "timed_out"]
```

## 事件信封

所有 SSE 数据使用同一信封：

```json
{
  "id": "evt_01J...",
  "run_id": "run_01J...",
  "sequence": 12,
  "type": "tool.completed",
  "occurred_at": "2026-07-17T10:00:00Z",
  "schema_version": 1,
  "data": {
    "step_number": 4,
    "tool_name": "run_tests",
    "ok": true
  }
}
```

第一版使用未命名 SSE message，事件类型只存在于 JSON 的 `type` 字段：

```text
id: 12
data: {"id":"evt_01J...","sequence":12,"type":"tool.completed",...}

```

这样浏览器统一使用 `source.onmessage`。如果将来发送 `event: tool.completed`，前端必须改用 `addEventListener`，两种方式不要混用。

## 契约测试

在伴随项目根目录执行：

```bash
make contract-test
```

契约测试至少验证：

- 状态枚举完全一致。
- `sequence` 是大于等于 1 的整数。
- 未知字段默认被拒绝。
- `schema_version` 不受支持时返回稳定错误。
- Tool Gateway 拒绝未知工具、额外参数和调用方提交的命令字符串。
- TypeScript 在 `unknown` 数据通过 Schema 后才更新页面状态。

## Tool Gateway 契约

Python 到 Go 的工具请求使用 `tool-call.schema.json`，Go 返回 `tool-result.schema.json`。请求只包含语义工具、结构化参数和毫秒级超时；短期 capability 放在 HTTP `Authorization` Header 中，不写进 JSON、日志或事件。Go 启动 Agent 时另行传入初始 revision，每次工具响应再携带当前 `workspace_revision`，使 Python 的完成判定绑定到实际被测试的修订。两端测试共同消费 `contracts/fixtures/` 下的规范样例。

## Artifact 边界

Artifact 只保存元数据和受控下载位置，不把无限日志直接嵌入事件：

```text
patch       Git diff，文本，限制大小
test_report 结构化测试摘要
log         截断后的执行日志
trace       Agent 步骤和费用摘要
```

## 故障排查

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 前端无法识别终态 | 三端状态字面量不一致 | 从 Schema 生成或验证类型，不复制枚举 |
| SSE 重连后重复 Step | 没有按 `sequence` 去重 | Reducer 忽略不大于已消费序号的事件 |
| 新字段导致旧客户端崩溃 | 没有版本策略 | 增加可选字段或提升 `schema_version` |

Checkpoint：Schema 能被 JSON 解析器和契约测试读取，再进入服务实现。
