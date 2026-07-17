import { describe, expect, it } from "vitest";

import { type RunEvent } from "./contracts";
import { createRunViewState, runReducer } from "./run-state";

function event(sequence: number, type: RunEvent["type"]): RunEvent {
  return {
    id: `evt_${sequence}_${type}`,
    run_id: "run_01",
    sequence,
    type,
    occurred_at: "2026-07-17T10:00:00Z",
    schema_version: 1,
    data: {},
  };
}

describe("runReducer", () => {
  it("applies each sequence only once", () => {
    const started = runReducer(createRunViewState(), event(1, "run.started"));
    const duplicate = runReducer(started, event(1, "tool.completed"));

    expect(started.status).toBe("running");
    expect(started.timeline).toHaveLength(1);
    expect(duplicate).toBe(started);
  });

  it("tracks terminal status and sandbox deletion", () => {
    const deleted = runReducer(createRunViewState("running"), event(2, "sandbox.deleted"));
    const succeeded = runReducer(deleted, event(3, "run.succeeded"));

    expect(deleted.sandboxDeleted).toBe(true);
    expect(succeeded.status).toBe("succeeded");
    expect(succeeded.lastSequence).toBe(3);
    expect(succeeded.timeline.map((item) => item.type)).toEqual([
      "sandbox.deleted",
      "run.succeeded",
    ]);
  });
});
