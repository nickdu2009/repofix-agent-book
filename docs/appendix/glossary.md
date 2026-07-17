# 术语表

| 术语 | 在 RepoFix 中的含义 |
| --- | --- |
| Agent | 根据目标与观察反复选择动作，直到满足停止条件的程序 |
| Agent Loop | 模型决策、工具执行、结果回传和再次决策的循环 |
| Tool | 由程序控制、可被模型请求调用的外部能力 |
| Observation | 工具执行后返回给模型的结构化结果 |
| State | Run 过程中必须由程序保存和验证的数据 |
| AgentStatus | Python 单次决策循环的内部状态；`candidate_ready` 不等于最终 Run 成功 |
| RunStatus | Go 持久化并对外发布的 Run 生命周期状态 |
| Stop Condition | 成功、失败、步数、时间、预算或取消等终止规则 |
| Control Plane | 负责任务状态、调度、持久化和沙箱生命周期的 Go 服务 |
| Sandbox | 隔离运行不可信代码和命令的临时环境 |
| Run | RepoFix 对一个任务的一次完整执行尝试 |
| Step | Run 中一次模型决策及其工具执行记录 |
| Artifact | Diff、测试日志、报告等可持久化结果 |
| Eval Case | 带输入、缺陷仓库和确定性验收规则的评测案例 |
| Fake Model | 测试中按预设脚本返回工具调用、不消耗在线模型的替身 |
| Context Budget | 一次模型请求允许携带的上下文容量或成本上限 |
| SSE | 服务器向浏览器单向推送 Run 事件的 HTTP 机制 |
| Contract | Go、Python 与 TypeScript 服务之间共享的数据约束 |
| Capability Token | 只允许某个 Run 在有限时间和范围内调用 Tool Gateway 的短期凭据 |
| Checkpoint | 章节骨架或参考答案的可检出状态；目录使用 `labs/chapter-NN/{start,solution}`，未来 Git tag 使用 `chapter-NN-start` / `chapter-NN-solution` |
| Fixture | 为练习或评测专门构造、行为固定的缺陷仓库 |
| Oracle | 独立判断修复是否正确的可信测试或确定性规则 |
| Tool Schema | 描述工具名称、参数和约束的严格 JSON Schema |
| Trace | 一次 Run 中模型、工具、状态、Token、耗时和错误的结构化记录 |
| Idempotency | 相同请求重复执行不会产生额外副作用的性质 |
| Outbox | 将领域状态与待发布事件放在同一事务中的一致性模式 |
| Lease | Worker 对 Run 的限时所有权，需要续租并可在过期后被抢占 |
| Replay | 客户端重连或服务恢复时按序重新读取持久化事件 |
| Backpressure | 消费者过慢时限制缓冲、断开或降载的机制 |
| Hidden Test | Agent 不可见、只在独立验证环境中运行的测试 |
