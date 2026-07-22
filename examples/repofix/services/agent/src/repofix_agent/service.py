"""Async service orchestration around the synchronous AgentRunner."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from .api_models import AgentRunRequest, AgentRunResponse, CancelAgentRunResponse
from .config import ServiceConfig
from .domain import AgentStatus, CancellationToken, RunBudget
from .errors import (
    AgentError,
    BudgetExceeded,
    RunCancelled,
    ToolGatewayError,
    UnsafeExecutionError,
)
from .runner import AgentRunner


class AgentServiceError(RuntimeError):
    """Stable error information converted to ErrorResponse by the API layer."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details


class RunnerFactory(Protocol):
    """Injection boundary for live adapters and deterministic test doubles."""

    def readiness(self) -> tuple[bool, str | None]: ...

    def create_runner(
        self,
        *,
        request: AgentRunRequest,
        budget: RunBudget,
        cancellation: CancellationToken,
    ) -> AgentRunner: ...


class UnavailableRunnerFactory:
    """Fail-closed default: importing the API never creates a live client."""

    def readiness(self) -> tuple[bool, str | None]:
        return False, "runner factory is not configured"

    def create_runner(
        self,
        *,
        request: AgentRunRequest,
        budget: RunBudget,
        cancellation: CancellationToken,
    ) -> AgentRunner:
        del request, budget, cancellation
        raise RuntimeError("runner factory is not configured")


class AgentService:
    """Own in-process loop coordination, while Go owns persisted Run state."""

    def __init__(
        self,
        runner_factory: RunnerFactory,
        *,
        config: ServiceConfig | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._runner_factory = runner_factory
        self._config = config or ServiceConfig()
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = asyncio.Lock()
        self._active: dict[str, CancellationToken] = {}
        self._seen_run_ids: set[str] = set()

    def readiness(self) -> tuple[bool, str | None]:
        return self._runner_factory.readiness()

    async def run(self, request: AgentRunRequest) -> AgentRunResponse:
        ready, reason = self.readiness()
        if not ready:
            raise AgentServiceError(
                503,
                "not_ready",
                "agent service is not ready",
                retryable=True,
                details={"reason": reason or "dependency unavailable"},
            )

        budget = self._budget_for(request)
        cancellation = CancellationToken()
        async with self._lock:
            if request.run_id in self._seen_run_ids:
                raise AgentServiceError(
                    409,
                    "run_already_exists",
                    "run_id has already been accepted",
                )
            self._seen_run_ids.add(request.run_id)
            self._active[request.run_id] = cancellation

        try:

            def run_in_worker():
                runner = self._runner_factory.create_runner(
                    request=request,
                    budget=budget,
                    cancellation=cancellation,
                )
                return runner.run(request.task)

            # Runner construction, the loop, and its adapters are synchronous. Keep
            # all of them out of the event loop so cancellation remains responsive.
            result = await asyncio.to_thread(run_in_worker)
            if cancellation.is_cancelled:
                raise RunCancelled("run cancelled after the final runner check")
        except RunCancelled as error:
            raise AgentServiceError(409, "cancelled", "agent run was cancelled") from error
        except BudgetExceeded as error:
            if "duration" in str(error):
                raise AgentServiceError(
                    504,
                    "deadline_exceeded",
                    "agent run exceeded its deadline",
                ) from error
            raise AgentServiceError(422, "budget_exceeded", str(error)) from error
        except UnsafeExecutionError as error:
            raise AgentServiceError(
                500,
                "unsafe_execution",
                "agent safety invariant rejected the runner configuration",
            ) from error
        except ToolGatewayError as error:
            details = (
                {"upstream_code": error.upstream_code} if error.upstream_code is not None else None
            )
            raise AgentServiceError(
                503 if error.retryable else 502,
                "tool_gateway_failed",
                "tool gateway request failed",
                retryable=error.retryable,
                details=details,
            ) from error
        except AgentError as error:
            raise AgentServiceError(422, "agent_failed", str(error)) from error
        finally:
            async with self._lock:
                self._active.pop(request.run_id, None)

        state = result.state
        if state.status is not AgentStatus.CANDIDATE_READY:
            raise AgentServiceError(
                500,
                "invalid_agent_result",
                "agent returned without a verified candidate",
            )
        if state.last_tested_revision is None:
            raise AgentServiceError(
                500,
                "invalid_agent_result",
                "agent candidate has no tested workspace revision",
            )

        return AgentRunResponse(
            run_id=request.run_id,
            status=state.status,
            summary=result.summary,
            steps=len(state.steps),
            model_calls=state.model_calls,
            input_tokens=state.input_tokens,
            output_tokens=state.output_tokens,
            workspace_revision=state.workspace_revision,
            last_tested_revision=state.last_tested_revision,
        )

    async def cancel(self, run_id: str) -> CancelAgentRunResponse:
        async with self._lock:
            cancellation = self._active.get(run_id)
            if cancellation is None:
                raise AgentServiceError(
                    404,
                    "run_not_active",
                    "run_id is not active in this agent process",
                )
            cancellation.cancel()
        return CancelAgentRunResponse(run_id=run_id)

    def _budget_for(self, request: AgentRunRequest) -> RunBudget:
        remaining_seconds = (request.deadline - self._now()).total_seconds()
        if remaining_seconds <= 0:
            raise AgentServiceError(
                504,
                "deadline_exceeded",
                "agent run deadline has already passed",
            )
        return RunBudget(
            max_steps=request.max_steps,
            max_model_calls=request.max_steps,
            max_total_tokens=self._config.max_total_tokens,
            max_seconds=min(remaining_seconds, self._config.max_run_seconds),
        )
