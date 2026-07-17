"""SDK-independent domain objects used by the agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from threading import Event
from typing import Any


class AgentStatus(StrEnum):
    """Internal loop status; the Go control plane owns the persisted RunStatus."""

    RUNNING = "running"
    CANDIDATE_READY = "candidate_ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ToolResult:
    """The only result shape an executor may return to the core."""

    ok: bool
    output: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    name: str
    arguments_json: str


@dataclass(frozen=True)
class AssistantText:
    text: str


ModelOutput = ToolCall | AssistantText


@dataclass(frozen=True)
class ModelResponse:
    """Normalized model output; no OpenAI SDK object crosses this boundary."""

    output: tuple[ModelOutput, ...]
    input_tokens: int = 0
    output_tokens: int = 0
    history_items: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class RunBudget:
    max_steps: int = 20
    max_model_calls: int = 20
    max_total_tokens: int = 100_000
    max_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.max_steps < 1 or self.max_model_calls < 1:
            raise ValueError("step and model-call budgets must be positive")
        if self.max_total_tokens < 1 or self.max_seconds <= 0:
            raise ValueError("token and time budgets must be positive")


@dataclass(frozen=True)
class StepRecord:
    number: int
    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    result: ToolResult
    workspace_revision: int


@dataclass
class AgentState:
    task: str
    status: AgentStatus = AgentStatus.RUNNING
    steps: list[StepRecord] = field(default_factory=list)
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    initial_workspace_revision: int = 0
    workspace_revision: int = 0
    last_tested_revision: int | None = None
    last_test_exit_code: int | None = None
    unresolved_tool_errors: list[str] = field(default_factory=list)
    failure_reason: str | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class AgentRunResult:
    summary: str
    state: AgentState


class CancellationToken:
    """Thread-safe cancellation signal owned by the control plane."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()
