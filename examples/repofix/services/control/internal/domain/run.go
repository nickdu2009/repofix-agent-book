package domain

import "fmt"

// RunStatus is the control-plane status serialized on the public API.
type RunStatus string

const (
	StatusPending      RunStatus = "pending"
	StatusProvisioning RunStatus = "provisioning"
	StatusRunning      RunStatus = "running"
	StatusSucceeded    RunStatus = "succeeded"
	StatusFailed       RunStatus = "failed"
	StatusCancelled    RunStatus = "cancelled"
	StatusTimedOut     RunStatus = "timed_out"
)

var allowedTransitions = map[RunStatus]map[RunStatus]struct{}{
	StatusPending: {
		StatusProvisioning: {},
		StatusCancelled:    {},
	},
	StatusProvisioning: {
		StatusRunning:   {},
		StatusFailed:    {},
		StatusCancelled: {},
		StatusTimedOut:  {},
	},
	StatusRunning: {
		StatusSucceeded: {},
		StatusFailed:    {},
		StatusCancelled: {},
		StatusTimedOut:  {},
	},
}

// Run is the program-owned lifecycle state for one task execution.
type Run struct {
	ID        string
	TaskID    string
	Status    RunStatus
	Version   int64
	SandboxID string
	// SandboxCleanupRecorded distinguishes "not attempted" from a recorded
	// cleanup attempt. SandboxDeleted is true only when that attempt succeeded.
	SandboxCleanupRecorded bool
	SandboxDeleted         bool
	FailureCode            string
}

// NewRun creates a Run at the only valid initial status.
func NewRun(id, taskID string) (Run, error) {
	if id == "" {
		return Run{}, fmt.Errorf("run id must not be empty")
	}
	if taskID == "" {
		return Run{}, fmt.Errorf("task id must not be empty")
	}
	return Run{
		ID:      id,
		TaskID:  taskID,
		Status:  StatusPending,
		Version: 1,
	}, nil
}

// Terminal reports whether no further status transition is allowed.
func (s RunStatus) Terminal() bool {
	switch s {
	case StatusSucceeded, StatusFailed, StatusCancelled, StatusTimedOut:
		return true
	default:
		return false
	}
}

// Transition validates and applies one lifecycle transition.
func (r *Run) Transition(next RunStatus) error {
	if _, ok := allowedTransitions[r.Status][next]; !ok {
		return fmt.Errorf("invalid run transition: %s -> %s", r.Status, next)
	}
	if next.Terminal() && r.SandboxID != "" && !r.SandboxCleanupRecorded {
		return fmt.Errorf("cannot finish run before sandbox cleanup is recorded")
	}
	if next.Terminal() && r.SandboxID != "" && !r.SandboxDeleted && next != StatusFailed {
		return fmt.Errorf("sandbox deletion failure requires failed run status")
	}
	r.Status = next
	r.Version++
	return nil
}
