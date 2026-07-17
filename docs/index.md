# RepoFix：从后端工程师到 AI Agent 工程实践

这不是一本把框架 API 罗列一遍的参考手册，而是一份可以持续数月完成的项目教程。

你将从一个最小的模型调用开始，亲手写出 Agent Loop，让 Agent 在隔离环境中读取代码、修改文件、运行测试，再逐步补上 Go 控制平面、状态恢复、评测体系和 TypeScript Web 控制台。

主线项目 **RepoFix** 接收一个 GitHub 仓库和 Issue，并尝试自动完成：

```text
理解问题 → 探索仓库 → 修改代码 → 运行测试
→ 根据结果重试 → 输出 Diff、测试报告和执行轨迹
```

## 这本书适合谁

- 有后端工程经验，主力语言是 Go。
- 使用过 Python，但需要恢复现代 Python 工程能力。
- 有 JavaScript 基础，希望在项目中掌握 TypeScript。
- 每周可投入约 5～7 小时。
- 希望使用 GitHub、Codespaces、Actions 和在线模型，不依赖本地计算机性能。

## 你会真正掌握什么

| 能力 | 项目中的证明 |
| --- | --- |
| Agent 原理 | 不依赖框架手写模型—工具—观察循环 |
| 安全执行 | 所有不可信命令都在 Daytona 沙箱中运行 |
| 可靠编排 | Go 状态机支持超时、取消、重试和恢复 |
| 可观测性 | 保存 Run、Step、事件、Diff 与测试结果 |
| 评测 | 用固定缺陷集比较成功率、成本和步骤数 |
| 产品化 | TypeScript 页面实时展示轨迹与结果 |

## 推荐阅读顺序

1. 先读[学习目标与方法](preface/learning-path.md)，理解为什么第一版不使用 LangGraph。
2. 按导航顺序完成正文。每章都要产出代码、测试或工程决策。
3. 正文不按周展开；需要安排时间时，再查看[28 周执行安排](appendix/28-week-plan.md)。
4. 每完成一个能力，就用[学习检查清单](appendix/checklists.md)确认自己能解释、能实现、能验证。

!!! warning "贯穿全书的安全边界"
    在接入 Daytona 以前，只允许 Agent 操作专门构造的 `fixtures/` 练习仓库。不要在 Codespaces 或带有开发密钥的环境中运行模型生成的任意命令。

[开始阅读](preface/learning-path.md){ .md-button .md-button--primary }
[查看 28 周安排](appendix/28-week-plan.md){ .md-button }
