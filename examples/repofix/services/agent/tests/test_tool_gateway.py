from __future__ import annotations

import json
from email.message import Message
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest

import repofix_agent.tool_gateway as tool_gateway
from repofix_agent import (
    AgentRunner,
    FakeModelClient,
    ModelResponse,
    ToolCall,
    ToolGatewayClient,
    ToolGatewayError,
)
from repofix_agent.errors import CompletionRejected

FIXTURES = Path(__file__).resolve().parents[3] / "contracts" / "fixtures"


class FakeResponse(BytesIO):
    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class FakeOpener:
    def __init__(self, response: object) -> None:
        self.response = response
        self.received: dict[str, Any] = {}

    def open(self, request: Any, *, timeout: float) -> FakeResponse:
        self.received = {
            "url": request.full_url,
            "authorization": request.get_header("Authorization"),
            "body": json.loads(request.data),
            "timeout": timeout,
        }
        if isinstance(self.response, Exception):
            raise self.response
        return FakeResponse(json.dumps(self.response).encode())


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_client_uses_shared_contract_and_tracks_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_fixture = load_fixture("tool-call.request.json")
    opener = FakeOpener(load_fixture("tool-result.response.json"))
    monkeypatch.setattr(tool_gateway, "_OPENER", opener)
    client = ToolGatewayClient(
        "http://control.internal/v1/tool-calls",
        "cap_short_lived",
        initial_workspace_revision=1,
    )

    result = client.execute("run_tests", {"target": "unit"}, timeout_seconds=2)

    assert result.ok is True
    assert result.metadata["tested_revision"] == 2
    assert client.workspace_revision == 2
    assert opener.received == {
        "url": "http://control.internal/v1/tool-calls",
        "authorization": "Bearer cap_short_lived",
        "body": request_fixture,
        "timeout": 2,
    }


def test_nonzero_initial_revision_still_requires_a_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        tool_gateway,
        "_OPENER",
        FakeOpener(load_fixture("tool-result.response.json")),
    )
    client = ToolGatewayClient(
        "http://control.internal/v1/tool-calls",
        "cap_short_lived",
        initial_workspace_revision=2,
    )
    runner = AgentRunner(
        FakeModelClient(
            [
                ModelResponse(output=(ToolCall("1", "run_tests", '{"target":"unit"}'),)),
                ModelResponse(output=(ToolCall("2", "finish", '{"summary":"no change"}'),)),
            ]
        ),
        client,
    )

    with pytest.raises(CompletionRejected, match="without a candidate"):
        runner.run("fix")


def test_client_rejects_schema_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        tool_gateway,
        "_OPENER",
        FakeOpener({"ok": True, "output": "missing required fields"}),
    )
    client = ToolGatewayClient(
        "http://control.internal/v1/tool-calls",
        "cap_short_lived",
        initial_workspace_revision=0,
    )

    with pytest.raises(ToolGatewayError, match="violates ToolCallResponse"):
        client.execute("read_file", {"path": "a.py"}, timeout_seconds=2)


def test_client_surfaces_stable_gateway_error(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "code": "tool_execution_failed",
        "message": "sandbox tool execution failed",
        "request_id": "req-test",
        "retryable": True,
    }
    http_error = HTTPError(
        "http://control.internal/v1/tool-calls",
        502,
        "Bad Gateway",
        Message(),
        FakeResponse(json.dumps(payload).encode()),
    )
    monkeypatch.setattr(tool_gateway, "_OPENER", FakeOpener(http_error))
    client = ToolGatewayClient(
        "http://control.internal/v1/tool-calls",
        "cap_short_lived",
        initial_workspace_revision=0,
    )

    with pytest.raises(ToolGatewayError) as caught:
        client.execute("read_file", {"path": "a.py"}, timeout_seconds=2)

    assert caught.value.retryable is True
    assert caught.value.upstream_code == "tool_execution_failed"


def test_client_does_not_follow_redirects() -> None:
    assert (
        tool_gateway._RejectRedirects().redirect_request(  # noqa: SLF001
            object(), object(), 302, "Found", Message(), "https://other.invalid/"
        )
        is None
    )


def test_client_rejects_invalid_configuration() -> None:
    with pytest.raises(ValueError, match="must not contain credentials"):
        ToolGatewayClient(
            "http://user:password@control.internal/v1/tool-calls",
            "cap",
            initial_workspace_revision=0,
        )
    with pytest.raises(ValueError, match="initial workspace revision"):
        ToolGatewayClient(
            "http://control.internal/v1/tool-calls",
            "cap",
            initial_workspace_revision=-1,
        )
