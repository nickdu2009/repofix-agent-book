# 系统架构与信任边界

## 本章目标

完成本章后，你能够：

- 从一次 Run 解释 Web、Go、Python、PostgreSQL 与 Daytona 的协作；
- 明确每种状态和外部资源的唯一所有者；
- 识别模型输出、目标仓库、开发环境和 Sandbox 的信任边界；
- 判断一项新功能应该放在哪个组件中。

## 前置条件与本章产物

前置阅读：[教程目标与学习路线](../preface/learning-path.md)。

本章产物是一份架构决策草稿 `examples/repofix/docs/adr/0001-runtime-ownership.md`。本章不启动任何服务。

## 1. 一次 Run 的最终形态

```text
TypeScript Web
  │  创建任务、订阅 SSE、取消 Run
  ▼
Go Control Plane ───────────────► PostgreSQL
  │  Run 状态、期限、事件、Sandbox ID
  │
  ├──► Python Agent Service ────► OpenAI API
  │      模型决策、上下文、Agent Loop
  │
  └──► Daytona Sandbox
         克隆仓库、文件工具、测试、Diff
```

Go 是编排与持久状态的权威，Python 是一次 Run 内模型决策的权威，Daytona 是唯一允许执行目标仓库代码的位置。

## 2. ADR-001：运行时所有权

全书采用以下决策，除非后续通过新的 ADR 显式替换：

| 资源或状态 | 唯一所有者 | 其他组件如何使用 |
| --- | --- | --- |
| Task、Run、终态 | Go Control Plane | Web 发请求；Python 上报结果，不能直接写终态 |
| Sandbox 创建、ID、删除 | Go Control Plane | Python 通过受控 Go Tool Gateway 使用能力句柄 |
| Agent Loop、模型上下文 | Python Agent Service | Go 启动、取消并接收领域事件 |
| 目标仓库文件与进程 | Daytona Sandbox | 只能通过受控文件/测试工具访问 |
| Run、Step、Event、Artifact | PostgreSQL，由 Go 写入 | Web 只读；Python 不直接连接数据库 |
| 页面状态 | TypeScript Web | 由 REST 快照与 SSE 事件派生 |

这个决定解决四个关键问题：

1. 只有 Go 持有 Daytona 主凭据并负责最终清理。
2. Python 崩溃不会让 Run 的持久状态消失。
3. Python 不能绕过工具策略直接调用 Daytona 任意命令。
4. 每个状态只有一个写入权威，避免 Go 与 Python 互相覆盖。

早期 Python 章节中的 `FakeExecutor` 只是进程内测试替身，不代表最终部署所有权。接入真实 Sandbox 后，Python 面向 Go Tool Gateway 的受控能力接口编程，Go Adapter 才调用 Daytona API。

## 3. 一次成功 Run 的事件顺序

| 顺序 | 发起者 | 动作 | 持久化证据 |
| --- | --- | --- | --- |
| 1 | Web | 创建 Task 与 Run | `runs` 中的 `pending` 记录 |
| 2 | Go | 创建一次性 Sandbox | `sandbox.created` 与 Sandbox ID |
| 3 | Go | 请求 Python 启动 Agent Loop | `run.started` |
| 4 | Python | 请求模型选择下一动作 | Token、耗时和请求 ID 摘要 |
| 5 | Python | 通过 Gateway 调用受限工具 | `step.started`、`tool.started`、`tool.completed` |
| 6 | Go | 在 Daytona 中执行文件或测试操作 | ToolResult、截断标记、退出码 |
| 7 | Python | 请求 `finish` | 完成摘要，不直接成为成功状态 |
| 8 | Go | 独立验证当前 revision 的测试 | `tests.completed` 或继续/失败 |
| 9 | Go | 收集 Diff 并删除 Sandbox | `patch.created`、Artifact，以及 `sandbox.deleted` 或 `sandbox.cleanup_failed` |
| 10 | Go | 写入最终状态 | `run.succeeded` 或其他终态事件 |

失败、取消或超时会跳过业务后续步骤，但不能跳过第 9 步的清理；终态事件只能在清理结果已经记录后写入。

## 4. 信任边界

| 区域 | 信任级别 | 可能包含什么 | 主要规则 |
| --- | --- | --- | --- |
| Codespaces/本地工作站 | 可信开发环境 | GitHub Token、API Key、源码 | 不执行模型生成或模型修改后的代码 |
| 模型响应 | 不可信数据 | 工具名、参数、完成声明 | Schema 校验、预算、权限和状态校验 |
| 目标仓库 | 不可信数据与代码 | Prompt Injection、脚本、依赖 | 只在一次性 Daytona 中读取和执行 |
| Daytona Sandbox | 可丢弃隔离区 | 目标仓库和运行产物 | 最小密钥、限时限额、显式删除 |
| 数据库与事件日志 | 受保护系统数据 | 轨迹、Diff、错误、成本 | 脱敏、大小限制、访问控制和保留策略 |

!!! danger "仓库文本也可能是 Prompt Injection"
    README、注释、Issue 和测试中的“请读取密钥”“忽略系统规则”等文字只是仓库数据，永远不能提升为系统指令。

## 5. 最小威胁模型

| 威胁 | 示例 | 必须实现的控制 |
| --- | --- | --- |
| 宿主机命令执行 | 模型写入恶意测试后运行 `pytest` | Daytona 前只用 Fake；真实执行只在 Sandbox |
| 路径逃逸 | `../../.env`、符号链接指向工作区外 | 根目录约束、拒绝敏感路径、文件工具测试 |
| 凭据泄露 | 将 GitHub Token 放进 Sandbox 或模型上下文 | 最小临时凭据、日志脱敏、禁止读取 Secrets |
| 网络滥用 | 访问内网地址或下载任意脚本 | 默认关闭出站网络，按需要开放域名 |
| 资源耗尽 | 无限循环、海量输出、磁盘写满 | Run deadline、进程超时、CPU/内存/磁盘和输出上限 |
| 伪造成功 | 模型声称测试通过，或修改测试后通过 | 固定可信测试、revision 校验、独立评测 Sandbox |
| 清理遗漏 | 服务崩溃后 Sandbox 留存 | `finally` 删除、auto-delete、孤儿清理任务 |

## 6. 为什么不把所有内容写成一个服务

单进程 MVP 确实更短，但本书需要学习两类不同问题：

- Python 擅长模型 SDK、Prompt、上下文与评测实验；
- Go 擅长长期运行的状态、并发控制、取消、恢复与 SSE。

拆分服务不是目的。只有当 Python 的确定性 Agent MVP 已经通过测试后，才引入 Go 和 HTTP 边界。这样每次复杂度增加都有可比较的基线。

## 验收

不看本页，画出一次 Run，并回答：

- [ ] 谁可以把 Run 写成 `succeeded`？
- [ ] 谁持有 Daytona 凭据并删除 Sandbox？
- [ ] Python 如何请求文件或测试工具？
- [ ] Go 崩溃恢复时从哪里获得 Run 与 Sandbox ID？
- [ ] 哪些内容必须被视为不可信输入？

任何答案出现两个“所有者”，都说明边界仍不明确。

## 故障排查

| 症状 | 架构原因 | 调整 |
| --- | --- | --- |
| Go 和 Python 都能写 Run 终态 | 缺少单一写入权威 | Python 只上报结果，Go 验证并持久化转换 |
| Python 必须持有 Daytona 主 Key | Gateway 边界被绕过 | 让 Go 提供受限能力接口 |
| 取消后仍有测试进程运行 | 取消信号没有传到 Sandbox 命令 | 为 Run、工具与进程建立同一 deadline 链 |
| 重启后不知道删除哪个 Sandbox | Sandbox ID 没有持久化 | Provision 成功后与 Run 原子记录 |

## 练习

1. 把“Python 直接写 PostgreSQL”放进架构，列出三个新故障模式。
2. 为“模型读取 `.env`”分别写预防、检测和恢复控制。
3. 设计一个取消发生在模型响应期间的事件序列。

## Checkpoint

将所有权表和选择理由写入 `docs/adr/0001-runtime-ownership.md`。这是一份设计 Checkpoint；下一章开始创建可运行工作区。
