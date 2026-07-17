# 共享契约

Python、Go 和 TypeScript 不应分别手写三套 **Wire RunStatus 与 RunEvent**。伴随代码在 `examples/repofix/contracts/` 保存机器可验证的 JSON Schema。Python 内部 `AgentStatus.CANDIDATE_READY` 是不同领域概念，绝不能序列化成最终 Run `succeeded`。

## 本章契约

- **前置**：阅读运行时架构决策。
- **产物**：Run、Event、Error 和 Artifact Schema。
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
- TypeScript 在 `unknown` 数据通过 Schema 后才更新页面状态。

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
