# 伴随代码完成状态

本页区分“现在 clone 后就能运行的 Checkpoint”和“正文中的目标设计”。教程可以先讲最终架构，但验收命令只有在对应源码、测试和 CI 已经进入伴随项目后，才算发布。

## 状态含义

| 状态 | 含义 | 读者应该怎样做 |
| --- | --- | --- |
| 可运行 | 源码、依赖、测试和命令已进入仓库 | 执行命令并完成练习 |
| 原型 | 核心机制可运行，但未达到本章最终产物 | 运行现有测试，并把缺口作为本章任务 |
| 设计蓝图 | 约束和目标已写清，云端或生产实现尚未发布 | 不执行目标命令，不伪造空 target |

## 当前矩阵

| 能力 | 状态 | 当前证据 | 尚未完成 |
| --- | --- | --- | --- |
| 工作区与缺陷 Fixture | 可运行 | `make bootstrap`、`make fixture-baseline` | 更多语言 Fixture |
| 章节学习骨架 | 可运行 | 19 个 `start/`、`solution/` 与 `make chapter-check` | 随实现成熟持续扩充行为测试 |
| Python Agent Core | 可运行 | 26 条核心/Adapter 离线测试、Ruff、零网络 Demo | 可恢复工具错误、费用预算 |
| Python HTTP 服务 | 可运行 | 5 条 Fake Runner API 测试、取消、顶层错误契约 | Live Tool Gateway Client、错误分类、Step 事件上报 |
| 共享 Run/Event 契约 | 可运行 | 4 份 Draft 2020-12 Schema 及正反例 | 完整 Task/Agent/Tool HTTP Schema |
| Go 控制平面 | 可运行的 Fake 闭环 | 状态机、内存仓库、Fake Sandbox/Agent/Verifier 测试 | HTTP、PostgreSQL、真实进程恢复 |
| Daytona Adapter | 设计蓝图 | 生命周期、安全策略和 Smoke 设计 | 锁定 SDK 的真实 Adapter 与手动 Smoke |
| PostgreSQL 与 SSE | 设计蓝图 | 完整 DDL、事件顺序和重放协议 | migration、Repository 与重连集成测试 |
| Eval Runner | 原型 | 1 个案例、4 条独立 Oracle/防作弊测试 | 3～5 个 Daytona 案例、JSONL 聚合报告 |
| TypeScript 契约层 | 可运行 | 锁定依赖、12 条 Zod/API/Reducer/SSE 测试 | 从 JSON Schema 自动防漂移 |
| React 控制台 | 原型 | 最小 App、生产构建 | 三个页面、Artifact 视图、Playwright E2E |
| Railway 发布 | 设计蓝图 | CI/密钥/回滚要求 | 镜像、migration、受保护环境和真实部署 |

## 命令规则

仓库根文档中出现的命令分为两类：

- **当前命令**：已存在于 `examples/repofix/Makefile` 或对应 `package.json`，复制后应得到文档所述结果。
- **目标命令**：章节明确写为“完成后增加”或“目标 Checkpoint”，当前不得执行。

用下面命令查看真实入口，不要根据正文猜测：

```bash
cd examples/repofix
make help
```

若状态表、Makefile、CI 和正文不一致，以“不能宣称已完成”为默认判断，并提交文档缺陷 Issue。

## 骨架、参考实现与发布 Checkpoint

`labs/chapter-NN/solution/` 是本章小练习的参考答案，不代表最终 RepoFix 的完整生产实现。尤其是 Daytona、PostgreSQL/SSE 与 Railway 章节，参考答案是可审查的设计或 Fake 合约；是否完成真实集成仍以上表为准。

章节 tag 只在源码和验收命令同时稳定后发布：

```bash
git fetch --tags
git tag --list 'chapter-*'
```

列表中没有的 tag 就没有发布。当前分支上的“可运行”状态由 CI 证明；`chapter-NN-start` / `chapter-NN-solution` tag 会在后续 release 中逐章补齐。`start` 是可动手的骨架，`solution` 是用于复盘和比较的参考实现。
