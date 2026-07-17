"""LAB:chapter-05 STATUS:complete — the program owns the stop budget."""

from collections.abc import Iterable
from enum import StrEnum


class Decision(StrEnum):
    CONTINUE = "continue"
    FINISH = "finish"


def run_loop(decisions: Iterable[Decision], max_steps: int) -> int:
    if max_steps < 1:
        raise ValueError("max_steps must be positive")
    for step, decision in enumerate(decisions, start=1):
        if step > max_steps:
            break
        if decision is Decision.FINISH:
            return step
    raise RuntimeError("step budget exhausted")


if __name__ == "__main__":
    assert run_loop([Decision.CONTINUE, Decision.FINISH], 3) == 2
    try:
        run_loop([Decision.CONTINUE, Decision.CONTINUE], 1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("budget exhaustion was accepted")
    print("chapter-05: PASS")
