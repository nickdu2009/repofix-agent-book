# ChatGPT 与 Codex 协作

AI 协作的目标不是减少思考，而是把重复实现、检查和反馈变成可审查的工程流程。核心机制仍要由你亲自解释并对测试负责。

## 本章契约

- **前置**：已经使用至少一个代码 Checkpoint，并理解仓库安全规则。
- **产物**：一个范围明确的 Issue、实现分支、测试证据、Diff 审查和学习复盘。
- **验收**：你能指出哪些判断由自己做出，哪些实现由 Codex 辅助，以及什么测试证明结果。

## 职责分工

| 工作 | ChatGPT | Codex | 你 |
| --- | --- | --- | --- |
| 概念与方案比较 | 讲解、追问、复盘 | 读取仓库后补充约束 | 作出并记录决策 |
| 核心机制 | 帮助拆解 | 配对、测试、审查 | 第一版亲自实现并解释 |
| 重复工程 | 给检查清单 | CI、脚手架、格式化、机械重构 | 审查 Diff |
| 故障分析 | 分析轨迹和假设 | 复现、定位、补测试 | 确认可接受的修复 |

第一版必须亲自实现并讲清：第一次模型调用、AgentState、Agent Loop、Tool 流程、Stop Condition、Go 状态机、Sandbox Adapter 和 Eval Runner。

## 每个 Issue 的工作流

1. 从章节 `start` tag 创建分支。
2. 把 Goal、Context、Constraints 和 Done when 写进 Issue。
3. 先亲自实现该章要求的语言小练习和核心骨架。
4. 让 Codex 阅读 `AGENTS.md`、相关实现和现有测试。
5. Codex 在明确文件范围内实现或审查。
6. 运行章节验收命令，检查成功和失败路径。
7. 阅读完整 Diff，不只看摘要。
8. 写学习日志，再与 `complete` checkpoint 比较。

## 配对提示词

```text
Goal:
为 RepoFix 的 read_utf8_file 增加路径与文件类型保护。

Context:
伴随项目位于 examples/repofix。
Python Agent 位于 services/agent。
Daytona 前的测试只能使用 FakeModel/FakeExecutor。

Allowed files:
- services/agent/src/repofix_agent/path_tools.py
- services/agent/tests/test_path_tools.py

Constraints:
- 不引入新框架
- 不执行真实模型生成的代码或命令
- 不读取工作区外文件
- 先阅读现有测试

Done when:
- 正常 UTF-8 文件可读取
- ../、绝对路径和外部符号链接被拒绝
- 二进制和超大文件被拒绝
- Python 测试与 Ruff 通过
- 给出剩余风险，不把路径检查称为沙箱
```

限制允许修改的文件能显著降低无关重构，也让 Diff 更容易学习。

## 审查清单

不要只问“测试是否通过”。逐项检查：

- 实现是否改变了约定的领域或 Wire Contract。
- 成功条件是否仍由程序验证。
- 是否新增真实网络、命令、凭据或付费调用。
- 是否覆盖至少一条成功和两条失败路径。
- 错误、取消、超时和清理是否仍有明确所有者。
- 是否有通过弱化测试、跳过检查或扩大权限得到的“绿色”。
- 文档命令、文件路径和实际源码是否一致。

## 安全约束

Codex 可以运行本书和伴随代码的可信测试，但不能把开发工作区当成 Live Agent Sandbox。任何由真实模型针对目标仓库生成或修改的代码，只能在 Daytona Checkpoint 之后、由受控 Tool Gateway 在隔离环境中执行。

Secret 不应出现在提示词、Diff、测试快照或日志中。需要确认变量时，只检查“是否存在”，不要打印值。

## 学习复盘

每个 Issue 完成后回答：

1. 本次新增的程序不变量是什么？
2. 哪条失败测试最能证明它？
3. 如果删除该检查，会出现什么错误或安全后果？
4. Codex 提议中有哪些内容没有采用，为什么？
5. 你是否能在不看实现的情况下重画数据流或状态转换？

## AGENTS.md

仓库根目录保存书籍编辑规则，`examples/repofix/AGENTS.md` 保存伴随项目命令、所有权和安全边界。规则应短、可执行，并与 CI 使用同一命令。

Checkpoint：一个他人可以复现的 PR，包含范围、实现、测试输出、剩余风险和学习日志，而不只是“Codex 已完成”的说明。
