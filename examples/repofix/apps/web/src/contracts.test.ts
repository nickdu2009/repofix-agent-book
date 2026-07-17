import { describe, expect, it } from "vitest";

import { RUN_EVENT_TYPES, RunEventSchema, RunSchema } from "./contracts";

const validRun = {
  id: "run_01",
  task_id: "task_01",
  status: "running",
  created_at: "2026-07-17T10:00:00Z",
  updated_at: "2026-07-17T10:00:01Z",
  version: 1,
};

const validEvent = {
  id: "evt_01",
  run_id: "run_01",
  sequence: 1,
  type: "sandbox.deleted",
  occurred_at: "2026-07-17T10:00:02Z",
  schema_version: 1,
  data: {},
};

describe("wire contracts", () => {
  it("accepts the canonical Run fields", () => {
    expect(RunSchema.parse(validRun)).toEqual(validRun);
  });

  it("rejects unknown Run states and extra fields", () => {
    expect(() => RunSchema.parse({ ...validRun, status: "testing" })).toThrow();
    expect(() => RunSchema.parse({ ...validRun, secret: "must not cross boundary" })).toThrow();
  });

  it("includes and accepts sandbox.deleted", () => {
    expect(RUN_EVENT_TYPES).toContain("sandbox.deleted");
    expect(RunEventSchema.parse(validEvent)).toEqual(validEvent);
  });

  it("rejects invalid sequence, schema version, and extra event fields", () => {
    expect(() => RunEventSchema.parse({ ...validEvent, sequence: 0 })).toThrow();
    expect(() => RunEventSchema.parse({ ...validEvent, schema_version: 2 })).toThrow();
    expect(() => RunEventSchema.parse({ ...validEvent, unexpected: true })).toThrow();
  });
});
