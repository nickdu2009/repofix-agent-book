# 附录 A：28 周执行安排

> 每周投入 5～7 小时。正文定义“做什么和为什么”，本附录只负责时间落地。

| 周 | 项目实践 | 语言学习重点 | 周产物 |
| --- | --- | --- | --- |
| 1 | 创建 GitHub 仓库、Projects、Codespaces | Python 环境、模块、类型标注 | 仓库骨架、学习看板 |
| 2 | 完成首次模型调用和基础 CI | Python 异常、`pathlib`、pytest | 模型调用、一个单元测试 |
| 3 | 定义 AgentState、StepRecord | `dataclass`、`StrEnum` | 状态模型与测试 |
| 4 | 实现读取、搜索和写入工具 | `Protocol`、JSON、路径安全 | 文件工具与安全测试 |
| 5 | 手写 Agent Loop | 工具调用、依赖注入 | 可运行决策循环 |
| 6 | 加入 Stop Condition、预算和轨迹 | Fake Model、pytest fixture | 修复第一个 Fixture |
| 7 | 抽象 Sandbox 接口 | Python 上下文管理器 | LocalSandbox |
| 8 | 接入 Daytona | SDK、异常和资源清理 | 云沙箱创建与执行 |
| 9 | 将文件与命令工具迁入沙箱 | 超时、`try/finally` | 沙箱内完整工具链 |
| 10 | 完成 Agent MVP | Python 异步基础 | 修复 5～10 个缺陷 |
| 11 | 创建 Go Control 服务 | Go 状态机设计 | Task/Run/Step 实体 |
| 12 | 实现 Run 状态转移和 API | Go 事务、幂等 | 创建和查询 Run |
| 13 | Python Agent 服务化 | FastAPI、Pydantic | Go 调用 Python |
| 14 | 接入 PostgreSQL 和事件 | Go 持久化、SSE | 可持久化运行轨迹 |
| 15 | 加入取消、超时、重试和恢复 | Go context | 可靠控制平面 |
| 16 | 建立 5 个评测案例 | pytest 参数化 | Eval Runner MVP |
| 17 | 扩展到 10～15 个案例 | Fixture、Fake Model | Smoke Eval |
| 18 | 记录 Token、耗时和错误 | JSONL、统计 | 评测报告 |
| 19 | 实现 Prompt/模型对比 | 故障注入 | 回归基线 |
| 20 | 增加仓库摘要和代码搜索 | Python 生成器、缓存 | 上下文选择器 |
| 21 | 增加上下文预算 | Python 迭代器、文本处理 | Token 预算控制 |
| 22 | 失败重规划和死循环检测 | TypeScript 联合类型入门 | 重复动作检测 |
| 23 | 创建 Web 项目和任务页面 | TS `strict`、接口、Zod | 创建任务页面 |
| 24 | 实现 SSE 轨迹页面 | Promise、Fetch、EventSource | 实时 Run 页面 |
| 25 | 实现 Diff、测试和评测页面 | React Hooks、Reducer、Vitest | 完整演示 UI |
| 26 | 部署 Go、Python 和 Web | TS 构建与环境变量 | Railway 测试环境 |
| 27 | 完善 CI、Smoke Test、回滚 | Playwright 基础 | 自动部署流程 |
| 28 | 文档、演示和案例复盘 | 综合复习 | 作品集版本 v1.0 |

## 附录 B：每周时间模板

| 活动 | 建议时间 |
| --- | --- |
| ChatGPT 概念学习与设计 | 45～60 分钟 |
| Python/TypeScript 小练习 | 30～45 分钟 |
| Codespaces 亲自实现核心功能 | 2 小时 |
| 与 Codex 配对开发 | 1.5～2 小时 |
| 测试、评测和 Diff 审查 | 1 小时 |
| GitHub 记录与复盘 | 30～60 分钟 |

每周结束前回答：

1. 本周新增了什么可运行能力？
2. 哪部分由自己实现，哪部分由 Codex 实现？
3. 能否解释新增状态和数据流？
4. 哪个测试证明功能有效？
5. 本周真实模型调用花费多少？
6. 下周最小目标是什么？

## 附录 C：Python 特性学习顺序

```text
类型标注和工程结构
  → dataclass / Enum
  → Protocol 和依赖注入
  → pathlib / subprocess / JSON
  → pytest / fixture / 参数化
  → 上下文管理器
  → async / await / 取消与超时
  → FastAPI / Pydantic
  → 生成器 / 缓存 / 评测统计
```

每个特性都采用：

```text
理解概念
  → 写一个不超过 30 行的小练习
  → 应用到 RepoFix
  → 写测试
  → 让 Codex 审查
  → 自己解释设计原因
```

## 附录 D：TypeScript 特性学习顺序

```text
JavaScript 与 TypeScript 差异
  → strict / type / interface
  → 联合类型和类型收窄
  → unknown 和运行时校验
  → 泛型和常用工具类型
  → Promise / Fetch / AbortController
  → SSE / EventSource
  → React Hooks / Reducer
  → Vitest / Playwright
```

TypeScript 的学习目标不是掌握复杂类型体操，而是让前后端契约、事件流和 UI 状态可验证、可维护。

