"""LAB:chapter-03 STATUS:complete — a tiny deterministic defect fixture."""


def divide(total: int, count: int) -> float:
    if count == 0:
        raise ValueError("count must be non-zero")
    return total / count


def verify() -> None:
    assert divide(9, 3) == 3
    try:
        divide(9, 0)
    except ValueError as exc:
        assert str(exc) == "count must be non-zero"
    else:
        raise AssertionError("zero count was accepted")


if __name__ == "__main__":
    verify()
    print("chapter-03: PASS")
