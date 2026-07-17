// LAB:chapter-15 STATUS:todo
// TypeScript 7: narrow a discriminated union without using any.

export {};

type RunEvent =
  | { type: "run.started"; runId: string }
  | { type: "run.failed"; code: string };

function describe(event: RunEvent): string {
  // TODO: handle both variants and keep the switch exhaustive.
  return event.type;
}

if (describe({ type: "run.failed", code: "timeout" }) !== "failed: timeout") {
  throw new Error("description mismatch");
}
