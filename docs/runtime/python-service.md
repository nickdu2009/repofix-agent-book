# Python Agent 服务化

Python 服务只拥有一次 Run 内部的模型决策循环。Go 传入 Run、任务和短期 Tool Gateway capability，Python 返回结构化候选结果。当前 Fake HTTP 闭环尚未上报 Step 事件；事件上报要等 Tool Gateway Client 与事件端口接入后实现。

## 本章契约

- **前置**：Agent Loop 可由 FakeModel 独立测试；共享契约已经固定。
- **产物**：FastAPI 应用、Pydantic 边界模型、健康检查和 HTTP 合约测试。
- **验收**：Go 可通过一次请求启动完整 Loop；不存在 `/next` 双重驱动。

!!! success "当前伴随实现"
    `services/agent` 已提供可运行的 FastAPI 边界和 5 条纯离线 API 测试。默认应用故意 fail-closed：未注入 RunnerFactory 时 `/healthz` 为 200、`/readyz` 为 503，也不会在 import 时创建 OpenAI Client。

## API

```text
POST /v1/agent-runs
POST /v1/agent-runs/{run_id}/cancel
GET  /healthz
GET  /readyz
```

请求示例：

```json
{
  "run_id": "run_01J...",
  "task": "修复小数除法错误并运行测试",
  "workspace_capability": "cap_short_lived",
  "tool_gateway_url": "http://control.internal/v1/tool-calls",
  "max_steps": 20,
  "deadline": "2099-01-01T00:00:00Z"
}
```

## 项目结构

```text
services/agent/
├── pyproject.toml
├── src/repofix_agent/
│   ├── api.py
│   ├── api_models.py
│   ├── config.py
│   ├── domain.py
│   ├── runner.py
│   └── service.py
└── tests/
    └── test_api.py
```

Pydantic 只用于 HTTP、配置和外部事件；AgentState、StepRecord、ToolResult 继续使用标准库 dataclass。

## Handler 边界

```python
@app.post("/v1/agent-runs", response_model=AgentRunResponse)
async def run_agent(request: AgentRunRequest) -> AgentRunResponse:
    return await service.run(request)
```

Handler 不创建 OpenAI Client、不解析工具参数、不持久化 Run。`AgentServiceError`、Pydantic 校验错误、404/405 和意外错误由统一 exception handler 转换成顶层 `ErrorResponse`，不会被 FastAPI 包成 `{"detail": ...}`。依赖通过 `create_app(runner_factory=...)` 注入，测试时换成 FakeModel 和 FakeToolExecutor。

现有 Runner 与 Adapter 是同步接口。`AgentService` 使用 `asyncio.to_thread()` 包住 Runner 的构造和完整执行，避免阻塞 FastAPI 事件循环。Runner 会把剩余 deadline 传给模型和工具 Adapter；取消 endpoint 可以立即设置线程安全 Token，但正在进行的网络/命令调用仍必须由各 Adapter 自己的 timeout 和 Go 进程取消来中断。

## 取消语义

取消不是简单地停止 HTTP 连接：

1. Go 将 Run 标记为已请求取消。
2. Go 调用 Python cancel endpoint，并取消 Tool Gateway 中的进程。
3. Python 在模型调用前后、工具调用前后检查取消事件。
4. Python 返回 `cancelled` 或 `candidate_ready` 事实；不会返回最终 `succeeded`。
5. Go 删除 Sandbox 并写入终态事件。

## 错误模型

所有非 2xx 响应符合 `contracts/error.schema.json`。当前离线服务已经区分：

```text
invalid_request       不重试
run_already_exists    409
run_not_active        不重试
not_ready             可重试
budget_exceeded       不在原 Run 内重试
deadline_exceeded     不在原 Run 内重试
cancelled             不重试
agent_failed          不重试
```

接入 Live Model 与 Tool Gateway Client 后，还必须把 Adapter 异常稳定映射为 `model_rate_limited`、`model_timeout` 和 `tool_gateway_failed`；当前实现不能宣称已经提供这三类错误。

## 实践步骤

```bash
cd examples/repofix/services/agent
../../.venv/bin/python -m pip install -e '.[dev,service]'
../../.venv/bin/python -m pytest -q tests/test_api.py
../../.venv/bin/python -m uvicorn repofix_agent.api:app --host 127.0.0.1 --port 8081
```

预期：5 条测试不调用网络。直接启动的默认应用用于观察 fail-closed 行为：`/healthz` 返回进程存活，`/readyz` 返回顶层 `not_ready` 错误。真正 ready 的进程必须由组合根注入 Live Model 与 Go Tool Gateway Client；在 Daytona Adapter 发布前不要伪造 `is_sandboxed=True`。

## 故障排查与验收

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 测试调用真实模型 | Adapter 在模块导入时创建 | 使用依赖注入，测试显式注入 Fake |
| Go 重试产生两个 Loop | 缺少 Run 幂等记录 | 以 `run_id` 为幂等键 |
| 客户端断开后任务仍运行 | 只依赖连接状态 | 使用明确 cancel endpoint 和 Run deadline |

当前验收覆盖：不就绪、Fake 完整闭环、重复 `run_id`、非法 Schema 的顶层错误，以及同步模型调用期间取消 endpoint 仍可响应。接入 Live Adapter 前还必须补模型超时、限流、工具失败和 Gateway 身份验证合约测试。
