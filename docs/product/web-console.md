# 第 16 章 · Web 客户端：React 控制台

Web 控制台只实现 RepoFix 的核心反馈环：创建任务、观察 Run、查看 Artifact、取消，以及比较评测。

## 快速开始

[打开通用 Codespaces](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json){ .md-button .md-button--primary }

| 用途 | 路径 |
| --- | --- |
| 只读 Reducer 与 SSE 骨架 | `examples/repofix/labs/chapter-16/start/` |
| 你的练习副本 | `examples/repofix/.work/chapter-16/` |
| 参考实现 | `examples/repofix/labs/chapter-16/solution/` |

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-16
make chapter-check CHAPTER=chapter-16
```

在 `.work/chapter-16/exercise.ts` 中完成 Reducer 的顺序与去重 TODO。`chapter-check` 检查结构与 TODO；随后运行 `apps/web/node_modules/.bin/tsc --noEmit --strict --target ES2024 --moduleDetection force .work/chapter-16/exercise.ts` 和 `node .work/chapter-16/exercise.ts`，分别验证类型与行为。SSE 生命周期在本章后文和集成参考中学习；这些命令只运行教程自带练习，start 保持只读。

## 本章契约

- **前置**：TypeScript 契约测试通过；Fake Go API 和 SSE 可运行。
- **产物**：三个页面、Run Reducer、SSE Hook、Diff/Test Report 视图和 E2E。
- **验收**：无云端密钥时，Fake E2E 可以从创建 Run 走到成功页面。

!!! info "集成参考的诚实状态"
    主项目中的 Web 已完成 Zod 契约、API Client、Run Reducer、可关闭 SSE 订阅及离线单元测试，`App` 仍是最小入口。chapter-16 solution 只示范本章可验证的 Reducer/SSE 边界；三个完整页面、Artifact 视图和 Playwright Fake E2E 仍是后续目标，不能因存在 solution 目录就宣称产品已经完成。

## 页面和组件

| 路由 | 最小组件与职责 |
| --- | --- |
| `/tasks/new` | `TaskForm` 创建 Task 与 Run |
| `/runs/:id` | `RunHeader`、Timeline、Diff、测试与成本 |
| `/evals` | `EvalTable` 与基线对比 |

每个页面必须实现 Loading、Empty、Error、Success；Run 页面再增加 Reconnecting、Cancelling 和 Terminal 状态。

## Reducer

Reducer 以 `sequence` 去重，不依赖事件到达次数：

```typescript
const terminal: Partial<Record<RunEventType, RunStatus>> = {
  "run.succeeded": "succeeded",
  "run.failed": "failed",
  "run.cancelled": "cancelled",
  "run.timed_out": "timed_out",
};

function runReducer(state: RunViewState, event: RunEvent): RunViewState {
  if (event.sequence <= state.lastSequence) return state;
  return {
    ...state,
    status: terminal[event.type] ?? state.status,
    lastSequence: event.sequence,
    timeline: [...state.timeline, event],
  };
}
```

完整实现还记录 Sandbox 清理状态，见 `apps/web/src/run-state.ts`。这里的核心只有两个不变量：旧序号不产生状态变化；终态由事件类型映射，不从任意 `data` 字段猜测。

## SSE Hook

本书第一版发送未命名 SSE message，因此使用 `onmessage`：

```typescript
export function subscribeToRun(
  runId: string,
  onEvent: (event: RunEvent) => void,
  onReconnect: () => void,
): () => void {
  const source = new EventSource(`/api/v1/runs/${encodeURIComponent(runId)}/events`);
  source.onmessage = (message) => {
    const raw: unknown = JSON.parse(message.data);
    onEvent(RunEventSchema.parse(raw));
  };
  source.onerror = onReconnect;
  return () => source.close();
}
```

React 的 `useEffect` 调用该函数，并直接返回清理函数；依赖项变化、组件卸载或终态到达时都要关闭旧连接。浏览器重连时会携带最后事件 ID，服务端负责按 `Last-Event-ID` 重放。组件挂载时先 GET 当前 Run 快照，订阅后在终态再 GET 一次确认。

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

## 练习

1. 连续发送两次相同 `sequence` 的事件，证明 Timeline 只增加一次。
2. 注入非法 JSON 与合法 JSON/非法 Schema 两种错误，让页面给出可区分提示。
3. 在组件卸载和 Run 进入终态时分别断言 SSE 连接关闭。

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
