// LAB:chapter-16 STATUS:todo
// TypeScript 7: derive UI state from ordered events.

export {};

type RunEvent =
  | { sequence: number; type: "run.started" }
  | { sequence: number; type: "run.failed" };

interface ViewState {
  readonly status: "pending" | "running" | "failed";
  readonly lastSequence: number;
}

function reduce(state: ViewState, event: RunEvent): ViewState {
  // TODO: ignore duplicate sequence numbers and apply newer events.
  return state;
}

const initial: ViewState = { status: "pending", lastSequence: 0 };
if (reduce(initial, { sequence: 1, type: "run.started" }).status !== "running") {
  throw new Error("reducer mismatch");
}
