"""Optional OpenAI Responses API adapter.

Install with ``pip install -e '.[live]'``. The core package imports no SDK types.
"""

from __future__ import annotations

import os
from typing import Any

from .domain import AssistantText, ModelResponse, ToolCall


class OpenAIModelClient:
    is_live = True

    def __init__(
        self,
        *,
        model: str | None = None,
        max_output_tokens: int = 4_096,
        client: Any | None = None,
    ) -> None:
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as error:
                raise RuntimeError("install the 'live' extra to use OpenAIModelClient") from error
            client = OpenAI()
        self._client = client
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
        self._max_output_tokens = max_output_tokens

    def create_response(
        self,
        *,
        instructions: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> ModelResponse:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        request_client = self._client.with_options(
            timeout=timeout_seconds,
            max_retries=0,
        )
        response = request_client.responses.create(
            model=self._model,
            instructions=instructions,
            input=history,
            tools=tools,
            parallel_tool_calls=False,
            max_output_tokens=self._max_output_tokens,
            store=False,
        )

        status = getattr(response, "status", None)
        error = getattr(response, "error", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        if error is not None or status == "failed":
            raise RuntimeError(f"OpenAI response failed: {error!s}")
        if status == "incomplete":
            raise RuntimeError(f"OpenAI response incomplete: {incomplete_details!s}")
        if status not in (None, "completed"):
            raise RuntimeError(f"unexpected OpenAI response status: {status}")

        normalized: list[ToolCall | AssistantText] = []
        history_items: list[dict[str, Any]] = []
        for item in response.output:
            item_type = getattr(item, "type", "")
            if item_type == "function_call":
                normalized.append(
                    ToolCall(
                        call_id=item.call_id,
                        name=item.name,
                        arguments_json=item.arguments,
                    )
                )
            serialized = self._serialize_item(item)
            if serialized is not None:
                history_items.append(serialized)

        if response.output_text:
            normalized.append(AssistantText(response.output_text))

        usage = getattr(response, "usage", None)
        return ModelResponse(
            output=tuple(normalized),
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            history_items=tuple(history_items),
        )

    @staticmethod
    def _serialize_item(item: Any) -> dict[str, Any] | None:
        if hasattr(item, "model_dump"):
            value = item.model_dump(mode="json")
            return value if isinstance(value, dict) else None
        if hasattr(item, "to_dict"):
            value = item.to_dict()
            return value if isinstance(value, dict) else None
        return None
