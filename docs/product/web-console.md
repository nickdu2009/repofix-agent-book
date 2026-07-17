# React Web 控制台

Web 控制台只实现 RepoFix 的核心反馈环：创建任务、观察 Run、查看 Artifact、取消，以及比较评测。

## 本章契约

- **前置**：TypeScript 契约测试通过；Fake Go API 和 SSE 可运行。
- **产物**：三个页面、Run Reducer、SSE Hook、Diff/Test Report 视图和 E2E。
- **验收**：无云端密钥时，Fake E2E 可以从创建 Run 走到成功页面。

!!! info "当前 Checkpoint 与目标 Checkpoint"
    当前伴随 Web 已完成 Zod 契约、API Client、Run Reducer、可关闭 SSE 订阅及 12 条单元测试，`App` 仍是最小入口。下面的三个页面、Artifact 视图和 Playwright Fake E2E 是本章要继续实现的目标，尚未发布 solution tag。

## 页面和组件

```text
/tasks/new       TaskForm → 创建 Task 和 Run
/runs/:id        RunHeader、Timeline、DiffView、TestReport、CostSummary
/evals           EvalTable、BaselineCompare
```

每个页面必须实现 Loading、Empty、Error、Success；Run 页面再增加 Reconnecting、Cancelling 和 Terminal 状态。

## Reducer

Reducer 以 `sequence` 去重，不依赖事件到达次数：

```typescript
function runReducer(state: RunViewState, event: RunEvent): RunViewState {
  if (event.sequence <= state.lastSequence) return state;

  const next = { ...state, lastSequence: event.sequence };
  switch (event.type) {
    case "run.started":
    case "sandbox.created":
    case "sandbox.deleted":
    case "sandbox.cleanup_failed":
    case "step.started":
    case "tool.started":
    case "tool.completed":
    case "tests.completed":
    case "patch.created":
      return { ...next, timeline: [...state.timeline, event] };
    case "run.succeeded":
      return { ...next, status: "succeeded" };
    case "run.failed":
      return { ...next, status: "failed" };
    case "run.cancelled":
      return { ...next, status: "cancelled" };
    case "run.timed_out":
      return { ...next, status: "timed_out" };
    default:
      return next;
  }
}
```

## SSE Hook

本书第一版发送未命名 SSE message，因此使用 `onmessage`：

```typescript
export function subscribeToRun(
  runId: string,
  onEvent: (event: RunEvent) => void,
  onConnectionChange: (state: "open" | "reconnecting") => void,
): () => void {
  const source = new EventSource(`/api/v1/runs/${encodeURIComponent(runId)}/events`);

  source.onopen = () => onConnectionChange("open");
  source.onerror = () => onConnectionChange("reconnecting");
  source.onmessage = (message) => {
    const raw: unknown = JSON.parse(message.data);
    onEvent(RunEventSchema.parse(raw));
  };

  return () => source.close();
}
```

浏览器重连时会携带最后事件 ID，服务端负责按 `Last-Event-ID` 重放。组件挂载时先 GET 当前 Run 快照，再订阅事件；终态到达后再 GET 一次确认并关闭连接。

原生 `EventSource` 不能随意设置 Authorization Header。生产版优先使用同源安全 Cookie；若必须使用 Bearer Header，应改用基于 `fetch` 的流式客户端并单独测试重连。

## Artifact 显示安全

- Diff 作为纯文本渲染，不使用未经清理的 `dangerouslySetInnerHTML`。
- 日志和 Diff 有大小上限，超限提供下载链接。
- 大 Timeline 使用分页或虚拟化。
- 测试报告展示摘要与失败详情，不把完整 ANSI 控制序列直接注入 DOM。

## 测试

Vitest：

- Schema 和 Reducer 去重。
- 每种终态。
- SSE 非法 JSON/Schema 错误。
- Hook 卸载关闭连接。
- 取消按钮的禁用和失败状态。

Playwright Fake E2E：

1. 创建任务。
2. 跳转 Run 页面。
3. 接收重复和断线重放事件。
4. 查看 Diff 与测试报告。
5. 验证成功或取消终态。

## 故障排查与验收

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 后端有事件但页面收不到 | 后端发送命名 event，前端使用 `onmessage` | 统一为未命名 message，或改用 `addEventListener` |
| 重连后 Timeline 重复 | Reducer 不按 sequence 去重 | 保存并比较 `lastSequence` |
| 页面卸载后仍请求 | Effect 没有清理 | 返回 `source.close()` 和 AbortController |

当前验收命令：

```bash
cd examples/repofix/apps/web
npm ci
npm run typecheck
npm test
npm run build
```

完成三个页面后再增加 `npm run e2e`；该脚本和 Fake Go E2E 尚未存在时，不要把它写成空操作。真实 Daytona E2E 始终只能手动启动。
