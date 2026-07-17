package verifier

import (
	"context"
	"sync"

	"github.com/nickdu2009/repofix-agent-book/examples/repofix/services/control/internal/agentclient"
)

// Result contains program-owned facts collected independently from the Agent.
type Result struct {
	TestsPassed       bool
	WorkspaceRevision int64
	TestedRevision    int64
}

// Accepted proves tests passed for the current workspace revision.
func (r Result) Accepted() bool {
	return r.TestsPassed && r.WorkspaceRevision == r.TestedRevision
}

// Verifier independently inspects the sandbox after the Agent returns a candidate.
type Verifier interface {
	Verify(context.Context, string, agentclient.Candidate) (Result, error)
}

// FakeVerifier returns configured independent facts and records its inputs.
type FakeVerifier struct {
	mu         sync.Mutex
	Result     Result
	Err        error
	SandboxIDs []string
	Candidates []agentclient.Candidate
}

var _ Verifier = (*FakeVerifier)(nil)

func (f *FakeVerifier) Verify(
	ctx context.Context,
	sandboxID string,
	candidate agentclient.Candidate,
) (Result, error) {
	if err := ctx.Err(); err != nil {
		return Result{}, err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.SandboxIDs = append(f.SandboxIDs, sandboxID)
	f.Candidates = append(f.Candidates, candidate)
	if f.Err != nil {
		return Result{}, f.Err
	}
	return f.Result, nil
}

func (f *FakeVerifier) CallCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.SandboxIDs)
}
