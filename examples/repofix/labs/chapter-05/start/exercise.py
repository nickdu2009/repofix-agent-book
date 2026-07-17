"""LAB:chapter-05 STATUS:todo — build a bounded deterministic Agent loop."""

from collections.abc import Iterable
from enum import StrEnum


class Decision(StrEnum):
    CONTINUE = "continue"
    FINISH = "finish"


def run_loop(decisions: Iterable[Decision], max_steps: int) -> int:
    # TODO: return the step that finishes and reject an exhausted budget.
    raise NotImplementedError


if __name__ == "__main__":
    assert run_loop([Decision.CONTINUE, Decision.FINISH], 3) == 2
