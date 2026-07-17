# RepoFix AI Agent 实践教程

[![Deploy book to GitHub Pages](https://github.com/nickdu2009/repofix-agent-book/actions/workflows/pages.yml/badge.svg)](https://github.com/nickdu2009/repofix-agent-book/actions/workflows/pages.yml)

一本面向 Go 后端工程师的 AI Agent 工程实践教程。通过主线项目 RepoFix，逐步手写 Agent Loop、构建工具系统、接入云沙箱、实现 Go 控制平面、建立评测体系，并用 TypeScript 完成可视化控制台。

仓库同时包含 `examples/repofix/` 伴随代码。教程中的核心代码进入 CI，读者可以从同一版本的书和源码开始实践。

当前哪些章节已有可运行代码、哪些仍是设计蓝图，请先看[伴随代码完成状态](docs/preface/implementation-status.md)。

在线阅读：<https://nickdu2009.github.io/repofix-agent-book/>

## 本地预览

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

浏览器打开 `http://127.0.0.1:8000`。

## 严格构建

```bash
mkdocs build --strict
```

## 运行伴随代码

```bash
cd examples/repofix
make bootstrap
make help
make test
```

默认测试覆盖 Python Agent/HTTP 服务、Go Fake 控制面、TypeScript 契约层、Eval 原型和共享 Schema，只使用 Fake Model/Fake Executor，不需要 OpenAI 或 Daytona Key，也不会执行真实模型生成的命令。故意失败的练习仓库使用安全断言目标 `make fixture-baseline`。

## 内容结构

- 导读：目标、学习方法与路线
- 第一部分：系统架构与云端工作区
- 第二部分：手写 Python Agent
- 第三部分：沙箱、Go 控制平面与事件系统
- 第四部分：评测、上下文选择与失败恢复
- 第五部分：TypeScript Web 控制台
- 第六部分：CI、部署及 ChatGPT/Codex 协作
- 附录：28 周执行安排

站点由 MkDocs Material 构建，并通过 GitHub Actions 发布到 GitHub Pages。
