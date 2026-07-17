from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import Event
from typing import Any

import httpx

from repofix_agent import (
    AgentRunner,
    CancellationToken,
    FakeModelClient,
    FakeToolExecutor,
    ModelResponse,
    RunBudget,
    ToolCall,
)
from repofix_agent.api import create_app
from repofix_agent.api_models import AgentRunRequest

RunnerBuilder = Callable[[AgentRunRequest, RunBudget, CancellationToken], AgentRunner]


class ReadyFactory:
    def __init__(self, builder: RunnerBuilder) -> None:
        self._builder = builder

    def readiness(self) -> tuple[bool, str | None]:
        return True, None

    def create_runner(
        self,
        *,
        request: AgentRunRequest,
        budget: RunBudget,
        cancellation: CancellationToken,
    ) -> AgentRunner:
        return self._builder(request, budget, cancellation)


def request_body(run_id: str = "run_01JTEST") -> dict[str, object]:
    deadline = datetime.now(UTC) + timedelta(minutes=5)
    return {
        "run_id": run_id,
        "task": "Fix calculator division and run tests",
        "workspace_capability": "cap_short_lived",
        "tool_gateway_url": "http://control.internal/v1/tool-calls",
        "max_steps": 3,
        "deadline": deadline.isoformat(),
    }


async def api_request(
    app: Any,
    method: str,
    path: str,
    **kwargs: Any,
) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def successful_runner(
    _request: AgentRunRequest,
    budget: RunBudget,
    cancellation: CancellationToken,
) -> AgentRunner:
    model = FakeModelClient(
        [
            ModelResponse(
                output=(
                    ToolCall(
                        "call-1",
                        "write_file",
                        '{"path":"calculator.py","content":"fixed"}',
                    ),
                ),
                input_tokens=10,
                output_tokens=5,
            ),
            ModelResponse(
                output=(ToolCall("call-2", "run_tests", '{"target":"unit"}'),),
                input_tokens=8,
                output_tokens=4,
            ),
            ModelResponse(
                output=(ToolCall("call-3", "finish", '{"summary":"fixed division"}'),),
                input_tokens=6,
                output_tokens=3,
            ),
        ]
    )
    return AgentRunner(
        model,
        FakeToolExecutor(files={"calculator.py": "buggy"}),
        budget=budget,
        cancellation=cancellation,
    )


def test_health_is_live_while_unconfigured_service_is_not_ready() -> None:
    app = create_app()

    async def exercise() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        health = await api_request(app, "GET", "/healthz")
        readiness = await api_request(app, "GET", "/readyz")
        missing = await api_request(app, "GET", "/missing")
        return health, readiness, missing

    health, readiness, missing = asyncio.run(exercise())

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert readiness.status_code == 503
    assert readiness.json()["code"] == "not_ready"
    assert readiness.json()["retryable"] is True
    assert "detail" not in readiness.json()
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"
    assert "detail" not in missing.json()


def test_ready_service_runs_one_complete_fake_loop() -> None:
    app = create_app(runner_factory=ReadyFactory(successful_runner))

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        readiness = await api_request(app, "GET", "/readyz")
        response = await api_request(app, "POST", "/v1/agent-runs", json=request_body())
        return readiness, response

    readiness, response = asyncio.run(exercise())

    assert readiness.json() == {"status": "ready"}
    assert response.status_code == 200
    assert response.json() == {
        "run_id": "run_01JTEST",
        "status": "candidate_ready",
        "summary": "fixed division",
        "steps": 3,
        "model_calls": 3,
        "input_tokens": 24,
        "output_tokens": 12,
        "workspace_revision": 1,
        "last_tested_revision": 1,
    }


def test_duplicate_run_id_is_rejected_without_starting_a_second_loop() -> None:
    app = create_app(runner_factory=ReadyFactory(successful_runner))

    async def exercise() -> tuple[httpx.Response, httpx.Response]:
        first = await api_request(app, "POST", "/v1/agent-runs", json=request_body())
        duplicate = await api_request(app, "POST", "/v1/agent-runs", json=request_body())
        return first, duplicate

    first, duplicate = asyncio.run(exercise())

    assert first.status_code == 200
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "run_already_exists"
    assert "detail" not in duplicate.json()


def test_validation_error_uses_top_level_error_contract() -> None:
    app = create_app(runner_factory=ReadyFactory(successful_runner))
    response = asyncio.run(
        api_request(
            app,
            "POST",
            "/v1/agent-runs",
            json={},
            headers={"x-request-id": "req-contract-test"},
        )
    )

    assert response.status_code == 422
    assert response.headers["x-request-id"] == "req-contract-test"
    body = response.json()
    assert set(body) == {"code", "message", "request_id", "retryable", "details"}
    assert body["code"] == "invalid_request"
    assert body["request_id"] == "req-contract-test"
    assert body["retryable"] is False
    assert "detail" not in body


class BlockingFakeModelClient:
    is_live = False

    def __init__(self) -> None:
        self.entered = Event()
        self.release = Event()

    def create_response(
        self,
        *,
        instructions: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> ModelResponse:
        del instructions, history, tools, timeout_seconds
        self.entered.set()
        if not self.release.wait(timeout=5):
            raise TimeoutError("test did not release blocking fake")
        return ModelResponse(output=(ToolCall("call-1", "read_file", '{"path":"a.py"}'),))


def test_cancel_endpoint_remains_responsive_during_sync_model_call() -> None:
    model = BlockingFakeModelClient()

    def blocking_runner(
        _request: AgentRunRequest,
        budget: RunBudget,
        cancellation: CancellationToken,
    ) -> AgentRunner:
        return AgentRunner(
            model,
            FakeToolExecutor(files={"a.py": "content"}),
            budget=budget,
            cancellation=cancellation,
        )

    app = create_app(runner_factory=ReadyFactory(blocking_runner))

    async def exercise() -> tuple[httpx.Response, httpx.Response, httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            run_request = asyncio.create_task(
                client.post("/v1/agent-runs", json=request_body("run_cancel"))
            )
            try:
                entered = await asyncio.wait_for(asyncio.to_thread(model.entered.wait, 2), 3)
                assert entered
                cancel = await asyncio.wait_for(
                    client.post("/v1/agent-runs/run_cancel/cancel"),
                    2,
                )
            finally:
                model.release.set()
            run = await asyncio.wait_for(run_request, 3)
            second_cancel = await client.post("/v1/agent-runs/run_cancel/cancel")
        return cancel, run, second_cancel

    cancel_response, run_response, second_cancel_response = asyncio.run(exercise())

    assert cancel_response.status_code == 202
    assert cancel_response.json() == {
        "run_id": "run_cancel",
        "cancel_requested": True,
    }
    assert run_response.status_code == 409
    assert run_response.json()["code"] == "cancelled"
    assert "detail" not in run_response.json()
    assert second_cancel_response.status_code == 404
    assert second_cancel_response.json()["code"] == "run_not_active"
