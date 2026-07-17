package repository

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
)

func TestMemoryStoreSequencesEventsAndRejectsStaleVersions(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	fixedTime := time.Date(2026, time.July, 17, 10, 0, 0, 0, time.UTC)
	store := NewMemoryStoreWithClock(func() time.Time { return fixedTime })
	run, err := domain.NewRun("run-1", "task-1")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Create(ctx, run); err != nil {
		t.Fatal(err)
	}

	run, err = store.Transition(ctx, run.ID, Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusProvisioning,
	})
	if err != nil {
		t.Fatal(err)
	}
	run, err = store.AttachSandbox(ctx, run.ID, run.Version, "box-1")
	if err != nil {
		t.Fatal(err)
	}
	runningVersion := run.Version
	run, err = store.Transition(ctx, run.ID, Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusRunning,
		EventType:       domain.EventRunStarted,
	})
	if err != nil {
		t.Fatal(err)
	}
	run, err = store.RecordSandboxCleanup(ctx, run.ID, run.Version, "box-1", true)
	if err != nil {
		t.Fatal(err)
	}
	run, err = store.Transition(ctx, run.ID, Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusSucceeded,
		EventType:       domain.EventRunSucceeded,
	})
	if err != nil {
		t.Fatal(err)
	}

	_, err = store.Transition(ctx, run.ID, Transition{
		ExpectedVersion: runningVersion,
		Next:            domain.StatusFailed,
	})
	if !errors.Is(err, ErrConflict) {
		t.Fatalf("stale transition error = %v, want ErrConflict", err)
	}

	events, err := store.Events(ctx, run.ID)
	if err != nil {
		t.Fatal(err)
	}
	wantTypes := []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
		domain.EventSandboxDeleted,
		domain.EventRunSucceeded,
	}
	if len(events) != len(wantTypes) {
		t.Fatalf("event count = %d, want %d", len(events), len(wantTypes))
	}
	for i, event := range events {
		wantSequence := int64(i + 1)
		if event.Sequence != wantSequence {
			t.Errorf("event %d sequence = %d, want %d", i, event.Sequence, wantSequence)
		}
		if event.Type != wantTypes[i] {
			t.Errorf("event %d type = %q, want %q", i, event.Type, wantTypes[i])
		}
		if event.SchemaVersion != 1 {
			t.Errorf("event %d schema version = %d, want 1", i, event.SchemaVersion)
		}
		if !event.OccurredAt.Equal(fixedTime) {
			t.Errorf("event %d time = %s, want %s", i, event.OccurredAt, fixedTime)
		}
	}
}

func TestMemoryStoreCopiesNestedEventData(t *testing.T) {
	t.Parallel()

	ctx := context.Background()
	store := NewMemoryStore()
	run, err := domain.NewRun("run-copy", "task-copy")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Create(ctx, run); err != nil {
		t.Fatal(err)
	}
	payload := map[string]any{
		"nested": map[string]any{
			"items": []any{"original"},
		},
		"typed_slice": []string{"original"},
		"typed_map":   map[string]string{"key": "original"},
	}
	run, err = store.Transition(ctx, run.ID, Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusCancelled,
		EventType:       domain.EventRunCancelled,
		EventData:       payload,
	})
	if err != nil {
		t.Fatal(err)
	}

	payload["nested"].(map[string]any)["items"].([]any)[0] = "mutated input"
	payload["typed_slice"].([]string)[0] = "mutated input"
	payload["typed_map"].(map[string]string)["key"] = "mutated input"
	events, err := store.Events(ctx, run.ID)
	if err != nil {
		t.Fatal(err)
	}
	items := events[0].Data["nested"].(map[string]any)["items"].([]any)
	items[0] = "mutated output"
	events[0].Data["typed_slice"].([]string)[0] = "mutated output"
	events[0].Data["typed_map"].(map[string]string)["key"] = "mutated output"

	again, err := store.Events(ctx, run.ID)
	if err != nil {
		t.Fatal(err)
	}
	got := again[0].Data["nested"].(map[string]any)["items"].([]any)[0]
	if got != "original" {
		t.Fatalf("stored nested data = %q, want original", got)
	}
	if got := again[0].Data["typed_slice"].([]string)[0]; got != "original" {
		t.Fatalf("stored typed slice = %q, want original", got)
	}
	if got := again[0].Data["typed_map"].(map[string]string)["key"]; got != "original" {
		t.Fatalf("stored typed map = %q, want original", got)
	}
}
