# 运行时架构决策

本章先固定组件所有权，再编写 Daytona、Python 服务和 Go 控制平面。否则取消、重试和清理会同时由两个服务负责。

## 本章契约

- **前置**：完成 Fake Agent Loop，并能在不执行真实命令的情况下通过单元测试。
- **产物**：`examples/repofix/docs/adr/0001-runtime-ownership.md`。
- **验收**：你能沿一次 Run 说明状态、工具、事件和 Sandbox 分别由谁拥有。

## ADR-0001：组件所有权

RepoFix v1 采用以下边界：

| 能力 | 唯一所有者 | 说明 |
| --- | --- | --- |
| Task、Run 和最终状态 | Go 控制平面 | Python 只能上报事实，不能直接宣布最终 Run 成功 |
| Agent Loop 和上下文 | Python Agent | 一次 HTTP 请求运行完整 Loop，不再提供含糊的 `/next` 接口 |
| Daytona 创建与删除 | Go 控制平面 | 只有 Go 持有 Daytona 凭据 |
| 文件与命令工具 | Go Tool Gateway | Python 使用短期 capability token 调用受控工具 |
| Step、Event、Artifact 持久化 | Go 控制平面 | 状态转换与事件写入同一事务 |
| 模型 API 凭据 | Python Agent | 不传入 Daytona Sandbox |

```mermaid
sequenceDiagram
    participant Web
    participant Go as Go Control
    participant Py as Python Agent
    participant Box as Daytona
    Web->>Go: 创建 Run
    Go->>Box: 创建 Sandbox
    Go->>Py: POST /v1/agent-runs
    loop Agent Step
        Py->>Go: 调用 Tool Gateway
        Go->>Box: 文件或命令操作
        Box-->>Go: ToolResult
        Go-->>Py: ToolResult
    end
    Py-->>Go: AgentRunResult
    Go->>Box: 删除 Sandbox
    Go-->>Web: SSE 终态事件
```

## 为什么选择完整 Run API

Python 拥有 Agent Loop，因此 Go 只发起一次完整 Run：

```text
POST /v1/agent-runs
POST /v1/agent-runs/{run_id}/cancel
GET  /healthz
GET  /readyz
```

Go 通过请求 deadline 和取消接口传播取消；Python 每轮模型调用和工具调用前检查取消标记。工具调用仍经过 Go，因此 Go 可以立即终止 Sandbox 中的进程。

## 故障所有权

| 故障 | 负责判断 | 负责清理 | 最终状态 |
| --- | --- | --- | --- |
| 模型限流且重试耗尽 | Python | Go | `failed` |
| 工具命令超时 | Go | Go | `failed` 或继续重规划 |
| 用户取消 | Go | Go | `cancelled` |
| Run deadline 到期 | Go | Go | `timed_out` |
| Python 崩溃 | Go | Go | v1 将当前 Run 置为 `failed`；新 Run 才可重试 |
| Sandbox 删除失败 | Go | Go 后台清理器 | 保留 Run 终态并记录清理告警 |

## 练习与验收

1. 画出“用户取消发生在测试运行中”的传播路径。
2. 解释为什么 Python 不应持有 Daytona 主凭据。
3. 检查后续章节是否出现第二个 Run 状态所有者。

完成标准：任何资源都只有一个生命周期所有者，每一种失败都能找到负责清理的组件。
