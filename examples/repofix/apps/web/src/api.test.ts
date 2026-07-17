import { describe, expect, it } from "vitest";
import { ZodError } from "zod";

import { ApiResponseError, getRun } from "./api";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("getRun", () => {
  it("parses unknown response data before returning it", async () => {
    const run = {
      id: "run_01",
      task_id: "task_01",
      status: "pending",
      created_at: "2026-07-17T10:00:00Z",
      updated_at: "2026-07-17T10:00:00Z",
      version: 1,
    };

    await expect(
      getRun("run/01", { fetch: async () => response(run) }),
    ).resolves.toEqual(run);
  });

  it("rejects a successful HTTP response with an invalid body", async () => {
    await expect(
      getRun("run_01", { fetch: async () => response({ id: "run_01", status: "testing" }) }),
    ).rejects.toBeInstanceOf(ZodError);
  });

  it("validates and exposes a structured API error", async () => {
    const payload = {
      code: "run_not_found",
      message: "run does not exist",
      request_id: "req_01",
      retryable: false,
    };

    try {
      await getRun("missing", { fetch: async () => response(payload, 404) });
      throw new Error("expected getRun to fail");
    } catch (error) {
      expect(error).toBeInstanceOf(ApiResponseError);
      expect((error as ApiResponseError).payload).toEqual(payload);
    }
  });
});
