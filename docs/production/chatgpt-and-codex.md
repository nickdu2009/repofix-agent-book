# ChatGPT 与 Codex 协作方式

### 17.1 ChatGPT 负责

- 从 Go 开发者视角解释 Python 和 TypeScript。
- 讨论 Agent 状态、工具和安全边界。
- 设计每次实践的完成标准。
- 分析失败轨迹。
- 完成阶段复盘和知识检查。

### 17.2 Codex 负责

- 阅读仓库并制定实施计划。
- 在明确范围内修改代码。
- 补充测试和异常处理。
- 修复 CI。
- 审查 Diff。
- 整理文档和重复性配置。

### 17.3 必须亲自实现的第一版

- 第一次模型 API 调用。
- AgentState。
- Agent Loop。
- Tool 执行流程。
- Stop Condition。
- Go Run 状态机。
- 第一个 Sandbox 适配器。
- 第一个 Evaluation Runner。

### 17.4 可以更多交给 Codex

- GitHub Actions YAML。
- Dockerfile。
- 基础 TypeScript 页面脚手架。
- 重复 DTO 和生成客户端。
- 测试 Fixture 整理。
- 文档格式化。
- 常规 CRUD。

### 17.5 Codex 提示词模板

```text
Goal:
为 RepoFix 的 read_file 工具增加安全路径检查。

Context:
Python Agent 位于 services/agent。
Agent 只能访问指定 workspace。

Constraints:
- 不引入新框架
- 不改变无关工具
- 不允许路径穿越
- 保持最小改动
- 先阅读现有测试

Done when:
- 正常相对路径可以读取
- ../ 路径被拒绝
- 符号链接逃逸被拒绝
- pytest 全部通过
- 给出改动摘要
```

仓库根目录应维护简洁的 `AGENTS.md`，记录构建命令、职责边界、安全要求和完成标准。Codex 会读取仓库中的 `AGENTS.md` 作为持久指导。参考：[Codex AGENTS.md](https://developers.openai.com/codex/agent-configuration/agents-md)
