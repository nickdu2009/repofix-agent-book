import { RunEventSchema, type RunEvent } from "./contracts";

export type RunEventParseFailure = "invalid_json" | "invalid_schema";

export class RunEventParseError extends Error {
  readonly reason: RunEventParseFailure;
  readonly rawData: string;
  readonly details: unknown;

  constructor(reason: RunEventParseFailure, rawData: string, details: unknown) {
    super(reason === "invalid_json" ? "SSE event is not valid JSON" : "SSE event violates RunEvent schema");
    this.name = "RunEventParseError";
    this.reason = reason;
    this.rawData = rawData;
    this.details = details;
  }
}

export function parseRunEvent(rawData: string): RunEvent {
  let raw: unknown;
  try {
    raw = JSON.parse(rawData) as unknown;
  } catch (error) {
    throw new RunEventParseError("invalid_json", rawData, error);
  }

  const result = RunEventSchema.safeParse(raw);
  if (!result.success) {
    throw new RunEventParseError("invalid_schema", rawData, result.error);
  }
  return result.data;
}

export interface EventSourceLike {
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent<string>) => void) | null;
  onerror: ((event: Event) => void) | null;
  close(): void;
}

export type EventSourceFactory = (url: string) => EventSourceLike;
export type RunStreamState = "connecting" | "open" | "reconnecting" | "closed";

export type RunStreamError =
  | { readonly kind: "parse"; readonly error: RunEventParseError }
  | { readonly kind: "connection"; readonly event: Event };

export interface RunSubscriptionHandlers {
  onEvent(event: RunEvent): void;
  onError(error: RunStreamError): void;
  onStateChange?(state: RunStreamState): void;
}

export interface RunSubscription {
  readonly closed: boolean;
  close(): void;
}

export interface RunSubscriptionOptions {
  eventSourceFactory?: EventSourceFactory;
}

const createBrowserEventSource: EventSourceFactory = (url) => new EventSource(url);

export function subscribeToRun(
  runId: string,
  handlers: RunSubscriptionHandlers,
  options: RunSubscriptionOptions = {},
): RunSubscription {
  const factory = options.eventSourceFactory ?? createBrowserEventSource;
  const source = factory(`/api/v1/runs/${encodeURIComponent(runId)}/events`);
  let closed = false;

  handlers.onStateChange?.("connecting");

  source.onopen = () => {
    if (!closed) handlers.onStateChange?.("open");
  };
  source.onerror = (event) => {
    if (closed) return;
    handlers.onStateChange?.("reconnecting");
    handlers.onError({ kind: "connection", event });
  };
  source.onmessage = (message) => {
    if (closed) return;
    try {
      handlers.onEvent(parseRunEvent(message.data));
    } catch (error) {
      const parseError =
        error instanceof RunEventParseError
          ? error
          : new RunEventParseError("invalid_schema", message.data, error);
      handlers.onError({ kind: "parse", error: parseError });
    }
  };

  return {
    get closed() {
      return closed;
    },
    close() {
      if (closed) return;
      closed = true;
      source.onopen = null;
      source.onmessage = null;
      source.onerror = null;
      source.close();
      handlers.onStateChange?.("closed");
    },
  };
}
