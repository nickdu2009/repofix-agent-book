"""Ports implemented by model and sandbox adapters."""

from __future__ import annotations

from typing import Any, Protocol

from .domain import ModelResponse, ToolResult


class ModelClient(Protocol):
    @property
    def is_live(self) -> bool:
        """True when calls leave the process and reach a real model."""
        ...

    def create_response(
        self,
        *,
        instructions: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> ModelResponse: ...


class ToolExecutor(Protocol):
    @property
    def is_sandboxed(self) -> bool: ...

    @property
    def workspace_revision(self) -> int: ...

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> ToolResult: ...


class SandboxExecutor(ToolExecutor, Protocol):
    """Port for a future Daytona adapter.

    Implementations MUST return ``is_sandboxed == True`` and keep all repository
    reads, writes, and test processes inside one isolated sandbox.
    """
