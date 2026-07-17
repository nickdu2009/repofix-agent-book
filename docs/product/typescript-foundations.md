# TypeScript 工程与契约校验

TypeScript 从 RepoFix 的 API 边界开始学习。编译期类型不能验证网络数据，因此 JSON Schema 是跨语言事实来源，Zod 负责浏览器运行时校验。

本章使用 Node.js 24 LTS、TypeScript 7、React 19 和 ESM。`tsconfig.json` 开启 `strict`、`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes`、`verbatimModuleSyntax`、未使用符号检查与 `switch` 穿透检查。现代 TypeScript 的重点是让边界更可靠，而不是编写复杂条件类型。

## 本章契约

- **前置**：`examples/repofix/contracts/` 已稳定，Fake Go API 可启动。
- **产物**：Vite + React + TypeScript 工程、API Client、运行时 Schema 和契约测试。
- **验收**：任何非法后端 payload 都不会进入 React 状态。

!!! success "伴随实现"
    `examples/repofix/apps/web/` 已锁定依赖并实现本章的 Run/RunEvent/Error Schema、`unknown` API 边界、Reducer 和 SSE 解析测试。不要再次运行脚手架覆盖它；初始化命令用于理解项目如何生成。

## 安装锁定工程

```bash
cd examples/repofix/apps/web
npm ci
```

`package.json` 固定直接依赖版本，`package-lock.json` 固定完整依赖树。升级 React、Vite、TypeScript 或 Zod 必须作为单独 Issue，同时运行 typecheck、测试和生产构建；不要在教程主线使用 `npm create ...@latest` 重新生成项目。

`tsconfig` 必须启用 `strict`、`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes` 和 `verbatimModuleSyntax`。类型导入使用 `import type`，不要用 `any` 或强制断言绕过外部数据边界。

## 统一状态

状态必须与 `run.schema.json` 完全一致：

```typescript
import { z } from "zod";

export const RunStatusSchema = z.enum([
  "pending",
  "provisioning",
  "running",
  "succeeded",
  "failed",
  "cancelled",
  "timed_out",
]);

export type RunStatus = z.infer<typeof RunStatusSchema>;
```

`testing` 是事件，不是 RunStatus。

## 事件信封

```typescript
const EventTypeSchema = z.enum([
  "run.started",
  "sandbox.created",
  "sandbox.deleted",
  "sandbox.cleanup_failed",
  "step.started",
  "tool.started",
  "tool.completed",
  "tests.completed",
  "patch.created",
  "run.succeeded",
  "run.failed",
  "run.cancelled",
  "run.timed_out",
]);

export const RunEventSchema = z.object({
  id: z.string().min(1),
  run_id: z.string().min(1),
  sequence: z.number().int().positive(),
  type: EventTypeSchema,
  occurred_at: z.string().datetime(),
  schema_version: z.literal(1),
  data: z.record(z.string(), z.unknown()),
}).strict();

export type RunEvent = z.infer<typeof RunEventSchema>;
```

外部数据从 `unknown` 开始：

```typescript
const raw: unknown = await response.json();
const event = RunEventSchema.parse(raw);
```

解析失败进入可观察的错误状态，不应静默丢弃或强制断言 `as RunEvent`。

## 可辨识联合与穷尽检查

业务层可将通用事件信封映射为更精确的联合类型。`switch` 末尾加入 `never`，新增事件时编译器会提示未处理分支：

```typescript
function assertNever(value: never): never {
  throw new Error(`unhandled event: ${JSON.stringify(value)}`);
}
```

## API Client

```typescript
export async function getRun(runId: string, signal?: AbortSignal): Promise<Run> {
  const response = await fetch(`/api/v1/runs/${encodeURIComponent(runId)}`, { signal });
  const raw: unknown = await response.json();
  if (!response.ok) throw ApiErrorSchema.parse(raw);
  return RunSchema.parse(raw);
}
```

区分 HTTP 失败、Schema 失败、取消和网络失败；不要把所有错误都转换成一个字符串。

## 练习

1. 用 `unknown` 接收一个缺少 `sequence` 的事件并证明 Schema 拒绝。
2. 为 `timed_out` 增加 UI 描述，使用 `never` 确保分支完整。
3. 使用 `AbortController` 取消一次 Run 查询。

## 测试、排错与验收

```bash
npm run typecheck
npm run test
```

至少覆盖合法事件、未知状态、缺失字段、额外字段、旧 Schema 版本和取消请求。若契约测试发现三端枚举不同，应修改共享 Schema，而不是单独放宽前端。

Checkpoint：`npm run typecheck && npm test && npm run build` 全部通过；页面尚未完成，但 API 边界、事件去重和错误可观察性已有可运行源码。
