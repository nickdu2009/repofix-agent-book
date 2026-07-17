import type { RunEvent, RunStatus } from "./contracts";

export interface RunViewState {
  readonly status: RunStatus;
  readonly lastSequence: number;
  readonly timeline: readonly RunEvent[];
  readonly sandboxDeleted: boolean;
}

export function createRunViewState(status: RunStatus = "pending"): RunViewState {
  return {
    status,
    lastSequence: 0,
    timeline: [],
    sandboxDeleted: false,
  };
}

export function runReducer(state: RunViewState, event: RunEvent): RunViewState {
  if (event.sequence <= state.lastSequence) {
    return state;
  }

  let status = state.status;
  switch (event.type) {
    case "run.started":
      status = "running";
      break;
    case "run.succeeded":
      status = "succeeded";
      break;
    case "run.failed":
      status = "failed";
      break;
    case "run.cancelled":
      status = "cancelled";
      break;
    case "run.timed_out":
      status = "timed_out";
      break;
    case "sandbox.created":
    case "sandbox.deleted":
    case "sandbox.cleanup_failed":
    case "step.started":
    case "tool.started":
    case "tool.completed":
    case "tests.completed":
    case "patch.created":
      break;
  }

  return {
    status,
    lastSequence: event.sequence,
    timeline: [...state.timeline, event],
    sandboxDeleted: state.sandboxDeleted || event.type === "sandbox.deleted",
  };
}
