// Package toolgateway exposes the narrow HTTP boundary used by the Python Agent.
package toolgateway

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"path"
	"strings"
	"time"
)

const maxRequestBytes = 64 << 10

var toolArguments = map[string][]string{
	"list_files":  {"path"},
	"read_file":   {"path"},
	"search_code": {"path", "query"},
	"write_file":  {"content", "path"},
	"run_tests":   {"target"},
}

type Request struct {
	Tool      string            `json:"tool"`
	Arguments map[string]string `json:"arguments"`
	TimeoutMS int               `json:"timeout_ms"`
}

type Result struct {
	OK                bool           `json:"ok"`
	Output            string         `json:"output"`
	Error             *string        `json:"error"`
	Metadata          map[string]any `json:"metadata"`
	WorkspaceRevision int64          `json:"workspace_revision"`
}

type ResolveCapabilityFunc func(context.Context, string) (string, error)

type ExecuteFunc func(context.Context, string, string, map[string]string) (Result, error)

type Handler struct {
	resolve ResolveCapabilityFunc
	execute ExecuteFunc
}

func NewHandler(resolve ResolveCapabilityFunc, execute ExecuteFunc) *Handler {
	return &Handler{resolve: resolve, execute: execute}
}

func (h *Handler) ServeHTTP(response http.ResponseWriter, request *http.Request) {
	requestID := request.Header.Get("X-Request-ID")
	if requestID == "" {
		requestID = fmt.Sprintf("req_%x", time.Now().UnixNano())
	}
	response.Header().Set("X-Request-ID", requestID)

	if request.Method != http.MethodPost {
		response.Header().Set("Allow", http.MethodPost)
		h.writeError(response, requestID, http.StatusMethodNotAllowed, "method_not_allowed", "method must be POST", false)
		return
	}
	if h.resolve == nil || h.execute == nil {
		h.writeError(response, requestID, http.StatusServiceUnavailable, "not_ready", "tool gateway is not configured", true)
		return
	}

	capability, ok := strings.CutPrefix(request.Header.Get("Authorization"), "Bearer ")
	if !ok || strings.TrimSpace(capability) == "" || strings.ContainsAny(capability, " \t\r\n") {
		h.writeError(response, requestID, http.StatusUnauthorized, "invalid_capability", "missing or invalid workspace capability", false)
		return
	}

	var call Request
	decoder := json.NewDecoder(http.MaxBytesReader(response, request.Body, maxRequestBytes))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&call); err != nil {
		h.writeError(response, requestID, http.StatusBadRequest, "invalid_request", "request body must match ToolCallRequest", false)
		return
	}
	if err := decoder.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		h.writeError(response, requestID, http.StatusBadRequest, "invalid_request", "request body must contain one JSON object", false)
		return
	}
	if err := validate(call); err != nil {
		h.writeError(response, requestID, http.StatusUnprocessableEntity, "invalid_tool_call", err.Error(), false)
		return
	}

	sandboxID, err := h.resolve(request.Context(), capability)
	if err != nil || sandboxID == "" {
		h.writeError(response, requestID, http.StatusUnauthorized, "invalid_capability", "workspace capability is invalid or expired", false)
		return
	}

	toolContext, cancel := context.WithTimeout(request.Context(), time.Duration(call.TimeoutMS)*time.Millisecond)
	defer cancel()
	result, err := h.execute(toolContext, sandboxID, call.Tool, call.Arguments)
	if err != nil {
		h.writeError(response, requestID, http.StatusBadGateway, "tool_execution_failed", "sandbox tool execution failed", true)
		return
	}
	if result.WorkspaceRevision < 0 {
		h.writeError(response, requestID, http.StatusBadGateway, "invalid_tool_result", "sandbox returned an invalid workspace revision", false)
		return
	}
	if (result.OK && result.Error != nil) || (!result.OK && result.Error == nil) {
		h.writeError(response, requestID, http.StatusBadGateway, "invalid_tool_result", "sandbox returned inconsistent result fields", false)
		return
	}
	if result.Metadata == nil {
		result.Metadata = map[string]any{}
	}
	if _, err := json.Marshal(result.Metadata); err != nil {
		h.writeError(response, requestID, http.StatusBadGateway, "invalid_tool_result", "sandbox returned invalid result metadata", false)
		return
	}
	h.writeJSON(response, http.StatusOK, result)
}

func validate(call Request) error {
	expected, ok := toolArguments[call.Tool]
	if !ok {
		return fmt.Errorf("unsupported tool: %s", call.Tool)
	}
	if call.TimeoutMS < 1 || call.TimeoutMS > 300_000 {
		return errors.New("timeout_ms must be between 1 and 300000")
	}
	if len(call.Arguments) != len(expected) {
		return fmt.Errorf("invalid arguments for %s", call.Tool)
	}
	for _, name := range expected {
		if _, ok := call.Arguments[name]; !ok {
			return fmt.Errorf("invalid arguments for %s", call.Tool)
		}
	}
	if pathValue, ok := call.Arguments["path"]; ok {
		if err := validateWorkspacePath(pathValue, call.Tool == "write_file"); err != nil {
			return err
		}
	}
	if call.Tool == "run_tests" && call.Arguments["target"] != "unit" {
		return errors.New("unsupported test target")
	}
	if call.Tool == "search_code" && call.Arguments["query"] == "" {
		return errors.New("search query must not be empty")
	}
	return nil
}

func validateWorkspacePath(value string, write bool) error {
	if value == "" || path.IsAbs(value) || strings.Contains(value, "\\") || strings.ContainsRune(value, '\x00') {
		return errors.New("path must be workspace-relative")
	}
	parts := strings.Split(value, "/")
	for _, part := range parts {
		if part == ".." {
			return errors.New("path must not escape the workspace")
		}
		if part == ".git" || part == ".env" || strings.HasPrefix(part, ".env.") ||
			part == ".ssh" || part == ".aws" {
			return errors.New("sensitive paths are not accessible")
		}
	}
	cleaned := path.Clean(value)
	if write && (cleaned == "tests" || strings.HasPrefix(cleaned, "tests/") ||
		cleaned == ".github" || strings.HasPrefix(cleaned, ".github/")) {
		return errors.New("protected paths are read-only")
	}
	return nil
}

func (h *Handler) writeError(
	response http.ResponseWriter,
	requestID string,
	status int,
	code string,
	message string,
	retryable bool,
) {
	h.writeJSON(response, status, map[string]any{
		"code":       code,
		"message":    message,
		"request_id": requestID,
		"retryable":  retryable,
	})
}

func (*Handler) writeJSON(response http.ResponseWriter, status int, payload any) {
	response.Header().Set("Content-Type", "application/json")
	response.WriteHeader(status)
	_ = json.NewEncoder(response).Encode(payload)
}
