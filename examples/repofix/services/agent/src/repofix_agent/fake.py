"""Deterministic test doubles. They never call a network or subprocess."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any

from .domain import ModelResponse, ToolResult


class FakeModelClient:
    is_live = False

    def __init__(self, responses: Iterable[ModelResponse]) -> None:
        self._responses = deque(responses)
        self.requests: list[dict[str, Any]] = []

    def create_response(
        self,
        *,
        instructions: str,
        history: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        timeout_seconds: float,
    ) -> ModelResponse:
        self.requests.append(
            {
                "instructions": instructions,
                "history": list(history),
                "tools": tools,
                "timeout_seconds": timeout_seconds,
            }
        )
        if not self._responses:
            raise AssertionError("FakeModelClient has no scripted response left")
        return self._responses.popleft()


class FakeToolExecutor:
    """In-memory executor for AgentRunner tests and the local demo.

    It intentionally reports ``is_sandboxed = False``. AgentRunner therefore refuses
    to pair it with OpenAIModelClient or any other live model.
    """

    is_sandboxed = False

    def __init__(
        self,
        *,
        files: dict[str, str] | None = None,
        test_exit_codes: Iterable[int] = (0,),
        protected_prefixes: tuple[str, ...] = ("tests/", ".github/"),
    ) -> None:
        self.files = dict(files or {})
        self._test_exit_codes = deque(test_exit_codes)
        self._protected_prefixes = protected_prefixes
        self._workspace_revision = 0
        self.calls: list[tuple[str, dict[str, Any]]] = []

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
            raise TimeoutError("fake executor received an expired deadline")
        self.calls.append((name, dict(arguments)))

        if name == "list_files":
            prefix = arguments["path"].strip("./")
            paths = sorted(
                path for path in self.files if not prefix or path.startswith(f"{prefix}/")
            )
            return ToolResult(ok=True, output="\n".join(paths))

        if name == "read_file":
            path = arguments["path"]
            if path not in self.files:
                return ToolResult(ok=False, output="", error=f"file not found: {path}")
            return ToolResult(ok=True, output=self.files[path])

        if name == "search_code":
            query = arguments["query"]
            prefix = arguments["path"].strip("./")
            matches = [
                f"{path}:{line_number}:{line}"
                for path, content in sorted(self.files.items())
                if not prefix or path.startswith(f"{prefix}/")
                for line_number, line in enumerate(content.splitlines(), start=1)
                if query in line
            ]
            return ToolResult(ok=True, output="\n".join(matches))

        if name == "write_file":
            path = arguments["path"]
            if path.startswith(self._protected_prefixes):
                return ToolResult(ok=False, output="", error=f"protected path: {path}")
            self.files[path] = arguments["content"]
            self._workspace_revision += 1
            return ToolResult(
                ok=True,
                output=f"wrote {path}",
                metadata={
                    "workspace_changed": True,
                    "workspace_revision": self._workspace_revision,
                },
            )

        if name == "run_tests":
            if not self._test_exit_codes:
                raise AssertionError("FakeToolExecutor has no scripted test result left")
            exit_code = self._test_exit_codes.popleft()
            output = "1 passed" if exit_code == 0 else "1 failed"
            return ToolResult(
                ok=True,
                output=output,
                metadata={
                    "exit_code": exit_code,
                    "tested_revision": self._workspace_revision,
                    "target": arguments["target"],
                },
            )

        return ToolResult(ok=False, output="", error=f"unsupported fake tool: {name}")
