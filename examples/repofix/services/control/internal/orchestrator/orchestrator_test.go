package orchestrator

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/agentclient"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/repository"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/sandbox"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/verifier"
)

func TestExecuteRequiresIndependentVerificationBeforeSuccess(t *testing.T) {
	t.Parallel()

	store, run := newStoredRun(t)
	boxes := &sandbox.FakeManager{InstanceID: "box-1"}
	agent := &agentclient.FakeClient{Candidate: agentclient.Candidate{
		Summary:        "the model claims it is fixed",
		ClaimedSuccess: true,
	}}
	independent := &verifier.FakeVerifier{Result: verifier.Result{
		TestsPassed:       true,
		WorkspaceRevision: 4,
		TestedRevision:    4,
	}}

	got, err := New(store, boxes, agent, independent).Execute(context.Background(), run.ID)
	if err != nil {
		t.Fatalf("Execute() error = %v", err)
	}
	if got.Status != domain.StatusSucceeded {
		t.Fatalf("status = %q, want succeeded", got.Status)
	}
	if independent.CallCount() != 1 {
		t.Fatalf("verifier calls = %d, want 1", independent.CallCount())
	}
	if boxes.DeleteCount() != 1 {
		t.Fatalf("sandbox deletes = %d, want 1", boxes.DeleteCount())
	}
	if !got.SandboxCleanupRecorded || !got.SandboxDeleted {
		t.Fatalf("cleanup state = recorded:%v deleted:%v, want true/true", got.SandboxCleanupRecorded, got.SandboxDeleted)
	}
	assertEventTypes(t, store, run.ID, []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
		domain.EventSandboxDeleted,
		domain.EventRunSucceeded,
	})
}

func TestExecuteRejectsAgentSuccessClaimWhenVerifierRejects(t *testing.T) {
	t.Parallel()

	store, run := newStoredRun(t)
	boxes := &sandbox.FakeManager{InstanceID: "box-1"}
	agent := &agentclient.FakeClient{Candidate: agentclient.Candidate{
		Summary:        "trust the Agent",
		ClaimedSuccess: true,
	}}
	independent := &verifier.FakeVerifier{Result: verifier.Result{
		TestsPassed:       true,
		WorkspaceRevision: 2,
		TestedRevision:    1,
	}}

	got, err := New(store, boxes, agent, independent).Execute(context.Background(), run.ID)
	if !errors.Is(err, ErrVerificationRejected) {
		t.Fatalf("Execute() error = %v, want ErrVerificationRejected", err)
	}
	if got.Status != domain.StatusFailed {
		t.Fatalf("status = %q, want failed", got.Status)
	}
	if got.FailureCode != "verification_rejected" {
		t.Fatalf("failure code = %q, want verification_rejected", got.FailureCode)
	}
	if boxes.DeleteCount() != 1 {
		t.Fatalf("sandbox deletes = %d, want 1", boxes.DeleteCount())
	}
	assertEventTypes(t, store, run.ID, []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
		domain.EventSandboxDeleted,
		domain.EventRunFailed,
	})
}

func TestExecuteFailureAndCancellationPaths(t *testing.T) {
	t.Parallel()

	agentFailure := errors.New("agent unavailable")
	createFailure := errors.New("sandbox unavailable")
	tests := []struct {
		name              string
		context           func() context.Context
		createErr         error
		deleteErr         error
		agentErr          error
		verifierErr       error
		verification      verifier.Result
		wantStatus        domain.RunStatus
		wantFailureCode   string
		wantCreates       int
		wantDeletes       int
		wantAgentCalls    int
		wantVerifierCalls int
		wantEvents        []domain.EventType
	}{
		{
			name: "cancelled before sandbox creation",
			context: func() context.Context {
				ctx, cancel := context.WithCancel(context.Background())
				cancel()
				return ctx
			},
			wantStatus:      domain.StatusCancelled,
			wantFailureCode: "cancelled",
			wantEvents:      []domain.EventType{domain.EventRunCancelled},
		},
		{
			name: "deadline before sandbox creation",
			context: func() context.Context {
				ctx, cancel := context.WithDeadline(context.Background(), time.Unix(0, 0))
				cancel()
				return ctx
			},
			wantStatus:      domain.StatusTimedOut,
			wantFailureCode: "deadline_exceeded",
			wantEvents:      []domain.EventType{domain.EventRunTimedOut},
		},
		{
			name:            "sandbox creation fails",
			context:         context.Background,
			createErr:       createFailure,
			wantStatus:      domain.StatusFailed,
			wantFailureCode: "sandbox_create_failed",
			wantCreates:     1,
			wantEvents:      []domain.EventType{domain.EventRunFailed},
		},
		{
			name:            "agent fails",
			context:         context.Background,
			agentErr:        agentFailure,
			wantStatus:      domain.StatusFailed,
			wantFailureCode: "agent_failed",
			wantCreates:     1,
			wantDeletes:     1,
			wantAgentCalls:  1,
			wantEvents: []domain.EventType{
				domain.EventSandboxCreated,
				domain.EventRunStarted,
				domain.EventSandboxDeleted,
				domain.EventRunFailed,
			},
		},
		{
			name:            "agent reports cancellation",
			context:         context.Background,
			agentErr:        context.Canceled,
			wantStatus:      domain.StatusCancelled,
			wantFailureCode: "cancelled",
			wantCreates:     1,
			wantDeletes:     1,
			wantAgentCalls:  1,
			wantEvents: []domain.EventType{
				domain.EventSandboxCreated,
				domain.EventRunStarted,
				domain.EventSandboxDeleted,
				domain.EventRunCancelled,
			},
		},
		{
			name:            "agent failure and sandbox cleanup failure",
			context:         context.Background,
			deleteErr:       errors.New("delete failed"),
			agentErr:        agentFailure,
			wantStatus:      domain.StatusFailed,
			wantFailureCode: "sandbox_cleanup_failed",
			wantCreates:     1,
			wantDeletes:     1,
			wantAgentCalls:  1,
			wantEvents: []domain.EventType{
				domain.EventSandboxCreated,
				domain.EventRunStarted,
				domain.EventSandboxCleanupFailed,
				domain.EventRunFailed,
			},
		},
		{
			name:              "verifier fails",
			context:           context.Background,
			verifierErr:       errors.New("oracle unavailable"),
			wantStatus:        domain.StatusFailed,
			wantFailureCode:   "verification_failed",
			wantCreates:       1,
			wantDeletes:       1,
			wantAgentCalls:    1,
			wantVerifierCalls: 1,
			wantEvents: []domain.EventType{
				domain.EventSandboxCreated,
				domain.EventRunStarted,
				domain.EventSandboxDeleted,
				domain.EventRunFailed,
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			store, run := newStoredRun(t)
			boxes := &sandbox.FakeManager{
				InstanceID: "box-1",
				CreateErr:  test.createErr,
				DeleteErr:  test.deleteErr,
			}
			agent := &agentclient.FakeClient{
				Candidate: agentclient.Candidate{Summary: "candidate", ClaimedSuccess: true},
				Err:       test.agentErr,
			}
			independent := &verifier.FakeVerifier{
				Result: test.verification,
				Err:    test.verifierErr,
			}

			got, err := New(store, boxes, agent, independent).Execute(test.context(), run.ID)
			if err == nil {
				t.Fatal("Execute() error = nil, want failure")
			}
			if got.Status != test.wantStatus {
				t.Fatalf("status = %q, want %q", got.Status, test.wantStatus)
			}
			if got.FailureCode != test.wantFailureCode {
				t.Fatalf("failure code = %q, want %q", got.FailureCode, test.wantFailureCode)
			}
			if boxes.CreateCount() != test.wantCreates {
				t.Errorf("sandbox creates = %d, want %d", boxes.CreateCount(), test.wantCreates)
			}
			if boxes.DeleteCount() != test.wantDeletes {
				t.Errorf("sandbox deletes = %d, want %d", boxes.DeleteCount(), test.wantDeletes)
			}
			if agent.CallCount() != test.wantAgentCalls {
				t.Errorf("agent calls = %d, want %d", agent.CallCount(), test.wantAgentCalls)
			}
			if independent.CallCount() != test.wantVerifierCalls {
				t.Errorf(
					"verifier calls = %d, want %d",
					independent.CallCount(),
					test.wantVerifierCalls,
				)
			}
			assertEventTypes(t, store, run.ID, test.wantEvents)
		})
	}
}

func TestExecuteRecordsCleanupFailureBeforeFailedTerminalState(t *testing.T) {
	t.Parallel()

	store, run := newStoredRun(t)
	boxes := &sandbox.FakeManager{
		InstanceID: "box-1",
		DeleteErr:  errors.New("delete failed"),
	}
	agent := &agentclient.FakeClient{Candidate: agentclient.Candidate{
		Summary:        "verified fix",
		ClaimedSuccess: true,
	}}
	independent := &verifier.FakeVerifier{Result: verifier.Result{
		TestsPassed:       true,
		WorkspaceRevision: 1,
		TestedRevision:    1,
	}}

	got, err := New(store, boxes, agent, independent).Execute(context.Background(), run.ID)
	if !errors.Is(err, ErrSandboxCleanup) {
		t.Fatalf("Execute() error = %v, want ErrSandboxCleanup", err)
	}
	if got.Status != domain.StatusFailed {
		t.Fatalf("status = %q, want failed", got.Status)
	}
	if got.FailureCode != "sandbox_cleanup_failed" {
		t.Fatalf("failure code = %q, want sandbox_cleanup_failed", got.FailureCode)
	}
	if !got.SandboxCleanupRecorded || got.SandboxDeleted {
		t.Fatalf("cleanup state = recorded:%v deleted:%v, want true/false", got.SandboxCleanupRecorded, got.SandboxDeleted)
	}
	if boxes.DeleteCount() != 1 {
		t.Fatalf("sandbox deletes = %d, want 1", boxes.DeleteCount())
	}
	assertEventTypes(t, store, run.ID, []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
		domain.EventSandboxCleanupFailed,
		domain.EventRunFailed,
	})
	events, eventsErr := store.Events(context.Background(), run.ID)
	if eventsErr != nil {
		t.Fatal(eventsErr)
	}
	if code, ok := events[2].Data["code"].(string); !ok || code != "sandbox_cleanup_failed" {
		t.Fatalf("sandbox.cleanup_failed data = %#v, want cleanup failure code", events[2].Data)
	}
}

func TestExecuteDefensivelyHandlesEmptySandboxID(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name            string
		deleteErr       error
		wantFailureCode string
		wantCleanupErr  bool
	}{
		{
			name:            "best effort cleanup succeeds",
			wantFailureCode: "sandbox_invalid_id",
		},
		{
			name:            "best effort cleanup fails",
			deleteErr:       errors.New("cannot recover partial sandbox"),
			wantFailureCode: "sandbox_cleanup_failed",
			wantCleanupErr:  true,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			store, run := newStoredRun(t)
			boxes := &sandbox.FakeManager{
				ReturnEmptyID: true,
				DeleteErr:     test.deleteErr,
			}
			agent := &agentclient.FakeClient{}
			independent := &verifier.FakeVerifier{}

			got, err := New(store, boxes, agent, independent).
				Execute(context.Background(), run.ID)
			if !errors.Is(err, ErrInvalidSandboxID) {
				t.Fatalf("Execute() error = %v, want ErrInvalidSandboxID", err)
			}
			if errors.Is(err, ErrSandboxCleanup) != test.wantCleanupErr {
				t.Fatalf("cleanup error match = %v, want %v", errors.Is(err, ErrSandboxCleanup), test.wantCleanupErr)
			}
			if got.Status != domain.StatusFailed || got.FailureCode != test.wantFailureCode {
				t.Fatalf("terminal run = %+v, want failed/%s", got, test.wantFailureCode)
			}
			if boxes.CreateCount() != 1 || boxes.DeleteCount() != 1 {
				t.Fatalf("sandbox lifecycle creates=%d deletes=%d, want 1/1", boxes.CreateCount(), boxes.DeleteCount())
			}
			if agent.CallCount() != 0 || independent.CallCount() != 0 {
				t.Fatal("Agent and verifier must not run for an invalid sandbox handle")
			}
			assertEventTypes(t, store, run.ID, []domain.EventType{domain.EventRunFailed})
		})
	}
}

func TestExecuteCleansUpAfterRepositoryBoundaryFailures(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name            string
		configure       func(*faultStore)
		wantFailureCode string
		wantEvents      []domain.EventType
	}{
		{
			name: "sandbox attachment fails",
			configure: func(store *faultStore) {
				store.attachErr = errors.New("attach failed")
			},
			wantFailureCode: "sandbox_record_failed",
			wantEvents: []domain.EventType{
				domain.EventSandboxDeleted,
				domain.EventRunFailed,
			},
		},
		{
			name: "running transition fails",
			configure: func(store *faultStore) {
				store.runningErr = errors.New("running transition failed")
			},
			wantFailureCode: "run_start_failed",
			wantEvents: []domain.EventType{
				domain.EventSandboxCreated,
				domain.EventSandboxDeleted,
				domain.EventRunFailed,
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			base, run := newStoredRun(t)
			store := &faultStore{Store: base}
			test.configure(store)
			boxes := &sandbox.FakeManager{InstanceID: "box-1"}
			agent := &agentclient.FakeClient{}
			independent := &verifier.FakeVerifier{}

			got, err := New(store, boxes, agent, independent).
				Execute(context.Background(), run.ID)
			if err == nil {
				t.Fatal("Execute() error = nil, want injected boundary failure")
			}
			if got.Status != domain.StatusFailed || got.FailureCode != test.wantFailureCode {
				t.Fatalf("terminal run = %+v, want failed/%s", got, test.wantFailureCode)
			}
			if boxes.DeleteCount() != 1 {
				t.Fatalf("sandbox deletes = %d, want 1", boxes.DeleteCount())
			}
			if agent.CallCount() != 0 || independent.CallCount() != 0 {
				t.Fatal("Agent and verifier must not run after persistence boundary failure")
			}
			assertEventTypes(t, base, run.ID, test.wantEvents)
		})
	}
}

func TestExecuteRecoversCleanupRecordWriteAmbiguity(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name            string
		configure       func(*faultStore)
		wantRecordCalls int
	}{
		{
			name: "transient failure before commit",
			configure: func(store *faultStore) {
				store.cleanupFailures = 1
			},
			wantRecordCalls: 2,
		},
		{
			name: "commit succeeds but response is lost",
			configure: func(store *faultStore) {
				store.cleanupCommitThenError = true
			},
			wantRecordCalls: 1,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			base, run := newStoredRun(t)
			store := &faultStore{
				Store:      base,
				cleanupErr: errors.New("cleanup record unavailable"),
			}
			test.configure(store)
			boxes := &sandbox.FakeManager{InstanceID: "box-1"}
			agent := verifiedAgent()
			independent := passingVerifier()

			got, err := New(store, boxes, agent, independent).
				Execute(context.Background(), run.ID)
			if err != nil {
				t.Fatalf("Execute() error = %v", err)
			}
			if got.Status != domain.StatusSucceeded {
				t.Fatalf("status = %q, want succeeded", got.Status)
			}
			if store.cleanupCalls != test.wantRecordCalls {
				t.Fatalf("cleanup record calls = %d, want %d", store.cleanupCalls, test.wantRecordCalls)
			}
			assertEventTypes(t, base, run.ID, []domain.EventType{
				domain.EventSandboxCreated,
				domain.EventRunStarted,
				domain.EventSandboxDeleted,
				domain.EventRunSucceeded,
			})
		})
	}
}

func TestExecuteLeavesRunNonTerminalWhenCleanupRecordPersistentlyFails(t *testing.T) {
	t.Parallel()

	base, run := newStoredRun(t)
	store := &faultStore{
		Store:           base,
		cleanupErr:      errors.New("cleanup record unavailable"),
		cleanupFailures: 2,
	}
	boxes := &sandbox.FakeManager{InstanceID: "box-1"}

	got, err := New(store, boxes, verifiedAgent(), passingVerifier()).
		Execute(context.Background(), run.ID)
	if !errors.Is(err, ErrCleanupRecord) {
		t.Fatalf("Execute() error = %v, want ErrCleanupRecord", err)
	}
	if got.Status != domain.StatusRunning || got.SandboxCleanupRecorded {
		t.Fatalf("run = %+v, want running with cleanup unrecorded", got)
	}
	if boxes.DeleteCount() != 1 || store.cleanupCalls != 2 {
		t.Fatalf("delete calls=%d record calls=%d, want 1/2", boxes.DeleteCount(), store.cleanupCalls)
	}
	assertEventTypes(t, base, run.ID, []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
	})
}

func TestExecuteCancellationAfterVerificationWinsBeforeSuccess(t *testing.T) {
	t.Parallel()

	store, run := newStoredRun(t)
	boxes := &sandbox.FakeManager{InstanceID: "box-1"}
	agent := &agentclient.FakeClient{Candidate: agentclient.Candidate{
		Summary:        "candidate",
		ClaimedSuccess: true,
	}}
	ctx, cancel := context.WithCancel(context.Background())
	independent := cancelOnVerify{cancel: cancel}

	got, err := New(store, boxes, agent, independent).Execute(ctx, run.ID)
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("Execute() error = %v, want context.Canceled", err)
	}
	if got.Status != domain.StatusCancelled {
		t.Fatalf("status = %q, want cancelled", got.Status)
	}
	assertEventTypes(t, store, run.ID, []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
		domain.EventSandboxDeleted,
		domain.EventRunCancelled,
	})
}

func TestExecuteCancellationAtSuccessCommitBoundary(t *testing.T) {
	t.Parallel()

	base, run := newStoredRun(t)
	ctx, cancel := context.WithCancel(context.Background())
	store := &faultStore{
		Store:         base,
		beforeSuccess: cancel,
	}
	boxes := &sandbox.FakeManager{InstanceID: "box-1"}

	got, err := New(store, boxes, verifiedAgent(), passingVerifier()).Execute(ctx, run.ID)
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("Execute() error = %v, want context.Canceled", err)
	}
	if got.Status != domain.StatusCancelled {
		t.Fatalf("status = %q, want cancelled", got.Status)
	}
	assertEventTypes(t, base, run.ID, []domain.EventType{
		domain.EventSandboxCreated,
		domain.EventRunStarted,
		domain.EventSandboxDeleted,
		domain.EventRunCancelled,
	})
}

type cancelOnVerify struct {
	cancel context.CancelFunc
}

type faultStore struct {
	repository.Store
	attachErr              error
	runningErr             error
	cleanupErr             error
	cleanupFailures        int
	cleanupCommitThenError bool
	cleanupCalls           int
	beforeSuccess          func()
}

var _ repository.Store = (*faultStore)(nil)

func (s *faultStore) AttachSandbox(
	ctx context.Context,
	runID string,
	expectedVersion int64,
	sandboxID string,
) (domain.Run, error) {
	if s.attachErr != nil {
		return domain.Run{}, s.attachErr
	}
	return s.Store.AttachSandbox(ctx, runID, expectedVersion, sandboxID)
}

func (s *faultStore) Transition(
	ctx context.Context,
	runID string,
	change repository.Transition,
) (domain.Run, error) {
	if change.Next == domain.StatusRunning && s.runningErr != nil {
		return domain.Run{}, s.runningErr
	}
	if change.Next == domain.StatusSucceeded && s.beforeSuccess != nil {
		callback := s.beforeSuccess
		s.beforeSuccess = nil
		callback()
	}
	return s.Store.Transition(ctx, runID, change)
}

func (s *faultStore) RecordSandboxCleanup(
	ctx context.Context,
	runID string,
	expectedVersion int64,
	sandboxID string,
	deleted bool,
) (domain.Run, error) {
	s.cleanupCalls++
	if s.cleanupCommitThenError {
		s.cleanupCommitThenError = false
		_, err := s.Store.RecordSandboxCleanup(
			ctx,
			runID,
			expectedVersion,
			sandboxID,
			deleted,
		)
		if err != nil {
			return domain.Run{}, err
		}
		return domain.Run{}, s.cleanupErr
	}
	if s.cleanupFailures > 0 {
		s.cleanupFailures--
		return domain.Run{}, s.cleanupErr
	}
	return s.Store.RecordSandboxCleanup(
		ctx,
		runID,
		expectedVersion,
		sandboxID,
		deleted,
	)
}

func verifiedAgent() *agentclient.FakeClient {
	return &agentclient.FakeClient{Candidate: agentclient.Candidate{
		Summary:        "verified candidate",
		ClaimedSuccess: true,
	}}
}

func passingVerifier() *verifier.FakeVerifier {
	return &verifier.FakeVerifier{Result: verifier.Result{
		TestsPassed:       true,
		WorkspaceRevision: 1,
		TestedRevision:    1,
	}}
}

func (v cancelOnVerify) Verify(
	_ context.Context,
	_ string,
	_ agentclient.Candidate,
) (verifier.Result, error) {
	v.cancel()
	return verifier.Result{
		TestsPassed:       true,
		WorkspaceRevision: 1,
		TestedRevision:    1,
	}, nil
}

func newStoredRun(t *testing.T) (*repository.MemoryStore, domain.Run) {
	t.Helper()
	store := repository.NewMemoryStore()
	run, err := domain.NewRun("run-1", "task-1")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Create(context.Background(), run); err != nil {
		t.Fatal(err)
	}
	return store, run
}

func assertEventTypes(
	t *testing.T,
	store *repository.MemoryStore,
	runID string,
	want []domain.EventType,
) {
	t.Helper()
	events, err := store.Events(context.Background(), runID)
	if err != nil {
		t.Fatal(err)
	}
	if len(events) != len(want) {
		t.Fatalf("event count = %d, want %d", len(events), len(want))
	}
	for i, event := range events {
		if event.Type != want[i] {
			t.Errorf("event %d type = %q, want %q", i, event.Type, want[i])
		}
		if event.Sequence != int64(i+1) {
			t.Errorf("event %d sequence = %d, want %d", i, event.Sequence, i+1)
		}
	}
}
