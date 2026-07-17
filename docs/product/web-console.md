# TypeScript Web 客户端

建议使用 React、Vite 和 TypeScript，只实现 RepoFix 必需页面：

```text
/tasks/new
/runs/:id
/evals
```

### 15.1 SSE 客户端

```typescript
function subscribeToRun(
  runId: string,
  onEvent: (event: RunEvent) => void,
): () => void {
  const source = new EventSource(`/api/runs/${runId}/events`);

  source.onmessage = (message) => {
    const raw: unknown = JSON.parse(message.data);
    const event = RunEventSchema.parse(raw);
    onEvent(event);
  };

  return () => source.close();
}
```

### 15.2 React 学习范围

- 函数组件与 Props。
- `useState`。
- `useEffect` 与清理函数。
- `useReducer`。
- 自定义 Hook。
- 表单与校验。
- Loading、Empty、Error 状态。
- Vitest 组件测试。
- Playwright E2E 基础。

### 15.3 页面验收

- 能创建 Task 和 Run。
- 能实时看到工具调用。
- 能查看修改 Diff。
- 能查看测试结果和错误。
- 能取消任务。
- SSE 断开时有明确状态。
- 非法 API 数据不会直接进入页面状态。
