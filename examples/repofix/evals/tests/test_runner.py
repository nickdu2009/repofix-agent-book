from __future__ import annotations

from pathlib import Path
import json
import shutil

from evals.runner import run_eval

CASE = Path(__file__).parents[1] / "cases" / "python-floor-division"


def test_independent_oracle_accepts_the_minimal_fix() -> None:
    def repair(workspace: Path) -> None:
        target = workspace / "calculator.py"
        target.write_text(
            target.read_text(encoding="utf-8").replace("left // right", "left / right"),
            encoding="utf-8",
        )

    result = run_eval(CASE, repair)

    assert result.outcome == "passed"
    assert result.changed_paths == ("calculator.py",)
    assert result.patch_sha256 is not None


def test_modifying_visible_tests_is_rejected_before_oracle() -> None:
    def tamper(workspace: Path) -> None:
        (workspace / "tests" / "test_calculator.py").write_text(
            "def test_nothing():\n    assert True\n",
            encoding="utf-8",
        )

    result = run_eval(CASE, tamper)

    assert result.outcome == "agent_failed"
    assert "forbidden paths" in result.detail


def test_hidden_oracle_rejects_a_visible_test_special_case() -> None:
    def overfit(workspace: Path) -> None:
        (workspace / "calculator.py").write_text(
            "def divide(left: float, right: float) -> float:\n"
            "    if (left, right) == (5, 2):\n"
            "        return 2.5\n"
            "    return left // right\n",
            encoding="utf-8",
        )

    result = run_eval(CASE, overfit)

    assert result.outcome == "oracle_failed"


def test_invalid_metadata_is_an_infrastructure_failure(tmp_path: Path) -> None:
    copied = tmp_path / "case"
    shutil.copytree(CASE, copied)
    metadata = json.loads((copied / "metadata.json").read_text(encoding="utf-8"))
    metadata["unexpected"] = True
    (copied / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")

    result = run_eval(copied, lambda workspace: None)

    assert result.outcome == "infrastructure_failed"
    assert "Additional properties" in result.detail
