# CI、Railway 部署与密钥

发布流水线分成“永远免费且确定性”和“需要云资源且显式触发”两条路径。普通提交不能意外调用模型或创建 Sandbox。

## 本章契约

- **前置**：Python、Go、TypeScript 和契约测试均可在本地独立运行。
- **产物**：应用 CI、容器镜像、Railway 服务、迁移、Smoke 和回滚手册。
- **验收**：从空环境构建；部署失败不会破坏上一版本；公开入口有认证、限流和费用上限。

!!! info "当前范围"
    GitHub Actions 已验证书籍、Python、Go、TypeScript、共享契约、Fixture 与 Fake E2E。Railway 服务、镜像、migration 和真实 Smoke 仍是本章目标设计，不应被描述成已经部署。

## GitHub Actions 分层

| Workflow | 触发 | 内容 | 云端费用 |
| --- | --- | --- | --- |
| Book | PR、main | `mkdocs build --strict` | 无 |
| Companion CI | PR、main | Python/Go/TS/契约/Fake E2E | 无 |
| Sandbox Contract | PR 或手动 | Fake Adapter；可选 Daytona Smoke | 默认无 |
| Live Eval | 手动、受保护环境 | 3～5 个真实案例 | 有 |
| Full Eval | 发布前或计划任务 | 完整评测及基线比较 | 有 |

真实模型 Workflow 必须同时满足：手动触发、受保护环境、费用预算和并发限制。

## CI 验证命令

```bash
make bootstrap
make lint
make test
make contract-test
make fake-e2e
mkdocs build --strict
```

关键书内代码来自伴随源码或由测试引用，避免 Markdown 示例与实际实现分叉。

## Railway 服务

```text
repofix-control   Go，对外 API 与 SSE
repofix-agent     Python，仅内网访问
repofix-web       静态 Web 或 Node 服务
PostgreSQL        持久化
```

每个服务明确配置：根目录、构建命令、启动命令、`PORT`、健康检查、内部 URL、资源上限和发布策略。数据库迁移作为独立、幂等的发布步骤，只允许一个实例执行。

## 环境变量矩阵

| 变量 | Control | Agent | Web | Sandbox |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | 是 | 否 | 否 | 否 |
| `DAYTONA_API_KEY` | 是 | 否 | 否 | 否 |
| `OPENAI_API_KEY` | 否 | 是 | 否 | 否 |
| `AGENT_INTERNAL_URL` | 是 | 否 | 否 | 否 |
| `CONTROL_PUBLIC_URL` | 否 | 否 | 构建时公开值 | 否 |

任何主 GitHub Token、Railway Token、OpenAI Key 或 Daytona Key都不得进入 Sandbox、Artifact、事件或前端构建产物。

## 发布顺序

1. 构建不可变镜像并记录 Git SHA。
2. 在临时数据库验证 migration。
3. 发布 Agent，并通过 `/readyz`。
4. 发布 Control，执行内部 Agent 合约 Smoke。
5. 发布 Web。
6. 运行不调用真实模型的 Fake Smoke。
7. 人工批准后运行一个受预算限制的真实案例。

失败时回滚到上一镜像；数据库迁移必须向前兼容，不能依赖自动降级破坏性 Schema。

## 公开部署安全

第一版公开演示至少需要：

- 登录或演示邀请码。
- 用户、IP 和全局 Run 速率限制。
- 每用户并发、Token、时长和 Sandbox 配额。
- 仅允许支持的公开 Git 仓库 URL，阻止内网/元数据地址。
- 日志脱敏和 Artifact 保留期限。
- 费用告警与紧急停止开关。

## Smoke、监控与回滚

Smoke 验证创建 Fake Run、SSE、取消和 Artifact；监控至少覆盖 Run 成功率、API 延迟、Sandbox 孤儿数、事件积压、模型错误率和费用。

回滚演练需要回答：当前镜像 SHA、最新 migration、未完成 Run 如何处理、孤儿 Sandbox 谁清理、评测是否暂停。

## 故障排查与验收

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| PR 意外产生模型费用 | Live Eval 条件过宽 | 要求手动触发和受保护环境 |
| Control 健康但任务全失败 | 只做存活检查 | readiness 校验 Agent 和必要配置 |
| 回滚后旧服务读不了数据 | migration 非向前兼容 | 使用 expand/contract 迁移 |

验收：任意贡献者在没有云端 Secret 时都能完成 Companion CI；只有授权维护者能启动付费测试和部署。
