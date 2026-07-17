# 第 15 章 · TypeScript 基础：工程与契约校验

TypeScript 从 RepoFix 的 API 边界开始学习。编译期类型不能验证网络数据，因此 JSON Schema 是跨语言事实来源，Zod 负责浏览器运行时校验。

本章使用 Node.js 24 LTS、TypeScript 7、React 19 和 ESM。`tsconfig.json` 开启 `strict`、`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes`、`verbatimModuleSyntax`、未使用符号检查与 `switch` 穿透检查。现代 TypeScript 的重点是让边界更可靠，而不是编写复杂条件类型。

## 快速开始

[打开通用 Codespaces](https://codespaces.new/nickdu2009/repofix-agent-book?quickstart=1&devcontainer_path=examples%2Frepofix%2F.devcontainer%2Fdevcontainer.json){ .md-button .md-button--primary }

| 用途 | 路径 |
| --- | --- |
| 只读 TypeScript 边界骨架 | `examples/repofix/labs/chapter-15/start/` |
| 你的练习副本 | `examples/repofix/.work/chapter-15/` |
| 参考实现 | `examples/repofix/labs/chapter-15/solution/` |

```bash
cd examples/repofix
make chapter-prepare CHAPTER=chapter-15
make chapter-check CHAPTER=chapter-15
```

在 `.work/chapter-15/exercise.ts` 中完成类型 TODO；不要修改 start，完成检查后才对照 `solution/`。`chapter-check` 检查结构与 TODO；随后用 `apps/web/node_modules/.bin/tsc --noEmit --strict --target ES2024 --moduleDetection force .work/chapter-15/exercise.ts` 做显式类型检查，再用 `node .work/chapter-15/exercise.ts` 验证行为。这些命令只运行教程自带练习，不运行模型生成的仓库代码。`apps/web/` 展示集成后的参考形态。

## 本章契约

- **前置**：`examples/repofix/contracts/` 已稳定，Fake Go API 可启动。
- **产物**：Vite + React + TypeScript 工程、API Client、运行时 Schema 和契约测试。
- **验收**：任何非法后端 payload 都不会进入 React 状态。

!!! success "集成参考实现"
    `examples/repofix/apps/web/` 展示本章能力集成进主项目后的形态：锁定依赖、Run/RunEvent/Error Schema、`unknown` API 边界、Reducer 和 SSE 解析测试。练习仍从 chapter-15 的 start 骨架开始，不要用完整目录覆盖自己的过程。

## 安装锁定工程

```bash
cd examples/repofix/apps/web
npm ci
```

`package.json` 固定直接依赖版本，`package-lock.json` 固定完整依赖树。升级 React、Vite、TypeScript 或 Zod 必须作为单独 Issue，同时运行 typecheck、测试和生产构建；不要在教程主线使用 `npm create ...@latest` 重新生成项目。

`tsconfig` 必须启用 `strict`、`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes` 和 `verbatimModuleSyntax`。类型导入使用 `import type`，不要用 `any` 或强制断言绕过外部数据边界。

## 统一状态

状态必须与 `run.schema.json` 完全一致。不要在教程里再抄一份完整列表；集成实现把字面量集中在 `apps/web/src/contracts.ts` 的 `RUN_STATUSES`，Zod Schema 和静态类型都从它派生：

```typescript
import { z } from "zod";

export const RunStatusSchema = z.enum(RUN_STATUSES);
export type RunStatus = z.infer<typeof RunStatusSchema>;
```

共享 Schema、Go 常量和 `RUN_STATUSES` 由契约测试比对；`testing` 是事件，不是 RunStatus。

## 核心示例链：unknown → Zod → 已验证类型

```typescript
export const RunEventSchema = z.object({
  id: z.string().min(1),
  run_id: z.string().min(1),
  sequence: z.number().int().positive(),
  type: z.enum(RUN_EVENT_TYPES),
  occurred_at: z.string().datetime({ offset: true }),
  schema_version: z.literal(1),
  data: z.record(z.string(), z.unknown()),
}).strict();

export type RunEvent = z.infer<typeof RunEventSchema>;

export async function readEvent(response: Response): Promise<RunEvent> {
  const raw: unknown = await response.json();
  return RunEventSchema.parse(raw);
}
```

这里故意省略事件字面量清单，完整契约见 `apps/web/src/contracts.ts`。关键点是外部数据从 `unknown` 开始，只有 `parse` 成功后才能进入 React 状态。解析失败必须进入可观察错误状态，不能用 `as RunEvent` 绕过。

## 可辨识联合与穷尽检查

业务层可将通用事件信封映射为更精确的联合类型。`switch` 末尾加入 `never`，新增事件时编译器会提示未处理分支：

```typescript
function assertNever(value: never): never {
  throw new Error(`unhandled event: ${JSON.stringify(value)}`);
}
```

## API Client

按以下顺序阅读 `apps/web/src/api.ts`，无需把完整 Client 复制进正文：

| 步骤 | 要验证的行为 |
| --- | --- |
| 构造请求 | `encodeURIComponent` 处理 ID，`AbortSignal` 可取消 |
| 读取响应 | JSON 先保存为 `unknown` |
| 非 2xx | 使用 `ApiErrorSchema` 验证错误信封 |
| 成功 | 使用 `RunSchema` 验证后返回 |

HTTP 失败、Schema 失败、取消和网络失败必须可区分，不能全部转换成一个字符串。

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
