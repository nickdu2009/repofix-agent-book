# Python Agent 服务化

Go 控制平面通过 HTTP 调用 Python Agent。此时引入 FastAPI 和 Pydantic。

### 10.1 Python 特性与框架边界

Pydantic 用于：

- HTTP 请求和响应。
- 配置。
- 模型工具参数。
- 外部事件解析。

内部 AgentState、StepRecord 和 ToolResult 可以继续使用 `dataclass`。

### 10.2 API 建议

```text
POST /agent/runs
POST /agent/runs/{run_id}/next
POST /agent/runs/{run_id}/cancel
GET  /health
```

实践重点：

- `async def` 与普通 `def` 的区别。
- 超时和取消如何跨 HTTP 传播。
- Python 异常如何转换成稳定的错误响应。
- 请求 ID 和 Run ID 如何进入日志。
- Go 与 Python 如何共享 OpenAPI/JSON Schema。
