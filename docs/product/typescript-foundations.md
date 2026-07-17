# TypeScript 基础教学

TypeScript 学习从 JavaScript 差异和 RepoFix API 开始，不单独学习完整前端体系。

### 14.1 必学特性

| 特性 | RepoFix 中的用途 |
| --- | --- |
| `type`、`interface` | API DTO、组件 Props |
| 联合类型 | RunStatus、RunEvent |
| 类型收窄 | 根据事件类型安全读取字段 |
| `unknown` | 接收尚未验证的 API 数据 |
| 泛型 | `ApiResult<T>`、通用请求函数 |
| `Promise` | HTTP 和异步操作 |
| `AbortController` | 取消请求 |
| ESM | 模块组织 |
| Zod | 运行时验证后端数据 |
| `strict` | 提前发现空值和类型错误 |

暂不学习复杂条件类型、类型体操、装饰器、自定义编译插件和复杂状态管理框架。

### 14.2 可辨识联合类型

```typescript
type RunEvent =
  | {
      type: "step.started";
      step: number;
      tool: string;
    }
  | {
      type: "step.completed";
      step: number;
      output: string;
    }
  | {
      type: "run.failed";
      error: string;
    };
```

使用 `switch` 后，TypeScript 会根据 `type` 自动缩小类型：

```typescript
function describeEvent(event: RunEvent): string {
  switch (event.type) {
    case "step.started":
      return `开始执行 ${event.tool}`;
    case "step.completed":
      return event.output;
    case "run.failed":
      return event.error;
  }
}
```

不要把所有事件字段都设计成可选字段。

### 14.3 运行时校验

TypeScript 类型不会在运行时验证 HTTP 数据。使用 Zod 检查：

```typescript
import { z } from "zod";

const RunSchema = z.object({
  id: z.string(),
  status: z.enum([
    "pending",
    "provisioning",
    "running",
    "testing",
    "succeeded",
    "failed",
  ]),
});

type Run = z.infer<typeof RunSchema>;

const raw: unknown = await response.json();
const run: Run = RunSchema.parse(raw);
```

### 14.4 与 Go 的概念对照

```text
TypeScript interface   ≈ Go struct/interface 的部分能力
联合类型               ≈ tagged union
Promise<T>             ≈ 异步结果，不等同于 goroutine
unknown                ≈ 必须验证后才能使用的数据
Record<K, V>           ≈ map[K]V
泛型 <T>               ≈ Go 泛型
```
