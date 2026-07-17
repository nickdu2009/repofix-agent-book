# Go 控制平面

Go 控制平面拥有 Run 的生命周期：创建、排队、Sandbox、状态、取消、恢复和最终结果。它不解析 Prompt，也不实现模型决策。

## 本章契约

- **前置**：共享契约和 Python Agent HTTP 合约已完成；本章先实现 Fake Sandbox，下一章再替换为 Daytona Adapter。
- **产物**：可编译的 Go 领域/编排核心及 Fake Agent 全栈闭环。
- **验收**：不使用 OpenAI、Daytona 或 PostgreSQL，也能创建 Run、消费事件、取消并到达终态。

!!! success "当前 Fake Checkpoint"
    `services/control` 已实现 Run 状态机、并发安全内存 Repository、Fake Agent/Sandbox/Verifier、清理事件和零云端 E2E。HTTP Handler、PostgreSQL 和真实 Daytona 属于后续 Checkpoint。

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

下面是完成 Go HTTP Adapter 后的目标 API；当前 Fake Checkpoint 没有监听端口：

```text
POST /v1/tasks
POST /v1/tasks/{task_id}/runs
GET  /v1/runs/{run_id}
GET  /v1/runs/{run_id}/events
POST /v1/runs/{run_id}/cancel
GET  /v1/runs/{run_id}/artifacts
POST /v1/tool-calls
```

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
4. 增加 HTTP 后再用 `httptest` 覆盖 API Schema、幂等与错误响应。
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
