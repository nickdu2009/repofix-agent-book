package repository

import (
	"context"
	"errors"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
)

var (
	ErrNotFound = errors.New("run not found")
	ErrConflict = errors.New("run version conflict")
	ErrExists   = errors.New("run already exists")
)

// Transition describes one atomic status change and its optional event.
type Transition struct {
	ExpectedVersion int64
	Next            domain.RunStatus
	FailureCode     string
	EventType       domain.EventType
	EventData       map[string]any
}

// Store is the persistence boundary used by the orchestrator.
type Store interface {
	Create(context.Context, domain.Run) error
	Get(context.Context, string) (domain.Run, error)
	Transition(context.Context, string, Transition) (domain.Run, error)
	AttachSandbox(context.Context, string, int64, string) (domain.Run, error)
	RecordSandboxCleanup(context.Context, string, int64, string, bool) (domain.Run, error)
	Events(context.Context, string) ([]domain.Event, error)
}
