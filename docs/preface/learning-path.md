# 教程目标与学习路线

## 本章目标

完成本章后，你能够：

- 说清 RepoFix 的最小闭环和最终系统之间的差别；
- 选择适合自己的核心路线或扩展路线；
- 解释为什么 Daytona 是运行真实 Agent 的安全闸门；
- 使用同仓库伴随代码和章节 Checkpoint。

## 前置条件与本章产物

前置条件只有基本的 Git、Go 和命令行经验。本章不编写业务代码。

本章产物是一份写入学习日志的个人实施约定：每周可用时间、选择的路线、必须亲自实现的部分，以及不允许越过的安全边界。

## 1. 最小闭环与最终系统

第一个可验证闭环只有五步：

```text
读取任务 → 读取文件 → 修改文件 → 运行测试 → 程序确认完成
```

随后才逐层加入代码搜索、上下文选择、Daytona、Go 控制平面、持久化、SSE、评测和 Web 控制台。每一层都必须保留上一层可运行的测试，避免最后才发现最初的 Agent Loop 不可靠。

最终的 RepoFix 会完成：

```text
理解任务 → 探索代码 → 制定动作 → 调用工具 → 观察结果
        → 继续或停止 → 独立验证 → 保存 Diff、轨迹与成本
```

## 2. 两条完成路线

| 路线 | 必须完成 | 适合情况 |
| --- | --- | --- |
| 核心路线 | Python Agent、Daytona、最小 Go 状态机、3 个评测案例、简单 Web 轨迹页 | 希望先得到可靠闭环 |
| 扩展路线 | 完整恢复、20～30 个案例、上下文优化、报表、生产部署 | 核心路线已稳定，继续产品化 |

时间不足时缩小案例数和页面范围，不要删除安全隔离、失败测试或停止条件。

## 3. 第一版为什么不使用 Agent 框架

第一版手写 Agent Loop，亲自观察：

- 模型如何请求工具；
- 工具结果如何回到模型；
- 上下文如何随步骤增长；
- 程序如何处理无效参数、超时、取消和预算；
- 模型声明成功与系统验证成功有什么区别。

LangGraph 等框架可以在主项目完成后作为对照实验，但不进入关键路径。只有先理解状态和失败语义，才能判断框架替你做了什么。

## 4. 模型提出动作，程序验证动作

模型输出和目标仓库内容都视为不可信输入。程序必须验证：

- 工具名与参数符合严格 Schema；
- 文件路径没有逃逸工作区；
- 操作没有访问密钥或隐藏评测文件；
- Run 没有超过步数、时间、Token 或费用预算；
- 测试通过的是当前代码版本，而不是修改前的旧版本；
- 取消、失败和成功都会清理 Sandbox。

没有调用受验证的 `finish`，普通文本不能让 Run 进入成功状态。

## 5. 三阶段安全路线

| 阶段 | 允许 | 禁止 |
| --- | --- | --- |
| 状态与协议学习 | `FakeModel + FakeExecutor`，纯内存结果 | 真实模型工具调用、执行仓库代码 |
| 工具单元测试 | 对 `tmp_path` 的确定性测试、固定返回值 | 将模型输出传给本地 shell |
| Daytona 已接入 | 在一次性 Sandbox 中写入和执行 | 把开发密钥、主 GitHub Token 注入 Sandbox |

`LocalSandbox` 若在后续章节出现，只用于人工编写的确定性测试，不是 Live Model 的运行环境。

## 6. 伴随代码与 Checkpoint

同一个仓库包含：

```text
docs/                 教程正文
examples/repofix/     可运行的主线项目
```

实施章节成熟后会发布 `chapter-NN-start` 与 `chapter-NN-solution` tag。`start` 表示包含 TODO 和验收测试的起始骨架，`solution` 表示通过本章验收的参考实现。先确认当前 release 已提供目标 tag；不要把文档中的占位符当成真实版本：

```bash
git fetch --tags
git tag --list 'chapter-*'
```

目标 tag 存在时，推荐从 start tag 建个人分支，完成后与 solution tag 比较：

```bash
git fetch --tags
git switch -c work/chapter-NN chapter-NN-start
git diff chapter-NN-solution -- examples/repofix
```

比较 Diff 是为了发现遗漏，不是直接覆盖自己的实现。

## 7. 哪些部分必须亲自完成

建议首次实现选择 `Learn Manually`：

- 第一次模型 API 调用；
- Agent State 和 Agent Loop；
- Tool Call 分发；
- Stop Condition；
- Go Run 状态机；
- 第一个 Sandbox Adapter；
- 第一个评测运行器。

CI 模板、Dockerfile、重复 DTO 和基础页面可以让 Codex 协助，但你必须能解释最终 Diff 和失败路径。

## 验收

在 `examples/repofix/docs/learning-log/00-learning-contract.md` 写下：

```markdown
# 我的学习约定

- 路线：核心 / 扩展
- 每周可用时间：
- 我必须亲自完成：
- 我可以委托 Codex：
- Daytona 前绝不执行：
- 判断章节完成的证据：
```

然后自检：

- [ ] 能用自己的话解释 Stop Condition 为什么不能信任模型自报。
- [ ] 能说明 Codespaces 与 Daytona 的信任边界。
- [ ] 知道先检查 tag 是否已发布，并从已有 start tag 创建分支，而不是改 detached tag。
- [ ] 已选择核心路线或扩展路线。

## 故障排查

| 情况 | 处理 |
| --- | --- |
| 想跳过 Fake 直接调用真实模型 | 先完成 Fake 的成功和失败路径；真实调用不能替代确定性测试 |
| 时间表开始落后 | 缩小案例数量，不删除隔离与验证步骤 |
| 看懂代码但无法解释 | 关闭参考实现，画出一次 Step 的输入、动作、结果和状态变化 |
| Checkpoint tag 不存在 | 先 `git fetch --tags`；若列表仍为空，说明本章尚未发布 tag，改用自己的工作分支和本章基线命令，不要猜测 tag 名 |

## 练习

1. 用三句话说明“模型负责提出动作，程序负责验证动作”。
2. 列出 Codespaces 中可能存在的三类敏感数据。
3. 解释为什么把允许命令限制为 `pytest` 仍然不能安全运行模型修改后的仓库。

## Checkpoint

本章只产生学习日志，不修改 RepoFix 代码。保存日志后继续阅读[章节实践模板](chapter-workflow.md)，再进入[系统架构](../foundations/architecture.md)。
