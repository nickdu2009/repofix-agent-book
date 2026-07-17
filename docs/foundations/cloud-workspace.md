# 仓库与云端开发环境

### 4.1 推荐目录

```text
repofix/
├── .devcontainer/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── workflows/
├── apps/
│   └── web/
├── services/
│   ├── agent/
│   └── control/
├── contracts/
├── evals/
│   ├── cases/
│   └── reports/
├── fixtures/
│   └── buggy-calculator/
├── docs/
│   ├── architecture/
│   ├── decisions/
│   └── learning-log/
├── AGENTS.md
├── Makefile
└── README.md
```

### 4.2 统一命令

为人和 Codex 提供一致入口：

```bash
make bootstrap
make dev
make test
make lint
make eval-smoke
make eval-full
```

不要让 README、CI 和 Codex 分别使用不同命令。

### 4.3 GitHub Projects 字段

建议设置：

```text
Status:
  Backlog / Ready / In Progress / Review / Done

Work Mode:
  Learn Manually / Pair with Codex / Delegate to Codex / Review Only

Language Focus:
  Python / Go / TypeScript / Architecture / Evaluation

Milestone:
  Bootstrap / Agent MVP / Sandbox / Control Plane / Eval / Web / Release
```

Issue 完成条件至少包含：

- 需要学习的概念。
- 需要实现的能力。
- 必须运行的测试。
- 可交给 Codex 的范围。
- 自己必须能够解释的内容。
