# CI、部署与密钥管理

### 16.1 云端工具分工

```text
GitHub Repository   代码唯一来源
GitHub Projects     学习与任务跟踪
GitHub Codespaces   开发工作站
GitHub Actions      测试与评测
Railway             Go、Python、Web、PostgreSQL
Daytona             Agent 隔离执行环境
OpenAI API          在线模型
```

### 16.2 部署流程

```text
创建分支
  → 开发和测试
  → Pull Request
  → GitHub Actions
  → Codex/人工审查
  → 合并 main
  → Railway 自动部署
  → 部署后 Smoke Test
```

### 16.3 密钥

- 开发密钥放 Codespaces Secrets。
- CI 密钥放 GitHub Actions Secrets。
- 部署密钥放 Railway Variables。
- 开发、测试和生产使用不同密钥。
- 真模型评测必须显式触发，避免每个提交都产生费用。
- Daytona 沙箱只获得完成当前任务必需的最小权限。
