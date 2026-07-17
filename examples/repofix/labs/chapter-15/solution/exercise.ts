// LAB:chapter-15 STATUS:complete
// TypeScript 7: narrow a discriminated union without using any.

export {};

type RunEvent =
  | { type: "run.started"; runId: string }
  | { type: "run.failed"; code: string };

function describe(event: RunEvent): string {
  switch (event.type) {
    case "run.started":
      return `started: ${event.runId}`;
    case "run.failed":
      return `failed: ${event.code}`;
    default: {
      const unreachable: never = event;
      return unreachable;
    }
  }
}

if (describe({ type: "run.failed", code: "timeout" }) !== "failed: timeout") {
  throw new Error("description mismatch");
}
console.log("chapter-15: PASS");
