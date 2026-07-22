# 第 02 章 · 仓库与云端开发工作区

## 快速开始

[打开通用 Codespaces](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json){ .md-button .md-button--primary }

| 用途 | 路径 |
| --- | --- |
| 只读工作区骨架 | `examples/repofix/labs/chapter-02/start/` |
| 你的练习副本 | `examples/repofix/.work/chapter-02/` |
| 可对照的参考配置 | `examples/repofix/labs/chapter-02/solution/` |

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-02
make chapter-check CHAPTER=chapter-02
```

`chapter-prepare` 会拒绝覆盖已有 `.work/chapter-02/`。在该工作副本中完成版本和工作区 TODO；只有自己的检查结果可解释后，再查看只读 `solution/`。后文的完整伴随项目只是参考实现，不替代本章操作。

## 本章目标

完成本章后，你将拥有一个可复现的 RepoFix 开发环境，并能够：

- 从 Codespaces 或本地 checkout 进入同一个伴随项目；
- 用统一的 Makefile 命令安装工具并运行测试；
- 确认语言版本与本书基线一致；
- 保证 API Key 不进入 Git，也不进入不可信 Sandbox。

## 前置条件与本章产物

前置条件：GitHub 账号、Git 基础，以及已经阅读[系统架构与信任边界](architecture.md)。

本章产物：

```text
examples/repofix/
├── .devcontainer/devcontainer.json
├── contracts/
├── docs/
│   ├── adr/
│   └── learning-log/
├── fixtures/buggy-calculator/
├── services/agent/
├── .gitignore
├── Makefile
└── README.md
```

## 1. 固定版本基线

本版教程使用当前稳定或 LTS 主版本，并在一个教程版本内保持固定；不使用预发布版本，也不追逐每周补丁更新：

| 工具 | 教程基线 | 用途 |
| --- | --- | --- |
| Python | 3.14.x | Agent、服务和评测 |
| Go | 1.26.x | 控制平面与 Daytona Go SDK |
| Node.js | 24.x LTS | TypeScript Web 工具链 |
| TypeScript | 7.0.2 | Web 编译与类型检查 |
| pytest | 9.1.1 | Python 测试 |
| Ruff | 0.15.22 | Python Lint |
| FastAPI | 0.139.2 | Python HTTP 边界 |
| Pydantic | 2.13.4 | HTTP 与配置校验 |
| Uvicorn | 0.51.0 | Python ASGI Server |
| HTTPX | 0.28.1 | 离线 ASGI 测试 |

版本依据来自各项目的稳定发布信息：[Go Release History](https://go.dev/doc/devel/release)、[Python Downloads](https://www.python.org/downloads/)、[Node.js Releases](https://nodejs.org/en/about/previous-releases) 和 [TypeScript](https://www.typescriptlang.org/)。Python 3.15 与 Node.js 26 当前不作为教程基线：前者仍是预发布系列，后者仍处于 Current 而不是 LTS。

Python、Go 和 Node.js 使用表中的主版本基线；TypeScript、pytest、Ruff、FastAPI、Pydantic、Uvicorn 和 HTTPX 则由项目文件固定到表中的精确版本。这里的“现代”指稳定语言版本、严格类型和当前工程工具，不代表每个示例都必须使用最新语法。升级基线应作为独立 Issue，先在全部 Checkpoint 上运行 CI，再修改书中版本。

## 2. 推荐方式：GitHub Codespaces

使用本章“快速开始”中的通用入口创建 Codespace。

在创建页面确认：

- Repository：`nickdu2009/repofix-agent-book`；
- Branch：与你阅读的书籍 release 对应，学习最新内容时选 `main`；
- Dev container：`examples/repofix/.devcontainer/devcontainer.json`；
- Machine type：入门阶段使用最小规格即可。

容器首次创建会自动执行 `make bootstrap`。打开终端验证工作目录：

```bash
pwd
```

路径末尾应为：

```text
/examples/repofix
```

如果从 GitHub 的普通 **Code → Codespaces** 按钮创建，且终端落在仓库根目录，手动进入：

```bash
cd examples/repofix
make bootstrap
```

## 3. 本地开发方式

本地已经安装 Python 3.14、Go 1.26、Node.js 24 LTS 和 GNU Make 时，可以执行：

```bash
git clone https://github.com/nickdu2009/repofix-agent-book.git
cd repofix-agent-book/examples/repofix
make bootstrap
make test
```

本地版本不同，不要通过删除 `check-tools` 绕过检查；优先使用 Codespaces，或用版本管理器安装本书基线。

## 4. Bootstrap 做了什么

`make bootstrap` 会：

1. 检查 Python、Go 和 Node.js 主版本；
2. 在伴随项目根目录创建 `.venv/`；
3. 安装 Agent 的固定 Python 开发/服务依赖和 JSON Schema Validator；
4. 用 `npm ci` 安装锁文件中的 Web 依赖；
5. 写入本地就绪标记，依赖文件未变化时不会重复安装。

执行：

```bash
make bootstrap
```

成功输出中应包含：

```text
Toolchain check passed: Python 3.14, Go 1.26, Node.js 24 LTS
RepoFix bootstrap complete. Run: make test
```

然后运行可信的项目测试：

```bash
make test
```

当前 Checkpoint 会运行 Python Agent/HTTP 服务、Go Fake 控制面、Web 契约层、Eval 原型和共享契约。不要把测试数量当成稳定接口：验收看退出码与各分组结果均通过，且没有 OpenAI 或 Daytona 请求。故意损坏的教学 Fixture 不属于默认测试目标。

## 5. 统一命令约定

| 命令 | 当前行为 | 成功含义 |
| --- | --- | --- |
| `make bootstrap` | 建立固定版本工具环境 | 开发环境可复现 |
| `make test` | 运行 Python、Go、Web、Eval 和契约测试 | 当前零云端伴随代码全部通过 |
| `make lint` | 对现有 Python 路径运行 Ruff | 静态检查通过 |
| `make contract-test` | 校验 Schema 本身及正反例 payload | 共享状态与事件契约拒绝非法数据 |
| `make fake-e2e` | 运行 Go Fake Agent/Sandbox/Verifier 闭环 | 只有独立验证后才成功，且 Sandbox 先清理 |
| `make eval-unit` | 运行独立 Oracle 和防作弊测试 | 修改测试与针对公开样例过拟合均失败 |
| `make fixture-baseline` | 确认练习仓库初始测试失败 | Fixture 确实含有目标缺陷 |
| `make fixture-test` | 直接测试练习仓库 | 修复前失败，修复后通过 |

后续章节增加 `make dev`、`make eval-smoke` 和跨语言测试时，README、CI 与 Codex 仍必须调用相同 Makefile 入口。

## 6. 密钥从第一天就分离

Bootstrap 不需要任何 API Key。进入真实模型章节后，把密钥配置为 Codespaces Secret，而不是写入仓库文件：

```text
OPENAI_API_KEY
OPENAI_MODEL
DAYTONA_API_KEY
```

规则：

- 不提交 `.env`；伴随项目的 `.gitignore` 已忽略它；
- 单元测试不读取真实 Key；
- 日志不打印环境变量；
- Daytona Sandbox 不继承 Codespaces 环境；
- 主 GitHub Token 永远不进入目标仓库 Sandbox。

## 7. 建立第一个 GitHub Project

在 GitHub Repository 页面选择 **Projects → New project**，使用 Board 模板，并添加：

```text
Status:          Backlog / Ready / In Progress / Review / Done
Work Mode:       Learn Manually / Pair with Codex / Delegate / Review Only
Language Focus:  Python / Go / TypeScript / Architecture / Evaluation
Milestone:       Bootstrap / Agent MVP / Sandbox / Control / Eval / Web / Release
```

第一个 Issue 参考[怎样完成一章](../preface/chapter-workflow.md)中的 GitHub 学习追踪方式，Done when 至少包含：

```text
make bootstrap
make test
```

以及“能够解释为什么 Daytona 前只能使用 FakeModel/FakeExecutor”。

## 验收

在新的终端执行：

```bash
cd /workspaces/repofix-agent-book/examples/repofix 2>/dev/null || cd examples/repofix
make bootstrap
make test
make contract-test
git status --short
```

验收条件：

- [ ] Bootstrap 显示固定版本检查通过。
- [ ] `make test` 全部通过且没有外部模型请求。
- [ ] `make contract-test` 输出 `validated 6 contract schemas and positive/negative examples`。
- [ ] `git status --short` 不显示 `.venv`、缓存或密钥。
- [ ] 可以指出书籍目录和伴随项目目录。
- [ ] 已创建第一篇学习日志或 Bootstrap Issue。

## 故障排查 {#workspace-troubleshooting}

| 症状 | 诊断 | 处理 |
| --- | --- | --- |
| `RepoFix requires Python 3.14.x` | `python3 --version` | 重新使用指定 Dev Container，不删除版本检查 |
| Codespace 打开在仓库根目录 | `pwd` | `cd examples/repofix`，下次使用本页预配置入口 |
| pip 下载失败 | `python3 -m pip index versions pytest` | 检查网络/代理后重试 `make bootstrap`，不要提交 `.venv` |
| `make test` 找不到 Fixture | `git status` 与 `git rev-parse --abbrev-ref HEAD` | 切到正确 Checkpoint 并拉取完整仓库 |
| 测试发起真实模型请求 | 检查测试是否读取 API Key | 立即停止，改用 FakeModel/FakeExecutor |
| `.env` 出现在 Git 状态中 | `git check-ignore -v .env` | 确认当前目录和 `.gitignore`，不要暂存文件 |

## 练习

1. 暂时把 Node 主版本检查改成错误版本，观察 `make bootstrap` 如何失败，然后恢复。
2. 第二次运行 `make bootstrap`，解释为什么它不重复安装依赖。
3. 在不写入真实值的前提下，列出 RepoFix 各阶段需要的 Secret 及其使用者。

## Checkpoint

保存学习日志，并提交工作区配置。完成 Checkpoint 的最小证据是 `make bootstrap && make test` 成功。下一章进入[第一个缺陷练习仓库](fixture.md)。
