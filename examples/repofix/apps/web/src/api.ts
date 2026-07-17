import { ApiErrorSchema, RunSchema, type ApiErrorPayload, type Run } from "./contracts";

export class ApiResponseError extends Error {
  readonly payload: ApiErrorPayload;

  constructor(payload: ApiErrorPayload) {
    super(payload.message);
    this.name = "ApiResponseError";
    this.payload = payload;
  }
}

export interface GetRunOptions {
  signal?: AbortSignal;
  fetch?: typeof globalThis.fetch;
}

export async function getRun(runId: string, options: GetRunOptions = {}): Promise<Run> {
  const fetchImpl = options.fetch ?? globalThis.fetch;
  const response = await fetchImpl(`/api/v1/runs/${encodeURIComponent(runId)}`, {
    ...(options.signal === undefined ? {} : { signal: options.signal }),
  });
  const raw: unknown = await response.json();

  if (!response.ok) {
    throw new ApiResponseError(ApiErrorSchema.parse(raw));
  }
  return RunSchema.parse(raw);
}
