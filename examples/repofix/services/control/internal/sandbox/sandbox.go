package sandbox

import (
	"context"
	"sync"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
)

// Instance identifies an isolated execution environment.
type Instance struct {
	ID string
}

// Manager owns sandbox creation and deletion.
// A successful Create must return a non-empty ID. If a provider partially
// creates a sandbox but cannot return its ID, it must clean that resource up
// before returning an error because the caller has no deletion handle.
type Manager interface {
	Create(context.Context, domain.Run) (Instance, error)
	Delete(context.Context, string) error
}

// FakeManager records lifecycle calls without touching a network or process.
type FakeManager struct {
	mu         sync.Mutex
	InstanceID string
	// ReturnEmptyID simulates a provider violating the Create contract.
	ReturnEmptyID bool
	CreateErr     error
	DeleteErr     error
	CreatedFor    []string
	DeletedIDs    []string
}

var _ Manager = (*FakeManager)(nil)

func (f *FakeManager) Create(ctx context.Context, run domain.Run) (Instance, error) {
	if err := ctx.Err(); err != nil {
		return Instance{}, err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.CreatedFor = append(f.CreatedFor, run.ID)
	if f.CreateErr != nil {
		return Instance{}, f.CreateErr
	}
	if f.ReturnEmptyID {
		return Instance{}, nil
	}
	id := f.InstanceID
	if id == "" {
		id = "fake-sandbox-1"
	}
	return Instance{ID: id}, nil
}

func (f *FakeManager) Delete(ctx context.Context, sandboxID string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.DeletedIDs = append(f.DeletedIDs, sandboxID)
	return f.DeleteErr
}

func (f *FakeManager) CreateCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.CreatedFor)
}

func (f *FakeManager) DeleteCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.DeletedIDs)
}
