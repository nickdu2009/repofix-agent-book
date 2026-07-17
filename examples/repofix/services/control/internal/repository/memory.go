package repository

import (
	"context"
	"fmt"
	"reflect"
	"sync"
	"time"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
)

// MemoryStore is a deterministic, concurrency-safe repository for tests and Fake E2E.
type MemoryStore struct {
	mu     sync.RWMutex
	runs   map[string]domain.Run
	events map[string][]domain.Event
	clock  func() time.Time
}

var _ Store = (*MemoryStore)(nil)

// NewMemoryStore creates an empty repository.
func NewMemoryStore() *MemoryStore {
	return NewMemoryStoreWithClock(time.Now)
}

// NewMemoryStoreWithClock allows tests to make event timestamps deterministic.
func NewMemoryStoreWithClock(clock func() time.Time) *MemoryStore {
	if clock == nil {
		clock = time.Now
	}
	return &MemoryStore{
		runs:   make(map[string]domain.Run),
		events: make(map[string][]domain.Event),
		clock:  clock,
	}
}

func (m *MemoryStore) Create(ctx context.Context, run domain.Run) error {
	if err := ctx.Err(); err != nil {
		return err
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.runs[run.ID]; ok {
		return fmt.Errorf("%w: %s", ErrExists, run.ID)
	}
	m.runs[run.ID] = run
	return nil
}

func (m *MemoryStore) Get(ctx context.Context, runID string) (domain.Run, error) {
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}

	m.mu.RLock()
	defer m.mu.RUnlock()
	run, ok := m.runs[runID]
	if !ok {
		return domain.Run{}, fmt.Errorf("%w: %s", ErrNotFound, runID)
	}
	return run, nil
}

func (m *MemoryStore) Transition(
	ctx context.Context,
	runID string,
	change Transition,
) (domain.Run, error) {
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}
	run, ok := m.runs[runID]
	if !ok {
		return domain.Run{}, fmt.Errorf("%w: %s", ErrNotFound, runID)
	}
	if run.Version != change.ExpectedVersion {
		return domain.Run{}, fmt.Errorf(
			"%w: run=%s expected=%d actual=%d",
			ErrConflict,
			runID,
			change.ExpectedVersion,
			run.Version,
		)
	}
	if err := run.Transition(change.Next); err != nil {
		return domain.Run{}, err
	}
	run.FailureCode = change.FailureCode
	m.runs[runID] = run
	if change.EventType != "" {
		m.appendEventLocked(runID, change.EventType, change.EventData)
	}
	return run, nil
}

func (m *MemoryStore) AttachSandbox(
	ctx context.Context,
	runID string,
	expectedVersion int64,
	sandboxID string,
) (domain.Run, error) {
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}
	if sandboxID == "" {
		return domain.Run{}, fmt.Errorf("sandbox id must not be empty")
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}
	run, ok := m.runs[runID]
	if !ok {
		return domain.Run{}, fmt.Errorf("%w: %s", ErrNotFound, runID)
	}
	if run.Version != expectedVersion {
		return domain.Run{}, fmt.Errorf(
			"%w: run=%s expected=%d actual=%d",
			ErrConflict,
			runID,
			expectedVersion,
			run.Version,
		)
	}
	if run.Status != domain.StatusProvisioning {
		return domain.Run{}, fmt.Errorf("cannot attach sandbox while run is %s", run.Status)
	}
	if run.SandboxID != "" {
		return domain.Run{}, fmt.Errorf("sandbox is already attached: %s", run.SandboxID)
	}
	run.SandboxID = sandboxID
	run.Version++
	m.runs[runID] = run
	m.appendEventLocked(runID, domain.EventSandboxCreated, map[string]any{
		"sandbox_id": sandboxID,
	})
	return run, nil
}

// RecordSandboxCleanup persists the cleanup outcome before any terminal event.
func (m *MemoryStore) RecordSandboxCleanup(
	ctx context.Context,
	runID string,
	expectedVersion int64,
	sandboxID string,
	deleted bool,
) (domain.Run, error) {
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}
	if sandboxID == "" {
		return domain.Run{}, fmt.Errorf("sandbox id must not be empty")
	}

	m.mu.Lock()
	defer m.mu.Unlock()
	if err := ctx.Err(); err != nil {
		return domain.Run{}, err
	}
	run, ok := m.runs[runID]
	if !ok {
		return domain.Run{}, fmt.Errorf("%w: %s", ErrNotFound, runID)
	}
	if run.Version != expectedVersion {
		return domain.Run{}, fmt.Errorf(
			"%w: run=%s expected=%d actual=%d",
			ErrConflict,
			runID,
			expectedVersion,
			run.Version,
		)
	}
	if run.Status.Terminal() {
		return domain.Run{}, fmt.Errorf("cannot record sandbox cleanup after run is %s", run.Status)
	}
	if run.SandboxCleanupRecorded {
		return domain.Run{}, fmt.Errorf("sandbox cleanup is already recorded")
	}
	if run.SandboxID != "" && run.SandboxID != sandboxID {
		return domain.Run{}, fmt.Errorf(
			"sandbox id mismatch: recorded=%s cleanup=%s",
			run.SandboxID,
			sandboxID,
		)
	}

	run.SandboxID = sandboxID
	run.SandboxCleanupRecorded = true
	run.SandboxDeleted = deleted
	run.Version++
	m.runs[runID] = run
	eventType := domain.EventSandboxDeleted
	data := map[string]any{"sandbox_id": sandboxID}
	if !deleted {
		eventType = domain.EventSandboxCleanupFailed
		data["code"] = "sandbox_cleanup_failed"
	}
	m.appendEventLocked(runID, eventType, data)
	return run, nil
}

func (m *MemoryStore) Events(ctx context.Context, runID string) ([]domain.Event, error) {
	if err := ctx.Err(); err != nil {
		return nil, err
	}

	m.mu.RLock()
	defer m.mu.RUnlock()
	if _, ok := m.runs[runID]; !ok {
		return nil, fmt.Errorf("%w: %s", ErrNotFound, runID)
	}
	events := m.events[runID]
	result := make([]domain.Event, len(events))
	for i, event := range events {
		result[i] = event
		result[i].Data = cloneData(event.Data)
	}
	return result, nil
}

func (m *MemoryStore) appendEventLocked(
	runID string,
	eventType domain.EventType,
	data map[string]any,
) {
	sequence := int64(len(m.events[runID]) + 1)
	m.events[runID] = append(m.events[runID], domain.Event{
		ID:            fmt.Sprintf("%s:%d", runID, sequence),
		RunID:         runID,
		Sequence:      sequence,
		Type:          eventType,
		OccurredAt:    m.clock().UTC(),
		SchemaVersion: 1,
		Data:          cloneData(data),
	})
}

func cloneData(data map[string]any) map[string]any {
	if data == nil {
		return map[string]any{}
	}
	copy := make(map[string]any, len(data))
	for key, value := range data {
		copy[key] = cloneJSONValue(value)
	}
	return copy
}

func cloneJSONValue(value any) any {
	cloned := cloneContainer(reflect.ValueOf(value))
	if !cloned.IsValid() {
		return nil
	}
	return cloned.Interface()
}

// cloneContainer recursively copies the acyclic map, slice, array, interface,
// and pointer containers accepted in JSON-compatible event data while
// preserving concrete Go types such as []string and map[string]string.
func cloneContainer(value reflect.Value) reflect.Value {
	if !value.IsValid() {
		return reflect.Value{}
	}

	switch value.Kind() {
	case reflect.Interface:
		if value.IsNil() {
			return reflect.Zero(value.Type())
		}
		cloned := cloneContainer(value.Elem())
		result := reflect.New(value.Type()).Elem()
		result.Set(cloned)
		return result
	case reflect.Map:
		if value.IsNil() {
			return reflect.Zero(value.Type())
		}
		result := reflect.MakeMapWithSize(value.Type(), value.Len())
		iterator := value.MapRange()
		for iterator.Next() {
			result.SetMapIndex(iterator.Key(), cloneContainer(iterator.Value()))
		}
		return result
	case reflect.Slice:
		if value.IsNil() {
			return reflect.Zero(value.Type())
		}
		result := reflect.MakeSlice(value.Type(), value.Len(), value.Len())
		for i := 0; i < value.Len(); i++ {
			result.Index(i).Set(cloneContainer(value.Index(i)))
		}
		return result
	case reflect.Array:
		result := reflect.New(value.Type()).Elem()
		for i := 0; i < value.Len(); i++ {
			result.Index(i).Set(cloneContainer(value.Index(i)))
		}
		return result
	case reflect.Pointer:
		if value.IsNil() {
			return reflect.Zero(value.Type())
		}
		result := reflect.New(value.Type().Elem())
		result.Elem().Set(cloneContainer(value.Elem()))
		return result
	default:
		return value
	}
}
