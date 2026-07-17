# v1.0 验收与后续方向

“完成”必须由命令、测试和可追溯 Artifact 证明，而不是一张功能清单。

## 本地确定性验收

在不配置 OpenAI 或 Daytona Key 的全新 Codespace 中：

```bash
cd examples/repofix
make bootstrap
make lint
make test
make contract-test
make fake-e2e
```

全部通过后，证明领域模型、Agent Loop、状态机、契约、SSE Reducer 和 Fake 全栈闭环可复现。

## 真实环境 Smoke

Daytona Adapter 与 Live Eval 发布后，由维护者显式执行目标命令：

```bash
RUN_DAYTONA_SMOKE=1 make sandbox-smoke
RUN_LIVE_EVAL=1 make eval-smoke
```

Smoke 必须生成：Run ID、源码 commit、模型和 Prompt 版本、Sandbox 清理结果、patch、独立测试报告、Token 和费用摘要。

当前 Makefile 故意没有 `sandbox-smoke` 和 `eval-smoke`；在实现与受保护 CI 环境完成前，不增加空 target，也不要执行这两条命令。

## 功能验收

- 输入受支持的公开 GitHub 仓库和 Issue 能创建 Run。
- Agent 只在独立 Daytona Sandbox 执行不可信代码。
- 测试未通过或测试后再次修改代码时不能完成。
- Go 支持取消、超时、幂等；重启后会保留事实，并将无法安全续跑的 Run 明确失败和清理。
- SSE 重连不会丢失或重复应用事件。
- Web 展示轨迹、Diff、测试、错误、成本和终态。
- Eval 使用独立验证 Sandbox 和隐藏测试。
- 发布流程具有 Smoke、回滚、限流和费用上限。

## 可靠性演练

在发布前主动执行：

1. 模型请求超时。
2. 测试进程超时。
3. 用户在测试中取消。
4. Python 服务崩溃。
5. Go 服务在事件提交后崩溃。
6. SSE 断线重连。
7. Sandbox 删除失败。

每个演练都应有预期状态、事件、清理行为和测试文件。

## 作品集交付物

- 在线书籍和架构决策记录。
- 可复现的伴随代码 checkpoint。
- 一段从 Issue 到 Patch 的演示。
- 一份失败案例复盘，而不只有成功演示。
- 一份 Prompt/模型变更前后的评测报告。
- 安全边界、成本控制和运维说明。

## 暂不进入主线

在评测证明需要之前，不加入 LangGraph 关键路径、多 Agent、A2A、长期记忆、向量数据库、Kubernetes、IDE 插件和自动合并 PR。

## 最终自测问题

你应能独立解释：为什么模型不能决定最终成功、为什么真实命令不能在 Codespaces 执行、谁拥有 Sandbox、如何防止旧测试结果、事件如何重放，以及评测如何防止修改测试作弊。
