# 术语表

| 术语 | 在 RepoFix 中的含义 |
| --- | --- |
| Agent | 根据目标与观察反复选择动作，直到满足停止条件的程序 |
| Agent Loop | 模型决策、工具执行、结果回传和再次决策的循环 |
| Tool | 由程序控制、可被模型请求调用的外部能力 |
| Observation | 工具执行后返回给模型的结构化结果 |
| State | Run 过程中必须由程序保存和验证的数据 |
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
