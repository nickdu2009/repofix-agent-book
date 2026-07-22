# 学习与实现路线图

本页回答两个不同的问题：

1. **教材是否已经准备好？**——章节、起始骨架、参考实现和检查入口是否存在。
2. **RepoFix 是否已经实现？**——真实源码、集成测试和运行证据是否足以证明该能力可用。

本书已经提供完整的学习路径和 19 章练习骨架，但章节存在不等于对应生产能力已经完成。Daytona、PostgreSQL、SSE、完整 Web 控制台和 Railway 仍需要学习者按里程碑逐步实现。

!!! tip "怎样使用这张路线图"
    每次只推进一个里程碑。先完成 `start/` 中的练习和验收，再查看 `solution/`；进入下一里程碑前，只细化下一阶段需要的实现，不提前生成整套生产代码。

## 两类状态不要混淆

### 教材准备状态

| 状态 | 含义 |
| --- | --- |
| 已准备 | 正文、`start/`、`solution/` 和 `chapter-check` 均已进入仓库 |
| 待扩充 | 可以学习，但还会随着真实实现补充案例或故障排查 |

当前 19 章都已达到“已准备”。这只说明学习入口完整，不代表 RepoFix 已经产品化。

### 项目实现状态

| 状态 | 含义 | 读者应该怎样做 |
| --- | --- | --- |
| 可运行 | 源码、依赖、测试和命令已进入仓库 | 执行命令并完成练习 |
| 原型 | 核心机制可运行，但未达到本章最终产物 | 运行现有测试，把缺口作为实践任务 |
| 设计蓝图 | 约束和目标已写清，真实集成尚未发布 | 完成设计练习，不伪造运行结果 |

## 五个学习里程碑

| 里程碑 | 对应章节 | 学习成果 | 当前项目状态 |
| --- | --- | --- | --- |
| M1 最小安全闭环 | 第 1～3 章 | 系统边界、云端工作区、可复现缺陷仓库 | 离线 Fixture 和检查入口可运行 |
| M2 手写 Python Agent | 第 4～6 章 | Python 恢复、Agent 状态与循环、安全工具 | Fake Model 闭环可运行 |
| M3 构建可靠运行时 | 第 7～12 章 | 契约、Python 服务、Go 控制平面、Daytona、持久化与事件 | 本地 Fake 闭环可运行；真实云端与数据库集成待实践 |
| M4 评测与产品界面 | 第 13～16 章 | 评测、上下文选择、TypeScript、Web 控制台 | Eval 与 Web 原型可运行；完整案例和页面待实践 |
| M5 交付与复盘 | 第 17～19 章 | CI、部署、协作边界、完成审计 | CI 与 Pages 可运行；Railway 待实践 |

## M1：建立最小安全闭环

**开始条件**：可以使用 Git、命令行和 GitHub Codespaces，不需要模型 API Key。

**需要亲自完成**：

- 写清 RepoFix 组件所有权和信任边界；
- 验证 Codespaces 中的工具版本与 Secret 边界；
- 证明缺陷仓库在修改前失败、最小修复后通过。

**可以让 Codex 协助**：检查目录结构、补充 CI 模板、审查测试是否真正覆盖缺陷。

**通过证据**：第 1～3 章的 `chapter-check` 全部通过，并能解释为什么 Codespaces 不是不可信代码沙箱。

**进入 M2 前**：不要接入真实模型；先保留一个完全确定、可以反复复现的失败案例。

## M2：手写 Python Agent

**开始条件**：M1 通过，并能区分“Agent 声称完成”和“测试证明完成”。

**需要亲自完成**：

- `AgentState`、Step 记录和最大步数预算；
- 不依赖 Agent 框架的决策循环；
- 文件路径校验、工具分发和 Stop Condition；
- Fake Model 的成功、失败与预算耗尽测试。

**可以让 Codex 协助**：补参数化测试、Ruff 配置、重复 DTO 和失败案例审查。

**通过证据**：第 4～6 章检查通过，Fake 闭环可以修改练习输入并由独立验证器确认结果；所有测试不访问网络。

**进入 M3 前**：你应能画出一次 Step 的输入、模型动作、工具结果和状态变化，并解释每个停止分支。

## M3：构建可靠运行时

**开始条件**：M2 的 Agent Core 稳定，路径逃逸、无效工具和预算耗尽都有测试。

**需要亲自完成**：

- 第一份跨语言 Run/Event/Error 契约；
- Python 服务边界与 Go Run 状态机；
- 第一个真实 Daytona Adapter；
- PostgreSQL migration、事件顺序、恢复与 SSE 重放。

**可以让 Codex 协助**：生成重复契约类型、补 HTTP 测试、整理 migration、审查取消和清理路径。

**通过证据**：真实模型的文件和命令工具只在一次性 Daytona Sandbox 中运行；取消、失败和成功都会清理资源；服务重启后 Run 有明确恢复结果。

**当前缺口**：Daytona 真实 Adapter、PostgreSQL Repository、SSE 重连集成测试尚未实现。完成这些证据前，本里程碑不能标记为通过。

## M4：用评测驱动产品界面

**开始条件**：M3 至少有一个可重复的沙箱闭环，事件契约已经稳定。

**需要亲自完成**：

- 第一个独立评测运行器和隐藏 Oracle；
- 上下文选择、预算和失败重规划；
- TypeScript 运行时校验与 SSE Reducer；
- 创建任务、查看轨迹、Diff 和测试报告的最小页面。

**可以让 Codex 协助**：扩展 Fixture、生成基础组件、补 Vitest/Playwright、整理评测报告。

**通过证据**：至少 3～5 个稳定案例可以重复运行；非法后端数据不会进入前端状态；关键页面有端到端测试。

**当前缺口**：当前只有最小 Eval 和 Web 原型，完整案例集、Artifact 视图与 Playwright E2E 尚未实现。

## M5：交付、部署与复盘

**开始条件**：核心路线已有稳定评测结果，而不是只有一次成功演示。

**需要亲自完成**：

- 确定 CI 分层、Secret 边界和发布门槛；
- 完成 Railway 服务、数据库 migration 和受保护环境；
- 演练失败部署、回滚和服务恢复；
- 对照完成标准诚实记录仍未具备的能力。

**可以让 Codex 协助**：Dockerfile、Actions、部署文档、Smoke 脚本和发布 Diff 审查。

**通过证据**：固定版本可以从空环境部署；Smoke、回滚和恢复都有日志；线上版本能追溯到 Git 提交与评测报告。

**当前缺口**：GitHub Actions 和 Pages 已运行，Railway 镜像、真实部署、migration 与恢复演练尚未实现。

## 当前能力证据矩阵

| 能力 | 项目状态 | 当前证据 | 尚未完成 |
| --- | --- | --- | --- |
| 工作区与缺陷 Fixture | 可运行 | `make bootstrap`、`make fixture-baseline` | 更多语言 Fixture |
| 章节学习骨架 | 可运行 | 19 个 `start/`、`solution/` 与 `make chapter-check` | 随实现成熟持续扩充行为测试 |
| Python Agent Core | 可运行 | 核心与 Adapter 离线测试、Ruff、零网络 Demo | 可恢复工具错误、费用预算 |
| Python HTTP 服务 | 可运行 | Fake Runner API、取消、顶层错误契约、Tool Gateway HTTP Client | Live Model 组合根、模型错误分类、Step 事件上报 |
| 共享 Run/Event 契约 | 可运行 | Run、Event、Error、Artifact、Tool Call/Result Schema 及正反例 | Task/Agent HTTP Schema |
| Go 控制平面 | 可运行的 Fake 闭环 | 状态机、内存仓库、Fake Sandbox/Agent/Verifier、Tool Gateway Handler 测试 | 完整公网 HTTP、PostgreSQL、真实进程恢复 |
| Daytona Adapter | 设计蓝图 | 生命周期、安全策略和 Smoke 设计 | 锁定 SDK 的真实 Adapter 与手动 Smoke |
| PostgreSQL 与 SSE | 设计蓝图 | DDL、事件顺序和重放协议 | migration、Repository 与重连集成测试 |
| Eval Runner | 原型 | 单案例、独立 Oracle 与防作弊测试 | 3～5 个 Daytona 案例、JSONL 聚合报告 |
| TypeScript 契约层 | 可运行 | 锁定依赖、Zod/API/Reducer/SSE 测试 | 从 JSON Schema 自动防漂移 |
| React 控制台 | 原型 | 最小 App、生产构建 | 三个页面、Artifact 视图、Playwright E2E |
| Railway 发布 | 设计蓝图 | CI、密钥和回滚要求 | 镜像、migration、受保护环境和真实部署 |

## 推进规则

1. 正文按能力组织，日期安排只放在[28 周执行安排](../appendix/28-week-plan.md)。
2. 只提前细化下一个里程碑，不提前让 Codex 完成全部核心实现。
3. Agent Loop、Stop Condition、Go 状态机、首个 Sandbox Adapter 和首个 Eval Runner 必须亲自实现。
4. CI、Dockerfile、重复类型、基础页面和文档整理可以委托 Codex，但必须审查 Diff。
5. 只有源码、测试和运行证据同时存在，项目状态才能升级。
6. Daytona 完成前，真实模型不得在 Codespaces 或本地工作站执行仓库代码和命令。

## 命令与 Checkpoint 规则

文档中的命令分为两类：

- **当前命令**：已存在于 `examples/repofix/Makefile` 或对应 `package.json`，复制后应得到文档所述结果。
- **目标命令**：章节明确写为“完成后增加”或“目标 Checkpoint”，当前不得执行。

用下面命令查看真实入口：

```bash
cd examples/repofix
make help
```

`labs/chapter-NN/solution/` 是小练习的参考答案，不代表最终 RepoFix 的生产实现。章节 tag 只在源码和验收命令同时稳定后发布：

```bash
git fetch --tags
git tag --list 'chapter-*'
```

列表中没有的 tag 就没有发布。当前可以直接使用 `labs/chapter-NN/start/` 与 `labs/chapter-NN/solution/`；未来稳定快照统一命名为 `chapter-NN-start` 和 `chapter-NN-solution`。

如果本页、Makefile、CI 和正文不一致，默认按“尚未完成”处理，并提交文档缺陷 Issue。
