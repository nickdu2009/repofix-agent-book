"""HTTP adapter for the Go-owned sandbox Tool Gateway."""

from __future__ import annotations

import json
import math
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .domain import ToolResult
from .errors import ToolGatewayError

_MAX_RESPONSE_BYTES = 1_048_576


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        return None


_OPENER = build_opener(_RejectRedirects())


class ToolGatewayClient:
    """Execute semantic tools through Go without exposing sandbox credentials."""

    is_sandboxed = True

    def __init__(
        self,
        endpoint: str,
        capability: str,
        initial_workspace_revision: int,
    ) -> None:
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("tool gateway endpoint must be an absolute HTTP URL")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("tool gateway endpoint must not contain credentials")
        if not capability:
            raise ValueError("workspace capability must not be empty")
        if (
            isinstance(initial_workspace_revision, bool)
            or not isinstance(initial_workspace_revision, int)
            or initial_workspace_revision < 0
        ):
            raise ValueError("initial workspace revision must be a non-negative integer")
        self._endpoint = endpoint
        self._capability = capability
        self._workspace_revision = initial_workspace_revision

    @property
    def workspace_revision(self) -> int:
        return self._workspace_revision

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        timeout_seconds: float,
    ) -> ToolResult:
        if timeout_seconds <= 0:
            raise TimeoutError("tool gateway deadline has expired")

        timeout_ms = min(300_000, max(1, math.ceil(timeout_seconds * 1000)))
        request = Request(
            self._endpoint,
            data=json.dumps(
                {"tool": name, "arguments": arguments, "timeout_ms": timeout_ms},
                ensure_ascii=False,
            ).encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._capability}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with _OPENER.open(request, timeout=timeout_seconds) as response:
                payload = self._read_json(response)
        except HTTPError as error:
            raise self._http_error(error) from error
        except (TimeoutError, URLError, OSError) as error:
            raise ToolGatewayError("tool gateway is unavailable", retryable=True) from error

        return self._tool_result(payload)

    @staticmethod
    def _read_json(response: Any) -> object:
        raw = response.read(_MAX_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_RESPONSE_BYTES:
            raise ToolGatewayError(
                "tool gateway response exceeds 1 MiB",
                retryable=False,
                upstream_code="invalid_tool_result",
            )
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ToolGatewayError(
                "tool gateway returned invalid JSON",
                retryable=False,
                upstream_code="invalid_tool_result",
            ) from error

    @classmethod
    def _http_error(cls, error: HTTPError) -> ToolGatewayError:
        try:
            payload = cls._read_json(error)
            if isinstance(payload, dict):
                code = payload.get("code")
                retryable = payload.get("retryable")
                if isinstance(code, str) and isinstance(retryable, bool):
                    return ToolGatewayError(
                        "tool gateway rejected the request",
                        retryable=retryable,
                        upstream_code=code,
                    )
        except ToolGatewayError:
            pass
        return ToolGatewayError(
            f"tool gateway returned HTTP {error.code}",
            retryable=error.code >= 500,
        )

    def _tool_result(self, payload: object) -> ToolResult:
        if not isinstance(payload, dict) or set(payload) != {
            "ok",
            "output",
            "error",
            "metadata",
            "workspace_revision",
        }:
            raise ToolGatewayError(
                "tool gateway response violates ToolCallResponse",
                retryable=False,
                upstream_code="invalid_tool_result",
            )

        ok = payload["ok"]
        output = payload["output"]
        error = payload["error"]
        metadata = payload["metadata"]
        revision = payload["workspace_revision"]
        if not isinstance(ok, bool) or not isinstance(output, str):
            raise ToolGatewayError(
                "tool gateway response has invalid result fields",
                retryable=False,
                upstream_code="invalid_tool_result",
            )
        if error is not None and not isinstance(error, str):
            raise ToolGatewayError(
                "tool gateway response has invalid error field",
                retryable=False,
                upstream_code="invalid_tool_result",
            )
        if (ok and error is not None) or (not ok and not error):
            raise ToolGatewayError(
                "tool gateway response has inconsistent result fields",
                retryable=False,
                upstream_code="invalid_tool_result",
            )
        if not isinstance(metadata, dict) or not all(isinstance(key, str) for key in metadata):
            raise ToolGatewayError(
                "tool gateway response has invalid metadata",
                retryable=False,
                upstream_code="invalid_tool_result",
            )
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 0:
            raise ToolGatewayError(
                "tool gateway response has invalid workspace revision",
                retryable=False,
                upstream_code="invalid_tool_result",
            )

        self._workspace_revision = revision
        return ToolResult(ok=ok, output=output, error=error, metadata=metadata)
