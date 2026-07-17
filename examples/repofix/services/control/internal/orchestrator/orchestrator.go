package orchestrator

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/agentclient"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/domain"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/repository"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/sandbox"
	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/verifier"
)

var (
	ErrVerificationRejected = errors.New("independent verification rejected candidate")
	ErrSandboxCleanup       = errors.New("sandbox cleanup failed")
	ErrCleanupRecord        = errors.New("sandbox cleanup result could not be recorded")
	ErrInvalidSandboxID     = errors.New("sandbox manager returned an empty id")
)

const defaultControlTimeout = 2 * time.Second

// Orchestrator owns the deterministic lifecycle around one Agent run.
type Orchestrator struct {
	runs           repository.Store
	sandboxes      sandbox.Manager
	agent          agentclient.Client
	verifier       verifier.Verifier
	controlTimeout time.Duration
}

func New(
	runs repository.Store,
	sandboxes sandbox.Manager,
	agent agentclient.Client,
	independentVerifier verifier.Verifier,
) *Orchestrator {
	return &Orchestrator{
		runs:           runs,
		sandboxes:      sandboxes,
		agent:          agent,
		verifier:       independentVerifier,
		controlTimeout: defaultControlTimeout,
	}
}

// Execute runs one pending Run through provisioning, Agent execution, independent
// verification, sandbox cleanup, and one terminal transition. If cleanup
// evidence cannot be persisted, it deliberately leaves the Run non-terminal so
// a recovery worker can retry without publishing a terminal event out of order.
func (o *Orchestrator) Execute(ctx context.Context, runID string) (run domain.Run, err error) {
	run, err = o.getRun(ctx, runID)
	if err != nil {
		return domain.Run{}, err
	}
	if run.Status != domain.StatusPending {
		return run, fmt.Errorf("run %s must be pending, got %s", run.ID, run.Status)
	}

	run, err = o.transition(ctx, run, repository.Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusProvisioning,
	})
	if err != nil {
		return run, err
	}
	if cause := ctx.Err(); cause != nil {
		return o.finishFromError(ctx, run, "run_interrupted", cause)
	}

	box, createErr := o.sandboxes.Create(ctx, run)
	if createErr != nil {
		return o.finishFromError(ctx, run, "sandbox_create_failed", createErr)
	}
	if box.ID == "" {
		return o.finishInvalidSandbox(ctx, run)
	}
	attached, attachErr := o.attachSandbox(ctx, run, box.ID)
	if attachErr != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "sandbox_record_failed", attachErr)
	}
	run = attached
	if cause := ctx.Err(); cause != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "run_interrupted", cause)
	}

	running, startErr := o.transition(ctx, run, repository.Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusRunning,
		EventType:       domain.EventRunStarted,
		EventData: map[string]any{
			"sandbox_id": box.ID,
		},
	})
	if startErr != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "run_start_failed", startErr)
	}
	run = running

	candidate, agentErr := o.agent.Run(ctx, agentclient.Request{
		RunID:     run.ID,
		TaskID:    run.TaskID,
		SandboxID: box.ID,
	})
	if agentErr != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "agent_failed", agentErr)
	}
	if cause := ctx.Err(); cause != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "run_interrupted", cause)
	}

	verified, verifyErr := o.verifier.Verify(ctx, box.ID, candidate)
	if verifyErr != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "verification_failed", verifyErr)
	}
	if !verified.Accepted() {
		return o.finishAfterCleanup(
			ctx,
			run,
			box.ID,
			"verification_rejected",
			ErrVerificationRejected,
		)
	}
	if cause := ctx.Err(); cause != nil {
		return o.finishAfterCleanup(ctx, run, box.ID, "run_interrupted", cause)
	}

	cleaned, cleanupErr, recordErr := o.cleanupSandbox(ctx, run, box.ID)
	if recordErr != nil {
		return cleaned, errors.Join(cleanupErr, recordErr)
	}
	if cleanupErr != nil {
		return o.finishTerminal(
			ctx,
			cleaned,
			domain.StatusFailed,
			domain.EventRunFailed,
			"sandbox_cleanup_failed",
			cleanupErr,
		)
	}
	run = cleaned
	if cause := ctx.Err(); cause != nil {
		return o.finishFromError(ctx, run, "run_interrupted", cause)
	}

	succeeded, succeedErr := o.transitionAtSuccessBoundary(ctx, run, repository.Transition{
		ExpectedVersion: run.Version,
		Next:            domain.StatusSucceeded,
		EventType:       domain.EventRunSucceeded,
		EventData: map[string]any{
			"summary":           candidate.Summary,
			"verified_revision": verified.WorkspaceRevision,
		},
	})
	if succeedErr != nil {
		if errors.Is(succeedErr, context.Canceled) ||
			errors.Is(succeedErr, context.DeadlineExceeded) {
			return o.finishFromError(ctx, run, "run_interrupted", succeedErr)
		}
		return run, succeedErr
	}
	return succeeded, nil
}

func (o *Orchestrator) finishInvalidSandbox(
	ctx context.Context,
	run domain.Run,
) (domain.Run, error) {
	// A malformed successful Create response has no correlatable ID, so a
	// sandbox lifecycle event cannot be emitted truthfully. The Manager contract
	// requires the provider to self-clean; Delete("") is an additional best-effort
	// cleanup request for adapters that can recover their last partial create.
	cleanupCtx, cancel := context.WithTimeout(context.Background(), o.controlTimeout)
	cleanupErr := o.sandboxes.Delete(cleanupCtx, "")
	cancel()
	if cleanupErr != nil {
		return o.finishTerminal(
			ctx,
			run,
			domain.StatusFailed,
			domain.EventRunFailed,
			"sandbox_cleanup_failed",
			errors.Join(ErrInvalidSandboxID, ErrSandboxCleanup, cleanupErr),
		)
	}
	return o.finishTerminal(
		ctx,
		run,
		domain.StatusFailed,
		domain.EventRunFailed,
		"sandbox_invalid_id",
		ErrInvalidSandboxID,
	)
}

func (o *Orchestrator) finishAfterCleanup(
	ctx context.Context,
	run domain.Run,
	sandboxID string,
	failureCode string,
	cause error,
) (domain.Run, error) {
	cleaned, cleanupErr, recordErr := o.cleanupSandbox(ctx, run, sandboxID)
	if recordErr != nil {
		return cleaned, errors.Join(cause, cleanupErr, recordErr)
	}
	if cleanupErr != nil {
		return o.finishTerminal(
			ctx,
			cleaned,
			domain.StatusFailed,
			domain.EventRunFailed,
			"sandbox_cleanup_failed",
			errors.Join(cause, cleanupErr),
		)
	}
	return o.finishFromError(ctx, cleaned, failureCode, cause)
}

func (o *Orchestrator) cleanupSandbox(
	ctx context.Context,
	run domain.Run,
	sandboxID string,
) (domain.Run, error, error) {
	cleanupCtx, cancel := context.WithTimeout(context.Background(), o.controlTimeout)
	deleteErr := o.sandboxes.Delete(cleanupCtx, sandboxID)
	cancel()

	recorded, recordErr := o.persistSandboxCleanup(ctx, run, sandboxID, deleteErr == nil)
	if recordErr != nil {
		var cleanupErr error
		if deleteErr != nil {
			cleanupErr = errors.Join(ErrSandboxCleanup, deleteErr)
		}
		return recorded, cleanupErr, fmt.Errorf("%w: %w", ErrCleanupRecord, recordErr)
	}
	if deleteErr != nil {
		return recorded, errors.Join(ErrSandboxCleanup, deleteErr), nil
	}
	return recorded, nil, nil
}

func (o *Orchestrator) finishFromError(
	ctx context.Context,
	run domain.Run,
	failureCode string,
	cause error,
) (domain.Run, error) {
	status, eventType, code := classifyFailure(failureCode, cause)
	return o.finishTerminal(ctx, run, status, eventType, code, cause)
}

func (o *Orchestrator) finishTerminal(
	ctx context.Context,
	run domain.Run,
	status domain.RunStatus,
	eventType domain.EventType,
	failureCode string,
	cause error,
) (domain.Run, error) {
	finished, transitionErr := o.transition(ctx, run, repository.Transition{
		ExpectedVersion: run.Version,
		Next:            status,
		FailureCode:     failureCode,
		EventType:       eventType,
		EventData: map[string]any{
			"code": failureCode,
		},
	})
	if transitionErr != nil {
		return run, errors.Join(cause, transitionErr)
	}
	return finished, cause
}

func classifyFailure(
	failureCode string,
	cause error,
) (domain.RunStatus, domain.EventType, string) {
	if errors.Is(cause, context.Canceled) {
		return domain.StatusCancelled, domain.EventRunCancelled, "cancelled"
	}
	if errors.Is(cause, context.DeadlineExceeded) {
		return domain.StatusTimedOut, domain.EventRunTimedOut, "deadline_exceeded"
	}
	return domain.StatusFailed, domain.EventRunFailed, failureCode
}

func (o *Orchestrator) getRun(ctx context.Context, runID string) (domain.Run, error) {
	controlCtx, cancel := o.controlContext(ctx)
	defer cancel()
	return o.runs.Get(controlCtx, runID)
}

func (o *Orchestrator) transition(
	ctx context.Context,
	run domain.Run,
	change repository.Transition,
) (domain.Run, error) {
	controlCtx, cancel := o.controlContext(ctx)
	defer cancel()
	return o.runs.Transition(controlCtx, run.ID, change)
}

func (o *Orchestrator) attachSandbox(
	ctx context.Context,
	run domain.Run,
	sandboxID string,
) (domain.Run, error) {
	controlCtx, cancel := o.controlContext(ctx)
	defer cancel()
	return o.runs.AttachSandbox(controlCtx, run.ID, run.Version, sandboxID)
}

func (o *Orchestrator) persistSandboxCleanup(
	ctx context.Context,
	run domain.Run,
	sandboxID string,
	deleted bool,
) (domain.Run, error) {
	recorded, firstErr := o.recordSandboxCleanupOnce(ctx, run, sandboxID, deleted)
	if firstErr == nil {
		return recorded, nil
	}

	// A write may fail before commit or may commit and lose its response. Read
	// back once: accept an identical durable outcome, otherwise retry once at the
	// latest version. Persistent failure intentionally leaves the Run non-terminal.
	latest, getErr := o.getRun(ctx, run.ID)
	if getErr != nil {
		return run, errors.Join(firstErr, getErr)
	}
	if latest.SandboxCleanupRecorded {
		if latest.SandboxID == sandboxID && latest.SandboxDeleted == deleted {
			return latest, nil
		}
		return latest, errors.Join(firstErr, repository.ErrConflict)
	}
	retried, retryErr := o.recordSandboxCleanupOnce(ctx, latest, sandboxID, deleted)
	if retryErr != nil {
		return latest, errors.Join(firstErr, retryErr)
	}
	return retried, nil
}

func (o *Orchestrator) recordSandboxCleanupOnce(
	ctx context.Context,
	run domain.Run,
	sandboxID string,
	deleted bool,
) (domain.Run, error) {
	controlCtx, cancel := o.controlContext(ctx)
	defer cancel()
	return o.runs.RecordSandboxCleanup(
		controlCtx,
		run.ID,
		run.Version,
		sandboxID,
		deleted,
	)
}

// transitionAtSuccessBoundary gives cancellation a precise commit rule: if the
// Repository observes cancellation before its atomic transition, cancellation
// wins; once the transition commits, success wins. Strict cross-process cancel
// ordering later requires a persisted cancel-request field in the same update.
func (o *Orchestrator) transitionAtSuccessBoundary(
	ctx context.Context,
	run domain.Run,
	change repository.Transition,
) (domain.Run, error) {
	return o.runs.Transition(ctx, run.ID, change)
}

func (o *Orchestrator) controlContext(ctx context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.WithoutCancel(ctx), o.controlTimeout)
}
