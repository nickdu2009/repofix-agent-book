# 怎样完成一章

这本书的主角是你的思考与实践，代码只是用来验证理解。每章都提供一个小骨架和一个参考实现，但推荐顺序始终是：先读问题、自己完成、让测试暴露误解，最后才看参考实现。

## 60 秒开始

以 `chapter-05` 为例，在仓库根目录执行：

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-05
make chapter-check CHAPTER=chapter-05
```

`chapter-prepare` 会把只读起点复制到 `.work/chapter-05/`。第一次 `chapter-check` 可能故意失败；失败信息就是本章的第一条学习线索。

每章开头的“快速开始”固定给出四个入口：

| 入口 | 用途 |
| --- | --- |
| Codespaces | 在浏览器中打开已配置的现代语言环境 |
| 练习骨架 | `labs/chapter-NN/start/`，只用于生成工作副本 |
| 结构检查 | 检查 `.work/chapter-NN/` 的归属、必需产物、TODO 与完成标记 |
| 参考实现 | `labs/chapter-NN/solution/`，完成尝试后用于复盘 |

不要直接修改 `start/` 或把 `solution/` 复制到工作区。需要重新开始时，再次执行 `chapter-prepare`；工具会明确提示现有工作，避免静默覆盖。

`chapter-check` 不执行工作区代码，因此不会变成一个隐蔽的通用代码执行器。实践章还会给出明确的 Python、Go 或 TypeScript 行为命令；结构检查和行为测试都通过，才算完成。

## 三种学习入口

### 只用浏览器

语法小练习可以在[在线练习](../playgrounds/index.md)中运行。Python 片段在浏览器内的 Pyodide 环境执行；Go 与 TypeScript 练习跳转到官方 Playground。

在线练习不读取仓库、不持有密钥，也不能替代项目测试。Agent Loop、跨语言契约、文件安全和控制面练习仍应在 Codespaces 或本地环境完成。

### 使用 Codespaces

点击章节中的 Codespaces 链接，环境启动后执行：

```bash
cd examples/repofix
make chapter-list
make chapter-prepare CHAPTER=chapter-NN
```

Codespaces 是学习工作站，不是不可信代码沙箱。Daytona 章节完成前，不得在其中运行真实模型生成或修改后的仓库代码。

### 使用本地环境

先按[仓库与云端工作区](../foundations/cloud-workspace.md)安装版本一致的 Python、Go 和 Node.js，再使用相同的 `make chapter-*` 命令。章节骨架不会依赖 OpenAI、Daytona 或云数据库凭据。

## 一章的学习循环

### 1. 先写下判断

动手前回答：

- 这个能力解决什么工程问题？
- 如果缺失，RepoFix 会怎样失败？
- 它属于模型决策、程序约束还是运行基础设施？
- 谁拥有状态，谁有权改变状态？
- 哪条测试可以推翻“它已经正确”的假设？

### 2. 只完成一个最小 TODO

骨架刻意控制在小范围：一个函数、一个状态转换、一份契约或一张决策表。先让一个失败变绿，再继续下一个，不要整章复制代码。

理论与云服务章节也有骨架，但产物是 ADR、威胁模型、迁移计划或 Smoke 记录，不会伪装成已经完成的生产实现。

### 3. 用行为证明理解

实践章至少验证：

| 类型 | 示例 |
| --- | --- |
| 成功路径 | 合法输入得到明确结果 |
| 失败路径一 | 非法路径、参数或状态被拒绝 |
| 失败路径二 | 超时、取消、旧结果或依赖故障被处理 |

“命令没有报错”和“模型说成功了”都不是充分证据。断言应覆盖外部可见行为、状态或持久化结果。

只执行该章明确列出的命令，例如：

```bash
python .work/chapter-05/exercise.py
go run .work/chapter-10/main.go
```

TypeScript 章节使用书中给出的严格类型检查入口。理论章则用 ADR、决策表或证据清单代替伪造的可执行结果。

### 4. 再对照参考实现

章节检查通过或你已经记录阻塞原因后，再查看 `solution/`：

```bash
diff -ru labs/chapter-05/start labs/chapter-05/solution
```

比较时回答：参考实现多处理了哪个失败？它的取舍是否适合你的实现？如果你的方案同样满足验收，不必为了逐行一致而重写。

### 5. 留下学习记录

在 `docs/learning-log/` 中记录：

1. 我现在能独立解释什么？
2. 哪个失败改变了我的理解？
3. 我的实现与参考实现为何不同？
4. 哪部分仍依赖 Codex 才能完成？
5. 下一章开始前必须解决什么？

## 与 Codex 协作

第一次实现核心机制时，先让 Codex 审查，不直接让它覆盖代码：

```text
Review my chapter-NN workspace against the chapter acceptance criteria.

重点检查：
- 状态和所有权是否遗漏
- 超时、取消和清理是否正确
- 是否可能在开发宿主机执行不可信代码
- 测试是否覆盖成功与失败路径

先按严重程度报告问题，不修改代码。
```

确认问题后，再授权它修改机械性部分。你仍应能解释最终 Diff 和失败语义。

## GitHub 学习追踪

仓库的“章节实践记录”Issue 模板与本页结构一致。每章创建一个 Issue，记录目标、解释题、测试证据、安全边界和复盘；代码进度与阅读进度因此不会混在一起。

状态建议保持简单：

```text
Backlog → Ready → In Progress → Review → Done
```

只有 `make chapter-check` 通过、解释题完成并留下复盘，才移动到 `Done`。

## Checkpoint 命名

目录和未来发布标签统一使用：

```text
chapter-NN-start
chapter-NN-solution
```

当前仓库始终提供 `labs/chapter-NN/start/` 与 `solution/`。Git tag 只是日后稳定发布的不可变快照，不是开始学习的前置条件；列表中不存在的 tag 不得手工伪造。

## 本章完成标准

- [ ] 从骨架生成了独立工作副本，没有直接修改 `start/`。
- [ ] 能用自己的话解释本章关键取舍。
- [ ] 实践章覆盖成功路径和两条失败路径。
- [ ] 设计章产生可审查的文档产物，没有冒充完整实现。
- [ ] `make chapter-check CHAPTER=chapter-NN` 通过。
- [ ] 实践章明确列出的语言级行为命令通过。
- [ ] 对照过参考实现并记录差异。
- [ ] GitHub Issue 中保存了证据与复盘。
