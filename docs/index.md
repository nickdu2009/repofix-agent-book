# RepoFix：从后端工程师到 AI Agent 工程实践

这是一份可以从空白工作区一路做到可部署系统的实践教程。正文先解释问题、取舍和失败方式；每章再给一个小型起始骨架、可复制命令、测试与参考实现，代码服务于学习，而不是占据教程主体。

主线项目 **RepoFix** 接收一个 GitHub 仓库和 Issue，并尝试完成：

```text
理解问题 → 探索仓库 → 修改代码 → 在隔离环境中测试
         → 根据结果重试 → 输出 Diff、测试报告和执行轨迹
```

## 阅读前提

本书面向有 Go 后端经验、使用过 Python、了解 JavaScript 的读者。你不需要本地 GPU，也不需要预先掌握 Agent 框架。

开始前准备：

- 一个 GitHub 账号，可以创建 Codespace；
- 每周约 5～7 小时的持续投入；
- 后续真实模型章节需要 OpenAI API Key；
- 后续隔离执行章节需要 Daytona 账号；
- 愿意亲自实现 Agent Loop、状态机、停止条件和首个评测运行器。

!!! info "正文与伴随代码在同一个仓库"
    `docs/` 是你正在阅读的书，`examples/repofix/` 是可以运行和修改的伴随项目。除非章节另有说明，所有项目命令都从 `examples/repofix/` 执行。

!!! warning "先看实现状态"
    前半本的 Fake 闭环已有源码与 CI；Daytona、PostgreSQL、完整页面和 Railway 仍包含目标设计。开始章节前先查[学习与实现路线图](preface/implementation-status.md)，区分“教材已准备”和“项目已实现”，不要执行尚未发布的目标命令。

## 最快开始

1. 阅读[学习路线](preface/learning-path.md)、[学习与实现路线图](preface/implementation-status.md)和[怎样完成一章](preface/chapter-workflow.md)。
2. 按[仓库与云端工作区](foundations/cloud-workspace.md)创建 Codespace，或先在[在线练习](playgrounds/index.md)运行语法小题。
3. 在伴随项目中准备第一章骨架：

   ```bash
   cd examples/repofix
   make chapter-list
   make chapter-prepare CHAPTER=chapter-01
   make chapter-check CHAPTER=chapter-01
   ```

4. 完成[第一个缺陷练习仓库](foundations/fixture.md)，理解“初始测试失败”和“修复后测试通过”为什么是两个独立证据。
5. 之后按左侧导航完成正文；时间安排只在[28 周执行安排](appendix/28-week-plan.md)中出现。

## 你将交付什么

| 能力 | 可验证产物 |
| --- | --- |
| Agent 原理 | 不依赖 Agent 框架的模型—工具—观察循环及单元测试 |
| 安全执行 | Daytona 中的隔离命令、资源清理记录和安全失败测试 |
| 可靠编排 | Go 状态机及超时、取消、重试、恢复测试 |
| 可观测性 | Run、Step、事件、Diff 与测试结果 |
| 评测 | 固定缺陷集、隐藏验证、JSONL 结果和对比报告 |
| 产品化 | TypeScript 页面、SSE 轨迹、CI 和部署版本 |

完成本书不是“所有页面都读过”，而是从一个全新 Codespace 可以复现项目，完成自己的章节工作副本，并用验收命令证明结果。

## 骨架与参考实现如何使用

每章的文件结构保持一致：

```text
labs/chapter-04/start/       带 TODO 的起点
labs/chapter-04/solution/    用于复盘的参考实现
.work/chapter-04/            你的工作副本，不提交到仓库
```

不要直接编辑骨架，先复制到工作区：

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-04
make chapter-check CHAPTER=chapter-04
```

第一次结构检查会按教学设计失败。完成 TODO、补齐骨架要求的完成标记、运行该章的行为命令并通过检查后，再对照 `solution/`。未来稳定版本仍会使用 `chapter-04-start` 与 `chapter-04-solution` tag，但 tag 不是开始当前教程的前置条件。

## 贯穿全书的安全闸门

!!! danger "Daytona 前禁止 Live Model 执行"
    在完成 Daytona 隔离章节以前，只能使用确定性的 `FakeModel` 与 `FakeExecutor` 测试 Agent Loop。即使目标只是 `fixtures/`，也不能让真实模型在 Codespaces 或本地工作站写入代码后执行它，更不能运行模型生成的命令。

原因是命令名白名单并不能隔离代码：`pytest` 会导入项目代码，`npm test` 会运行 scripts，`go test` 也会编译并执行仓库内容。开发环境可能含有 GitHub Token 和模型密钥，它不是不可信代码的沙箱。

只有同时满足以下条件，才能跨过安全闸门：

- Agent 的文件和命令工具已经接到一次性 Daytona Sandbox；
- Sandbox 不含开发机密钥和主 GitHub Token；
- 有时间、资源、网络与路径限制；
- 无论成功、失败还是取消，Sandbox 都会显式删除；
- 集成测试证明命令没有在开发宿主机执行。

## 入门验收

- [ ] 能说明 `docs/` 与 `examples/repofix/` 的关系。
- [ ] 能生成独立章节工作副本，并说明 `start/`、`.work/` 与 `solution/` 的区别。
- [ ] `make chapter-check CHAPTER=chapter-01` 成功。
- [ ] 能解释为什么真实模型必须等到 Daytona 后才运行。
- [ ] 能区分“Agent 声称修复”和“独立测试证明修复”。

如果环境命令失败，先查看[工作区故障排查](foundations/cloud-workspace.md#workspace-troubleshooting)，不要跳过失败直接进入 Agent 章节。

[开始阅读](preface/learning-path.md){ .md-button .md-button--primary }
[创建工作区](foundations/cloud-workspace.md){ .md-button }
