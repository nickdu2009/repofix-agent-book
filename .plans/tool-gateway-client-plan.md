# 实施计划：Python 到 Go Tool Gateway 闭环

## 来源与对齐

- 需求来源：用户确认添加 Python → Go 的真实 Tool Gateway Client。
- 设计来源：本对话确认的最小双向调用架构。
- ADR 约束：
  - ADR-0001 — Runtime ownership — Accepted — `examples/repofix/docs/adr/0001-runtime-ownership.md`
- 范围边界：实现严格 Tool Call 契约、Python HTTP Client、Go HTTP Handler 和离线测试；不实现 Daytona SDK、任意 Shell、PostgreSQL 或生产认证存储。

## 验收标准追溯

- AC1：Python Client 实现现有 `ToolExecutor` 协议。
- AC2：Go Handler 校验 Bearer capability、严格 JSON 和受支持工具。
- AC3：Go 传入真实初始 revision，响应携带 ToolResult 和当前 revision。
- AC4：所有测试离线运行，不执行模型生成命令。
- AC5：第 9～11 章及实现状态准确反映新边界。

## 并行规划

[parallelism:
- independent lanes: none
- sequential blockers: wire contract before both adapters
- shared write surfaces: tool DTO and runtime documentation
- delegation: 0 because both sides must evolve against one contract
]

## 实施步骤

### 步骤 1：固定 Tool Gateway Wire 契约

- 落地文件/模块：`examples/repofix/contracts/`
- 依赖：无
- 操作要点：增加严格请求与响应 Schema。
- 受约束 ADR：ADR-0001
- 验收检查（verify）：`make contract-test`
- 覆盖验收标准：AC2、AC3

### 步骤 2：实现 Python ToolGatewayClient

- 落地文件/模块：`examples/repofix/services/agent/src/repofix_agent/`、对应测试
- 依赖：步骤 1
- 操作要点：使用标准库 HTTP Client，发送 capability，禁止重定向，校验响应并从真实初始 revision 更新状态。
- 受约束 ADR：ADR-0001
- 验收检查（verify）：`make agent-test`
- 覆盖验收标准：AC1、AC3、AC4

### 步骤 3：实现 Go Tool Gateway Handler

- 落地文件/模块：`examples/repofix/services/control/internal/toolgateway/`
- 依赖：步骤 1
- 操作要点：验证请求、能力令牌、工作区路径和测试目标白名单，再调用受控执行函数。
- 受约束 ADR：ADR-0001
- 验收检查（verify）：`make go-test`、`make go-race`
- 覆盖验收标准：AC2、AC3、AC4

### 步骤 4：更新教程状态

- 落地文件/模块：`docs/runtime/python-service.md`、`docs/runtime/go-control-plane.md`、`docs/runtime/daytona-sandbox.md`、`docs/preface/implementation-status.md`
- 依赖：步骤 2、步骤 3
- 操作要点：把真实跨服务 HTTP 边界与仍缺失的 Daytona Adapter 分开标注。
- 受约束 ADR：ADR-0001
- 验收检查（verify）：`mkdocs build --strict`
- 覆盖验收标准：AC5

## 风险与回滚

- 风险：Gateway 响应 revision 与实际 Sandbox 不一致。
  - 关联步骤：2、3
  - 缓解 / 回滚：每次响应强制携带非负 revision；异常响应由 Python fail-closed。
- 风险：接口意外允许任意命令。
  - 关联步骤：3
  - 缓解 / 回滚：固定工具名白名单，参数只作为结构化数据交给执行函数。

## 验收标准覆盖检查

- AC1 → 步骤 2
- AC2 → 步骤 1、3
- AC3 → 步骤 1～3
- AC4 → 步骤 2、3
- AC5 → 步骤 4

## 待确认 / 残留假设

- 【假设】Capability 到 Sandbox 的映射由 Go 组合根提供；本次只定义最小解析函数边界。（验证方法：后续 Daytona 组合根测试。）

## 下一步

- 按步骤实现，然后运行自审和定向验证。
