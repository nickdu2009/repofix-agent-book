import { describe, expect, it } from "vitest";

import type { RunEvent } from "./contracts";
import {
  parseRunEvent,
  subscribeToRun,
  type EventSourceLike,
  type RunStreamError,
  type RunStreamState,
} from "./sse";

class FakeEventSource implements EventSourceLike {
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  closeCalls = 0;

  open() {
    this.onopen?.({} as Event);
  }

  message(data: string) {
    this.onmessage?.({ data } as MessageEvent<string>);
  }

  fail() {
    this.onerror?.({} as Event);
  }

  close() {
    this.closeCalls += 1;
  }
}

function validEvent(sequence = 1): RunEvent {
  return {
    id: `evt_${sequence}`,
    run_id: "run_01",
    sequence,
    type: "tool.completed",
    occurred_at: "2026-07-17T10:00:00Z",
    schema_version: 1,
    data: { ok: true },
  };
}

describe("parseRunEvent", () => {
  it("keeps JSON and schema failures distinguishable", () => {
    expect(() => parseRunEvent("not-json")).toThrowError(
      expect.objectContaining({ reason: "invalid_json" }),
    );
    expect(() => parseRunEvent(JSON.stringify({ sequence: 0 }))).toThrowError(
      expect.objectContaining({ reason: "invalid_schema" }),
    );
  });
});

describe("subscribeToRun", () => {
  it("reports parse errors and continues receiving valid events", () => {
    const source = new FakeEventSource();
    const events: RunEvent[] = [];
    const errors: RunStreamError[] = [];

    subscribeToRun(
      "run/01",
      {
        onEvent: (event) => events.push(event),
        onError: (error) => errors.push(error),
      },
      { eventSourceFactory: () => source },
    );

    source.message("not-json");
    source.message(JSON.stringify(validEvent()));

    expect(errors).toHaveLength(1);
    expect(errors[0]?.kind).toBe("parse");
    expect(events).toEqual([validEvent()]);
  });

  it("makes connection changes observable and closes idempotently", () => {
    const source = new FakeEventSource();
    const states: RunStreamState[] = [];
    const errors: RunStreamError[] = [];
    const events: RunEvent[] = [];
    let requestedUrl = "";

    const subscription = subscribeToRun(
      "run/01",
      {
        onEvent: (event) => events.push(event),
        onError: (error) => errors.push(error),
        onStateChange: (state) => states.push(state),
      },
      {
        eventSourceFactory: (url) => {
          requestedUrl = url;
          return source;
        },
      },
    );

    source.open();
    source.fail();
    subscription.close();
    subscription.close();
    source.message(JSON.stringify(validEvent()));

    expect(requestedUrl).toBe("/api/v1/runs/run%2F01/events");
    expect(states).toEqual(["connecting", "open", "reconnecting", "closed"]);
    expect(errors[0]?.kind).toBe("connection");
    expect(subscription.closed).toBe(true);
    expect(source.closeCalls).toBe(1);
    expect(events).toEqual([]);
  });
});
