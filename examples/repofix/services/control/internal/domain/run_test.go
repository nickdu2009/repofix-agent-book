package domain

import (
	"fmt"
	"testing"
)

func TestRunTransitionMatrix(t *testing.T) {
	t.Parallel()

	statuses := []RunStatus{
		StatusPending,
		StatusProvisioning,
		StatusRunning,
		StatusSucceeded,
		StatusFailed,
		StatusCancelled,
		StatusTimedOut,
	}
	allowed := map[[2]RunStatus]bool{
		{StatusPending, StatusProvisioning}:   true,
		{StatusPending, StatusCancelled}:      true,
		{StatusProvisioning, StatusRunning}:   true,
		{StatusProvisioning, StatusFailed}:    true,
		{StatusProvisioning, StatusCancelled}: true,
		{StatusProvisioning, StatusTimedOut}:  true,
		{StatusRunning, StatusSucceeded}:      true,
		{StatusRunning, StatusFailed}:         true,
		{StatusRunning, StatusCancelled}:      true,
		{StatusRunning, StatusTimedOut}:       true,
	}

	for _, from := range statuses {
		for _, to := range statuses {
			t.Run(fmt.Sprintf("%s_to_%s", from, to), func(t *testing.T) {
				run := Run{ID: "run-1", TaskID: "task-1", Status: from, Version: 7}
				err := run.Transition(to)
				if allowed[[2]RunStatus{from, to}] {
					if err != nil {
						t.Fatalf("Transition() error = %v", err)
					}
					if run.Status != to {
						t.Fatalf("status = %q, want %q", run.Status, to)
					}
					if run.Version != 8 {
						t.Fatalf("version = %d, want 8", run.Version)
					}
					return
				}

				if err != nil {
					if run.Status != from || run.Version != 7 {
						t.Fatalf("illegal transition mutated run: %+v", run)
					}
					return
				}
				t.Fatal("Transition() succeeded for an illegal transition")
			})
		}
	}
}

func TestRunRequiresRecordedSandboxCleanupBeforeTerminalState(t *testing.T) {
	t.Parallel()

	tests := []struct {
		name    string
		run     Run
		next    RunStatus
		wantErr bool
	}{
		{
			name:    "sandbox not cleaned",
			run:     Run{Status: StatusRunning, SandboxID: "box-1"},
			next:    StatusFailed,
			wantErr: true,
		},
		{
			name: "failed cleanup permits failed terminal",
			run: Run{
				Status:                 StatusRunning,
				SandboxID:              "box-1",
				SandboxCleanupRecorded: true,
			},
			next: StatusFailed,
		},
		{
			name: "failed cleanup cannot succeed",
			run: Run{
				Status:                 StatusRunning,
				SandboxID:              "box-1",
				SandboxCleanupRecorded: true,
			},
			next:    StatusSucceeded,
			wantErr: true,
		},
		{
			name: "failed cleanup cannot finish as cancelled",
			run: Run{
				Status:                 StatusRunning,
				SandboxID:              "box-1",
				SandboxCleanupRecorded: true,
			},
			next:    StatusCancelled,
			wantErr: true,
		},
		{
			name: "successful cleanup permits success",
			run: Run{
				Status:                 StatusRunning,
				SandboxID:              "box-1",
				SandboxCleanupRecorded: true,
				SandboxDeleted:         true,
			},
			next: StatusSucceeded,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			err := test.run.Transition(test.next)
			if (err != nil) != test.wantErr {
				t.Fatalf("Transition() error = %v, wantErr %v", err, test.wantErr)
			}
		})
	}
}

func TestTerminalStatuses(t *testing.T) {
	t.Parallel()

	for _, status := range []RunStatus{
		StatusSucceeded,
		StatusFailed,
		StatusCancelled,
		StatusTimedOut,
	} {
		if !status.Terminal() {
			t.Errorf("%q should be terminal", status)
		}
	}
	for _, status := range []RunStatus{StatusPending, StatusProvisioning, StatusRunning} {
		if status.Terminal() {
			t.Errorf("%q should not be terminal", status)
		}
	}
}
