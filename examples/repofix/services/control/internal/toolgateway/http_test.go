package toolgateway

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"reflect"
	"strings"
	"testing"
)

func TestHandlerExecutesAuthorizedSemanticTool(t *testing.T) {
	requestFixture, err := os.ReadFile("../../../../contracts/fixtures/tool-call.request.json")
	if err != nil {
		t.Fatal(err)
	}
	responseFixture, err := os.ReadFile("../../../../contracts/fixtures/tool-result.response.json")
	if err != nil {
		t.Fatal(err)
	}
	var gotSandboxID string
	var gotArguments map[string]string
	handler := NewHandler(
		func(_ context.Context, capability string) (string, error) {
			if capability != "cap_short_lived" {
				t.Fatalf("capability = %q", capability)
			}
			return "box-1", nil
		},
		func(
			_ context.Context,
			sandboxID string,
			tool string,
			arguments map[string]string,
		) (Result, error) {
			gotSandboxID = sandboxID
			gotArguments = arguments
			if tool != "run_tests" {
				t.Fatalf("tool = %q", tool)
			}
			return Result{
				OK:                true,
				Output:            "1 passed",
				Metadata:          map[string]any{"exit_code": 0, "tested_revision": 2},
				WorkspaceRevision: 2,
			}, nil
		},
	)

	request := httptest.NewRequest(
		http.MethodPost,
		"/v1/tool-calls",
		strings.NewReader(string(requestFixture)),
	)
	request.Header.Set("Authorization", "Bearer cap_short_lived")
	request.Header.Set("X-Request-ID", "req-test")
	response := httptest.NewRecorder()

	handler.ServeHTTP(response, request)

	if response.Code != http.StatusOK {
		t.Fatalf("status = %d, body = %s", response.Code, response.Body.String())
	}
	if gotSandboxID != "box-1" || gotArguments["target"] != "unit" {
		t.Fatalf("sandbox=%q arguments=%v", gotSandboxID, gotArguments)
	}
	var result Result
	if err := json.NewDecoder(response.Body).Decode(&result); err != nil {
		t.Fatal(err)
	}
	if !result.OK || result.WorkspaceRevision != 2 {
		t.Fatalf("result = %+v", result)
	}
	var wantResult Result
	if err := json.Unmarshal(responseFixture, &wantResult); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(result, wantResult) {
		t.Fatalf("result = %+v, fixture = %+v", result, wantResult)
	}
}

func TestHandlerRejectsUnsafeOrMalformedCalls(t *testing.T) {
	handler := NewHandler(
		func(context.Context, string) (string, error) { return "box-1", nil },
		func(context.Context, string, string, map[string]string) (Result, error) {
			t.Fatal("execute must not be called")
			return Result{}, nil
		},
	)
	tests := []struct {
		name          string
		authorization string
		body          string
		wantStatus    int
	}{
		{"missing capability", "", `{"tool":"read_file","arguments":{"path":"a.py"},"timeout_ms":1000}`, http.StatusUnauthorized},
		{"arbitrary command", "Bearer cap", `{"tool":"run_command","arguments":{"command":"rm -rf /"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"command smuggled into test", "Bearer cap", `{"tool":"run_tests","arguments":{"target":"unit","command":"pytest"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"unknown test target", "Bearer cap", `{"tool":"run_tests","arguments":{"target":"../../bin/sh"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"path traversal", "Bearer cap", `{"tool":"read_file","arguments":{"path":"../../.env"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"absolute path", "Bearer cap", `{"tool":"read_file","arguments":{"path":"/etc/passwd"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"backslash path", "Bearer cap", `{"tool":"read_file","arguments":{"path":"dir\\file.py"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"sensitive path", "Bearer cap", `{"tool":"read_file","arguments":{"path":"config/.env.local"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"git metadata path", "Bearer cap", `{"tool":"read_file","arguments":{"path":".git/config"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"protected test write", "Bearer cap", `{"tool":"write_file","arguments":{"path":"tests/test_fix.py","content":"pass"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"protected workflow write", "Bearer cap", `{"tool":"write_file","arguments":{"path":".github/workflows/test.yml","content":"jobs: {}"},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"empty search query", "Bearer cap", `{"tool":"search_code","arguments":{"path":".","query":""},"timeout_ms":1000}`, http.StatusUnprocessableEntity},
		{"unknown top-level field", "Bearer cap", `{"tool":"read_file","arguments":{"path":"a.py"},"timeout_ms":1000,"extra":true}`, http.StatusBadRequest},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			request := httptest.NewRequest(http.MethodPost, "/v1/tool-calls", strings.NewReader(test.body))
			request.Header.Set("Authorization", test.authorization)
			response := httptest.NewRecorder()

			handler.ServeHTTP(response, request)

			if response.Code != test.wantStatus {
				t.Fatalf("status = %d, want %d, body = %s", response.Code, test.wantStatus, response.Body.String())
			}
		})
	}
}
