"""LAB:chapter-14 STATUS:todo — select context under a hard budget."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    score: int
    tokens: int


def select(candidates: list[Candidate], budget: int) -> list[str]:
    # TODO: prefer higher scores without exceeding the token budget.
    raise NotImplementedError


if __name__ == "__main__":
    items = [Candidate("a.py", 9, 4), Candidate("b.py", 5, 3)]
    assert select(items, 4) == ["a.py"]
