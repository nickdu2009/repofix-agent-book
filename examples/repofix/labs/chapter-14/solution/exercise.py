"""LAB:chapter-14 STATUS:complete — deterministic context selection."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Candidate:
    path: str
    score: int
    tokens: int


def select(candidates: list[Candidate], budget: int) -> list[str]:
    if budget < 0:
        raise ValueError("budget must not be negative")
    selected: list[str] = []
    used = 0
    for item in sorted(candidates, key=lambda value: (-value.score, value.path)):
        if item.tokens >= 0 and used + item.tokens <= budget:
            selected.append(item.path)
            used += item.tokens
    return selected


if __name__ == "__main__":
    items = [Candidate("a.py", 9, 4), Candidate("b.py", 5, 3)]
    assert select(items, 4) == ["a.py"]
    assert select(items, 7) == ["a.py", "b.py"]
    print("chapter-14: PASS")
