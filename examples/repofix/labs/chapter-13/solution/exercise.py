"""LAB:chapter-13 STATUS:complete — aggregate deterministic evaluation results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvalResult:
    case_id: str
    passed: bool
    cost_usd: float


def pass_rate(results: list[EvalResult]) -> float:
    if not results:
        raise ValueError("at least one result is required")
    return sum(result.passed for result in results) / len(results)


if __name__ == "__main__":
    cases = [EvalResult("a", True, 0.1), EvalResult("b", False, 0.2)]
    assert pass_rate(cases) == 0.5
    assert abs(sum(case.cost_usd for case in cases) - 0.3) < 1e-9
    print("chapter-13: PASS")
