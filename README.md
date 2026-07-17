# RepoFix AI Agent 实践教程

[![Deploy book to GitHub Pages](https://github.com/nickdu2009/repofix-agent-book/actions/workflows/pages.yml/badge.svg)](https://github.com/nickdu2009/repofix-agent-book/actions/workflows/pages.yml)

一本面向 Go 后端工程师的 AI Agent 工程实践教程。通过主线项目 RepoFix，逐步手写 Agent Loop、构建工具系统、接入云沙箱、实现 Go 控制平面、建立评测体系，并用 TypeScript 完成可视化控制台。

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
