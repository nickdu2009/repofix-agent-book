"""Pydantic models at the Python service HTTP boundary."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, SecretStr

from .domain import AgentStatus


class BoundaryModel(BaseModel):
    """Reject unknown fields so Go and Python cannot silently drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AgentRunRequest(BoundaryModel):
    run_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
    task: str = Field(min_length=1, max_length=20_000)
    initial_workspace_revision: int = Field(ge=0)
    workspace_capability: SecretStr = Field(min_length=1)
    tool_gateway_url: HttpUrl
    max_steps: int = Field(default=20, ge=1, le=100)
    deadline: AwareDatetime


class AgentRunResponse(BoundaryModel):
    run_id: str
    status: AgentStatus
    summary: str
    steps: int = Field(ge=1)
    model_calls: int = Field(ge=1)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    workspace_revision: int = Field(ge=0)
    last_tested_revision: int = Field(ge=0)


class CancelAgentRunResponse(BoundaryModel):
    run_id: str
    cancel_requested: Literal[True] = True


class HealthResponse(BoundaryModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(BoundaryModel):
    status: Literal["ready"] = "ready"


class ErrorResponse(BoundaryModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    retryable: bool
    details: dict[str, Any] | None = None
