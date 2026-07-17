"""Run the deterministic, zero-network teaching demo."""

from .domain import ModelResponse, ToolCall
from .fake import FakeModelClient, FakeToolExecutor
from .runner import AgentRunner


def call(call_id: str, name: str, arguments_json: str) -> ModelResponse:
    return ModelResponse(output=(ToolCall(call_id, name, arguments_json),))


def main() -> None:
    model = FakeModelClient(
        [
            call("call-1", "write_file", '{"path":"calculator.py","content":"fixed"}'),
            call("call-2", "run_tests", '{"target":"unit"}'),
            call("call-3", "finish", '{"summary":"Fixed and verified calculator"}'),
        ]
    )
    result = AgentRunner(model, FakeToolExecutor()).run("Fix calculator division")
    print(f"status={result.state.status}")
    print(f"steps={len(result.state.steps)}")
    print(f"summary={result.summary}")


if __name__ == "__main__":
    main()
