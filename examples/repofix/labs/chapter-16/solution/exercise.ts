// LAB:chapter-16 STATUS:complete
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
  if (event.sequence <= state.lastSequence) return state;
  return {
    status: event.type === "run.started" ? "running" : "failed",
    lastSequence: event.sequence,
  };
}

const initial: ViewState = { status: "pending", lastSequence: 0 };
const running = reduce(initial, { sequence: 1, type: "run.started" });
if (running.status !== "running") throw new Error("reducer mismatch");
if (reduce(running, { sequence: 1, type: "run.failed" }) !== running) {
  throw new Error("duplicate event was not ignored");
}
console.log("chapter-16: PASS");
