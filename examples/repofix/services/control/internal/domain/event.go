package domain

import "time"

// EventType is the canonical event value stored and sent over SSE.
type EventType string

const (
	EventRunStarted           EventType = "run.started"
	EventSandboxCreated       EventType = "sandbox.created"
	EventSandboxDeleted       EventType = "sandbox.deleted"
	EventSandboxCleanupFailed EventType = "sandbox.cleanup_failed"
	EventStepStarted          EventType = "step.started"
	EventToolStarted          EventType = "tool.started"
	EventToolCompleted        EventType = "tool.completed"
	EventTestsCompleted       EventType = "tests.completed"
	EventPatchCreated         EventType = "patch.created"
	EventRunSucceeded         EventType = "run.succeeded"
	EventRunFailed            EventType = "run.failed"
	EventRunCancelled         EventType = "run.cancelled"
	EventRunTimedOut          EventType = "run.timed_out"
)

// Event is the durable event envelope used by the control plane.
type Event struct {
	ID            string         `json:"id"`
	RunID         string         `json:"run_id"`
	Sequence      int64          `json:"sequence"`
	Type          EventType      `json:"type"`
	OccurredAt    time.Time      `json:"occurred_at"`
	SchemaVersion int            `json:"schema_version"`
	Data          map[string]any `json:"data"`
}
