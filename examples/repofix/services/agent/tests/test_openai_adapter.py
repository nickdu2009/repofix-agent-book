from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from repofix_agent import ToolCall
from repofix_agent.openai_adapter import OpenAIModelClient


@dataclass
class FakeUsage:
    input_tokens: int = 12
    output_tokens: int = 4


class FakeFunctionCall:
    type = "function_call"
    call_id = "call-1"
    name = "read_file"
    arguments = '{"path":"calculator.py"}'

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {
            "type": self.type,
            "call_id": self.call_id,
            "name": self.name,
            "arguments": self.arguments,
        }


class FakeReasoning:
    type = "reasoning"

    def model_dump(self, *, mode: str) -> dict[str, Any]:
        assert mode == "json"
        return {"type": self.type, "id": "reasoning-1", "summary": []}


class FakeResponse:
    status = "completed"
    error = None
    incomplete_details = None
    output = [FakeReasoning(), FakeFunctionCall()]
    output_text = ""
    usage = FakeUsage()


class FakeResponsesAPI:
    def __init__(self, result: object) -> None:
        self._result = result
        self.kwargs: dict[str, Any] = {}

    def create(self, **kwargs: Any) -> object:
        self.kwargs = kwargs
        return self._result


class FakeSDKClient:
    def __init__(self, result: object) -> None:
        self.responses = FakeResponsesAPI(result)
        self.options: dict[str, Any] = {}

    def with_options(self, **kwargs: Any) -> FakeSDKClient:
        self.options = kwargs
        return self


def test_adapter_normalizes_sdk_output_and_disables_parallel_tools() -> None:
    sdk = FakeSDKClient(FakeResponse())
    client = OpenAIModelClient(model="test-model", client=sdk)

    result = client.create_response(
        instructions="repair",
        history=[],
        tools=[],
        timeout_seconds=12.5,
    )

    assert result.input_tokens == 12
    assert result.output_tokens == 4
    assert isinstance(result.output[0], ToolCall)
    assert sdk.responses.kwargs["parallel_tool_calls"] is False
    assert sdk.responses.kwargs["max_output_tokens"] == 4_096
    assert sdk.responses.kwargs["store"] is False
    assert sdk.options == {"timeout": 12.5, "max_retries": 0}
    assert result.history_items[0]["type"] == "reasoning"
    assert result.history_items[1]["type"] == "function_call"


def test_adapter_rejects_non_positive_output_budget() -> None:
    with pytest.raises(ValueError, match="positive"):
        OpenAIModelClient(max_output_tokens=0, client=FakeSDKClient(FakeResponse()))


def test_adapter_rejects_incomplete_response() -> None:
    class IncompleteResponse(FakeResponse):
        status = "incomplete"
        incomplete_details = {"reason": "max_output_tokens"}

    client = OpenAIModelClient(client=FakeSDKClient(IncompleteResponse()))

    with pytest.raises(RuntimeError, match="incomplete"):
        client.create_response(
            instructions="repair",
            history=[],
            tools=[],
            timeout_seconds=1,
        )
