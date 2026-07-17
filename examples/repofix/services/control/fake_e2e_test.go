package control_test

import (
	"context"
	"testing"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/agentclient"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/orchestrator"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/repository"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/sandbox"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/verifier"
)

func TestFakeControlPlaneE2E(t *testing.T) {
	store := repository.NewMemoryStore()
	run, err := domain.NewRun("run-e2e", "task-e2e")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Create(context.Background(), run); err != nil {
		t.Fatal(err)
	}

	boxes := &sandbox.FakeManager{InstanceID: "box-e2e"}
	agent := &agentclient.FakeClient{Candidate: agentclient.Candidate{
		Summary:        "candidate patch",
		ClaimedSuccess: true,
	}}
	independent := &verifier.FakeVerifier{Result: verifier.Result{
		TestsPassed:       true,
		WorkspaceRevision: 3,
		TestedRevision:    3,
	}}

	completed, err := orchestrator.New(store, boxes, agent, independent).
		Execute(context.Background(), run.ID)
	if err != nil {
		t.Fatalf("Fake E2E failed: %v", err)
	}
	if completed.Status != domain.StatusSucceeded {
		t.Fatalf("status = %q, want succeeded", completed.Status)
	}
	if completed.SandboxID != "box-e2e" {
		t.Fatalf("sandbox id = %q, want box-e2e", completed.SandboxID)
	}
	if boxes.CreateCount() != 1 || boxes.DeleteCount() != 1 {
		t.Fatalf(
			"sandbox lifecycle creates=%d deletes=%d, want 1/1",
			boxes.CreateCount(),
			boxes.DeleteCount(),
		)
	}

	events, err := store.Events(context.Background(), run.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != 4 {
		t.Fatalf("events = %d, want 4", len(events))
	}
	for i, event := range events {
		if event.Sequence != int64(i+1) {
			t.Fatalf("event %d sequence = %d, want %d", i, event.Sequence, i+1)
		}
	}
	if events[2].Type != domain.EventSandboxDeleted {
		t.Fatalf("pre-terminal event = %q, want sandbox.deleted", events[2].Type)
	}
	if events[3].Type != domain.EventRunSucceeded {
		t.Fatalf("terminal event = %q, want run.succeeded", events[3].Type)
	}
}
