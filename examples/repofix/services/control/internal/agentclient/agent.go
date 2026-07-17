package agentclient

import (
	"context"
	"sync"
)

// Request contains only identifiers needed by the Fake decision service.
type Request struct {
	RunID     string
	TaskID    string
	SandboxID string
}

// Candidate is an untrusted completion proposal. It is not proof of success.
type Candidate struct {
	Summary        string
	ClaimedSuccess bool
}

// Client runs the model decision loop and returns a candidate result.
type Client interface {
	Run(context.Context, Request) (Candidate, error)
}

// FakeClient is a deterministic Agent service replacement.
type FakeClient struct {
	mu        sync.Mutex
	Candidate Candidate
	Err       error
	Requests  []Request
}

var _ Client = (*FakeClient)(nil)

func (f *FakeClient) Run(ctx context.Context, request Request) (Candidate, error) {
	if err := ctx.Err(); err != nil {
		return Candidate{}, err
	}
	f.mu.Lock()
	defer f.mu.Unlock()
	f.Requests = append(f.Requests, request)
	if f.Err != nil {
		return Candidate{}, f.Err
	}
	return f.Candidate, nil
}

func (f *FakeClient) CallCount() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return len(f.Requests)
}
