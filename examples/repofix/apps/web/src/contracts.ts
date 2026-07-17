import { z } from "zod";

export const RUN_STATUSES = [
  "pending",
  "provisioning",
  "running",
  "succeeded",
  "failed",
  "cancelled",
  "timed_out",
] as const;

export const RunStatusSchema = z.enum(RUN_STATUSES);
export type RunStatus = z.infer<typeof RunStatusSchema>;

const DateTimeSchema = z.string().datetime({ offset: true });

export const RunSchema = z
  .object({
    id: z.string().min(1),
    task_id: z.string().min(1),
    status: RunStatusSchema,
    created_at: DateTimeSchema,
    updated_at: DateTimeSchema,
    version: z.number().int().min(1),
    failure_code: z.string().nullable().optional(),
    cancel_requested_at: DateTimeSchema.nullable().optional(),
  })
  .strict();

export type Run = z.infer<typeof RunSchema>;

export const RUN_EVENT_TYPES = [
  "run.started",
  "sandbox.created",
  "sandbox.deleted",
  "sandbox.cleanup_failed",
  "step.started",
  "tool.started",
  "tool.completed",
  "tests.completed",
  "patch.created",
  "run.succeeded",
  "run.failed",
  "run.cancelled",
  "run.timed_out",
] as const;

export const RunEventTypeSchema = z.enum(RUN_EVENT_TYPES);
export type RunEventType = z.infer<typeof RunEventTypeSchema>;

export const RunEventSchema = z
  .object({
    id: z.string().min(1),
    run_id: z.string().min(1),
    sequence: z.number().int().min(1),
    type: RunEventTypeSchema,
    occurred_at: DateTimeSchema,
    schema_version: z.literal(1),
    data: z.record(z.string(), z.unknown()),
  })
  .strict();

export type RunEvent = z.infer<typeof RunEventSchema>;

export const ApiErrorSchema = z
  .object({
    code: z.string().min(1),
    message: z.string().min(1),
    request_id: z.string().min(1),
    retryable: z.boolean(),
    details: z.record(z.string(), z.unknown()).nullable().optional(),
  })
  .strict();

export type ApiErrorPayload = z.infer<typeof ApiErrorSchema>;
