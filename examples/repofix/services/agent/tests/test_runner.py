from __future__ import annotations

import json

import pytest

from repofix_agent import (
    AgentRunner,
    AgentStatus,
    AssistantText,
    CancellationToken,
    FakeModelClient,
    FakeToolExecutor,
    ModelResponse,
    RunBudget,
    ToolCall,
    ToolResult,
)
from repofix_agent.errors import (
    BudgetExceeded,
    CompletionRejected,
    ModelProtocolError,
    RunCancelled,
    UnsafeExecutionError,
)


def response(call_id: str, name: str, **arguments: str) -> ModelResponse:
    return ModelResponse(
        output=(ToolCall(call_id, name, json.dumps(arguments)),),
        input_tokens=10,
        output_tokens=5,
    )


def test_success_requires_write_current_tests_and_finish() -> None:
    model = FakeModelClient(
        [
            response("1", "write_file", path="calculator.py", content="fixed"),
            response("2", "run_tests", target="unit"),
            response("3", "finish", summary="fixed division"),
        ]
    )
    executor = FakeToolExecutor(files={"calculator.py": "buggy"})

    result = AgentRunner(model, executor).run("fix division")

    assert result.summary == "fixed division"
    assert result.state.status is AgentStatus.CANDIDATE_READY
    assert result.state.workspace_revision == 1
    assert result.state.last_tested_revision == 1
    assert result.state.last_test_exit_code == 0
    assert [step.tool_name for step in result.state.steps] == [
        "write_file",
        "run_tests",
        "finish",
    ]
    assert model.requests[1]["history"][-1]["call_id"] == "1"


def test_plain_text_cannot_complete_run() -> None:
    runner = AgentRunner(
        FakeModelClient([ModelResponse(output=(AssistantText("done"),))]),
        FakeToolExecutor(),
    )

    with pytest.raises(ModelProtocolError, match="plain text"):
        runner.run("pretend to fix")

    assert runner.state is not None
    assert runner.state.status is AgentStatus.FAILED


def test_finish_before_tests_is_rejected() -> None:
    runner = AgentRunner(
        FakeModelClient([response("1", "finish", summary="trust me")]),
        FakeToolExecutor(),
    )

    with pytest.raises(CompletionRejected, match="before tests pass"):
        runner.run("fix")


def test_passing_tests_without_a_candidate_change_cannot_finish() -> None:
    runner = AgentRunner(
        FakeModelClient(
            [
                response("1", "run_tests", target="unit"),
                response("2", "finish", summary="no patch needed"),
            ]
        ),
        FakeToolExecutor(),
    )

    with pytest.raises(CompletionRejected, match="without a candidate"):
        runner.run("fix")


def test_change_after_passing_tests_invalidates_completion() -> None:
    runner = AgentRunner(
        FakeModelClient(
            [
                response("1", "run_tests", target="unit"),
                response("2", "write_file", path="calculator.py", content="changed later"),
                response("3", "finish", summary="not actually verified"),
            ]
        ),
        FakeToolExecutor(),
    )

    with pytest.raises(CompletionRejected, match="changed after"):
        runner.run("fix")

    assert runner.state is not None
    assert runner.state.last_tested_revision == 0
    assert runner.state.workspace_revision == 1


def test_maximum_steps_stops_before_an_extra_model_call() -> None:
    model = FakeModelClient(
        [
            response("1", "read_file", path="calculator.py"),
            response("2", "read_file", path="calculator.py"),
            response("3", "finish", summary="should never be requested"),
        ]
    )
    runner = AgentRunner(
        model,
        FakeToolExecutor(files={"calculator.py": "bug"}),
        budget=RunBudget(max_steps=2),
    )

    with pytest.raises(BudgetExceeded, match="steps"):
        runner.run("fix")

    assert len(model.requests) == 2


def test_maximum_model_calls_stops_before_a_second_request() -> None:
    model = FakeModelClient(
        [
            response("1", "read_file", path="calculator.py"),
            response("2", "read_file", path="calculator.py"),
        ]
    )
    runner = AgentRunner(
        model,
        FakeToolExecutor(files={"calculator.py": "bug"}),
        budget=RunBudget(max_model_calls=1),
    )

    with pytest.raises(BudgetExceeded, match="model calls"):
        runner.run("fix")

    assert len(model.requests) == 1


def test_time_budget_is_checked_and_passed_to_adapters() -> None:
    model = FakeModelClient(
        [response("1", "write_file", path="calculator.py", content="fixed")]
    )
    runner = AgentRunner(
        model,
        FakeToolExecutor(),
        budget=RunBudget(max_seconds=7.5, max_steps=1),
        clock=lambda: 0.0,
    )

    with pytest.raises(BudgetExceeded, match="steps"):
        runner.run("fix")

    assert model.requests[0]["timeout_seconds"] == 7.5


def test_cancelled_run_does_not_call_model() -> None:
    cancellation = CancellationToken()
    cancellation.cancel()
    model = FakeModelClient([response("1", "finish", summary="never")])
    runner = AgentRunner(model, FakeToolExecutor(), cancellation=cancellation)

    with pytest.raises(RunCancelled):
        runner.run("fix")

    assert not model.requests
    assert runner.state is not None
    assert runner.state.status is AgentStatus.CANCELLED


def test_token_budget_is_program_owned() -> None:
    expensive_response = ModelResponse(
        output=(ToolCall("1", "run_tests", '{"target":"unit"}'),),
        input_tokens=80,
        output_tokens=30,
    )
    runner = AgentRunner(
        FakeModelClient([expensive_response]),
        FakeToolExecutor(),
        budget=RunBudget(max_total_tokens=100),
    )

    with pytest.raises(BudgetExceeded, match="token"):
        runner.run("fix")


def test_malformed_or_extra_arguments_are_protocol_errors() -> None:
    model = FakeModelClient(
        [
            ModelResponse(
                output=(
                    ToolCall(
                        "1",
                        "read_file",
                        '{"path":"calculator.py","unexpected":"value"}',
                    ),
                )
            )
        ]
    )

    with pytest.raises(ModelProtocolError, match="extra"):
        AgentRunner(model, FakeToolExecutor()).run("fix")


def test_multiple_tool_calls_are_rejected_even_without_finish() -> None:
    model = FakeModelClient(
        [
            ModelResponse(
                output=(
                    ToolCall("1", "read_file", '{"path":"a.py"}'),
                    ToolCall("2", "read_file", '{"path":"b.py"}'),
                )
            )
        ]
    )

    with pytest.raises(ModelProtocolError, match="exactly one"):
        AgentRunner(model, FakeToolExecutor()).run("fix")


def test_tool_error_remains_unresolved_for_the_whole_mvp_run() -> None:
    runner = AgentRunner(
        FakeModelClient(
            [
                response("1", "read_file", path="missing.py"),
                response("2", "run_tests", target="unit"),
                response("3", "finish", summary="cannot erase the earlier error"),
            ]
        ),
        FakeToolExecutor(),
    )

    with pytest.raises(CompletionRejected, match="unresolved tool errors"):
        runner.run("fix")

    assert runner.state is not None
    assert runner.state.unresolved_tool_errors == ["file not found: missing.py"]


def test_protected_test_file_cannot_be_rewritten_to_fake_success() -> None:
    runner = AgentRunner(
        FakeModelClient(
            [
                response("1", "write_file", path="tests/test_calculator.py", content=""),
                response("2", "write_file", path="calculator.py", content="fixed"),
                response("3", "run_tests", target="unit"),
                response("4", "finish", summary="attempted test tampering"),
            ]
        ),
        FakeToolExecutor(files={"tests/test_calculator.py": "assert False"}),
    )

    with pytest.raises(CompletionRejected, match="unresolved tool errors"):
        runner.run("fix")

    assert runner.state is not None
    assert runner.state.unresolved_tool_errors == [
        "protected path: tests/test_calculator.py"
    ]


def test_executor_cannot_mutate_recorded_arguments() -> None:
    class MutatingExecutor(FakeToolExecutor):
        def execute(
            self,
            name: str,
            arguments: dict[str, object],
            *,
            timeout_seconds: float,
        ) -> ToolResult:
            original_path = str(arguments["path"])
            arguments.clear()
            self._workspace_revision += 1
            return ToolResult(ok=True, output=f"wrote {original_path}")

    runner = AgentRunner(
        FakeModelClient(
            [response("1", "write_file", path="calculator.py", content="fixed")]
        ),
        MutatingExecutor(),
        budget=RunBudget(max_steps=1),
    )

    with pytest.raises(BudgetExceeded, match="steps"):
        runner.run("fix")

    assert runner.state is not None
    assert runner.state.steps[0].arguments == {
        "path": "calculator.py",
        "content": "fixed",
    }


def test_non_json_tool_result_becomes_a_controlled_failure() -> None:
    class InvalidResultExecutor(FakeToolExecutor):
        def execute(
            self,
            name: str,
            arguments: dict[str, object],
            *,
            timeout_seconds: float,
        ) -> ToolResult:
            return ToolResult(ok=True, output="bad", metadata={"value": object()})

    runner = AgentRunner(
        FakeModelClient(
            [
                response("1", "write_file", path="calculator.py", content="fixed"),
                response("2", "finish", summary="invalid result was ignored"),
            ]
        ),
        InvalidResultExecutor(),
    )

    with pytest.raises(CompletionRejected, match="unresolved tool errors"):
        runner.run("fix")

    assert runner.state is not None
    assert "non-JSON ToolResult" in runner.state.unresolved_tool_errors[0]


def test_live_model_cannot_use_fake_host_executor() -> None:
    class LiveModel:
        is_live = True

    with pytest.raises(UnsafeExecutionError, match="sandboxed"):
        AgentRunner(LiveModel(), FakeToolExecutor())  # type: ignore[arg-type]
