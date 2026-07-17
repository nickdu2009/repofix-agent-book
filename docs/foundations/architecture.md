# 系统架构

```text
┌─────────────────────────────┐
│ TypeScript Web              │
│ 创建任务、SSE、Diff、评测   │
└──────────────┬──────────────┘
               │ HTTP / SSE
┌──────────────▼──────────────┐
│ Go Control Plane            │
│ Task / Run / Step 状态机    │
│ 超时、取消、重试、恢复      │
└───────┬──────────────┬──────┘
        │              │
        │ HTTP         │ Sandbox API
┌───────▼────────┐  ┌──▼────────────────┐
│ Python Agent   │  │ Daytona Sandbox   │
│ 模型与决策循环 │  │ 克隆、修改、测试  │
└───────┬────────┘  └───────────────────┘
        │
        │ Online Model API
┌───────▼────────┐
│ OpenAI API     │
└────────────────┘

               ┌───────────────────────┐
               │ PostgreSQL            │
               │ Task/Run/Step/Eval    │
               └───────────────────────┘
```

### 3.1 语言职责

| 技术 | 核心职责 |
| --- | --- |
| Go | API、状态机、任务编排、并发、超时、取消、持久化、SSE、沙箱生命周期 |
| Python | 模型调用、Agent Loop、工具定义、上下文选择、Prompt、评测运行器 |
| TypeScript | 任务创建、实时轨迹、Diff、测试结果、评测报表 |
| PostgreSQL | Task、Run、Step、Artifact、Evaluation 数据 |
| Daytona | 隔离运行仓库代码和 Agent 生成的命令 |
