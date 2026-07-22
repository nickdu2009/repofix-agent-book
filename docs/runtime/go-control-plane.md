# 第 10 章 · Go 控制平面

Go 控制平面拥有 Run 的生命周期：创建、排队、Sandbox、状态、取消、恢复和最终结果。它不解析 Prompt，也不实现模型决策。

## 快速开始

| 入口 | 内容 |
| --- | --- |
| Codespaces | [打开 RepoFix 通用工作区](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json) |
| 只读骨架 | `examples/repofix/labs/chapter-10/start/` |
| 准备工作副本 | `make chapter-prepare CHAPTER=chapter-10` |
| 工作副本 | `.work/chapter-10/` |
| 结构检查 | `make chapter-check CHAPTER=chapter-10` |
| 复盘参考 | `examples/repofix/labs/chapter-10/solution/` |

在 Codespaces 终端进入 `examples/repofix`，先运行 `chapter-prepare`，再只在 `.work/chapter-10/` 完成 TODO，最后运行 `chapter-check`。`start/` 始终只读；只有通过验收并记录自己的取舍后才用 `solution/` 复盘，不要从参考实现开始复制。

完成状态转移后运行 `go run .work/chapter-10/main.go`；程序必须接受合法转移并拒绝终态回到运行态。

## 本章契约

- **前置**：共享契约和 Python Agent HTTP 合约已完成；本章先实现 Fake Sandbox，下一章再替换为 Daytona Adapter。
- **产物**：可编译的 Go 领域/编排核心及 Fake Agent 全栈闭环。
- **验收**：不使用 OpenAI、Daytona 或 PostgreSQL，也能创建 Run、消费事件、取消并到达终态。

!!! success "当前 Fake Checkpoint"
    `services/control` 已实现 Run 状态机、并发安全内存 Repository、Fake Agent/Sandbox/Verifier、清理事件、零云端 E2E，以及受限 `POST /v1/tool-calls` Handler。完整公网 API、PostgreSQL 和真实 Daytona 属于后续 Checkpoint。

## 现代 Go 基线

本章统一使用 Go 1.26，并遵守以下约定：

- `context.Context` 从调用边界向下传递，用于取消和截止时间，不存入结构体；
- 使用 `errors.Is`、`errors.As` 和带 `%w` 的错误包装保留错误链；
- HTTP 与 Worker 日志使用标准库 `log/slog` 的结构化字段，不拼接不可检索的长字符串；
- 优先使用标准库以及 `slices`、`maps` 等明确工具，泛型只用于消除真实重复，不为抽象而抽象；
- 并发路径必须通过 `go test -race`，时间和取消逻辑优先用可控时钟或 `testing/synctest` 测试；
- 所有启动的 goroutine 都必须有所有者、停止条件和等待点。

“现代 Go”仍然强调小接口、显式错误和清晰所有权，不意味着把其他语言的框架风格搬进 Go。

## 目录结构

```text
services/control/
├── doc.go
├── fake_e2e_test.go
├── internal/domain/
│   ├── event.go
│   └── run.go
├── internal/orchestrator/
├── internal/repository/
├── internal/sandbox/
├── internal/toolgateway/
├── internal/agentclient/
└── internal/verifier/
```

## 状态机

第一版状态：

```text
pending → provisioning → running → succeeded
   │             │           ├──→ failed
   │             │           ├──→ cancelled
   │             │           └──→ timed_out
   └─────────────┴───────────────→ cancelled
```

合法转换必须集中在领域层：

```go
var allowed = map[RunStatus]map[RunStatus]bool{
	StatusPending:      {StatusProvisioning: true, StatusCancelled: true},
	StatusProvisioning: {StatusRunning: true, StatusFailed: true, StatusCancelled: true, StatusTimedOut: true},
	StatusRunning:      {StatusSucceeded: true, StatusFailed: true, StatusCancelled: true, StatusTimedOut: true},
}

func (r *Run) Transition(next RunStatus) error {
	if !allowed[r.Status][next] {
		return fmt.Errorf("invalid run transition: %s -> %s", r.Status, next)
	}
	r.Status = next
	r.Version++
	return nil
}
```

状态更新使用 `WHERE id = ? AND version = ?`，避免恢复 Worker 和原 Worker 同时完成 Run。

## HTTP API

下面列出完整目标 API。当前 Fake Checkpoint 已实现可挂载的 `/v1/tool-calls` Handler，但还没有 HTTP 组合根或监听端口：

```text
POST /v1/tasks
POST /v1/tasks/{task_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
GET  /v1/runs/{run_id}/artifacts
POST /v1/tool-calls
```

Tool Gateway 只接受共享 Schema 中的语义工具。Handler 验证 Bearer capability，将它解析为 Go 所有的 `sandbox_id`，拒绝未知字段、未知工具和参数漂移。路径必须是工作区相对路径，不能包含 `..`、反斜杠或 `.env`、`.git` 等敏感段；`tests/` 与 `.github/` 对写工具只读。当前 `run_tests` 只接受 `target=unit`，不能接收 shell 命令。

创建 Run 接受 `Idempotency-Key`。重复请求返回同一个资源，不能重复创建 Sandbox。

## Orchestrator 主路径

```go
func (o *Orchestrator) Execute(ctx context.Context, runID string) (err error) {
	run := o.claimPending(runID)
	box := o.createAndRecordSandbox(ctx, run)
	candidate := o.agent.Run(ctx, run, box)
	verified := o.verifier.Verify(ctx, box, candidate)
	run = o.cleanupAndRecord(ctx, run, box) // sandbox.deleted 或 cleanup_failed
	return o.finishFromVerifiedCandidate(ctx, run, verified)
}
```

代码中的精确错误路径比伪代码更长。关键不变量是：Verifier 必须确认测试覆盖当前 revision；Sandbox 清理结果事件先写入；最后才写唯一终态。Python 的 `summary` 或 `ClaimedSuccess` 不是成功凭据。

## 测试顺序

1. 表驱动测试覆盖全部合法和非法状态转换。
2. FakeAgent + FakeSandbox + FakeVerifier + 内存 Repository 跑闭环。
3. `go test -race ./services/control/...` 检查并发安全。
4. `httptest` 覆盖 Tool Gateway 的 capability、Schema、工具白名单与错误响应。
5. PostgreSQL 和 Daytona 作为后续 Adapter 合约测试。

## 故障排查与验收

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 同一 Run 创建两个 Sandbox | Claim 没有原子条件 | 使用 lease 与版本条件更新 |
| 取消后变成 succeeded | 终态竞争未定义 | 在事务中规定取消/超时优先级 |
| Go 服务退出时 Run 丢失 | Worker 只有内存状态 | 先落库，再执行外部动作 |

验收命令：

```bash
go test ./services/control/...
go test -race ./services/control/...
make fake-e2e
```

Fake E2E 必须在没有云端密钥的 CI 中运行。
