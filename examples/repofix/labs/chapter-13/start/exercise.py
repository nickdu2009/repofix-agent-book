"""LAB:chapter-13 STATUS:todo — aggregate deterministic evaluation results."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EvalResult:
    case_id: str
    passed: bool
    cost_usd: float


def pass_rate(results: list[EvalResult]) -> float:
    # TODO: reject an empty sample and return a value in [0, 1].
    raise NotImplementedError


if __name__ == "__main__":
    cases = [EvalResult("a", True, 0.1), EvalResult("b", False, 0.2)]
    assert pass_rate(cases) == 0.5
