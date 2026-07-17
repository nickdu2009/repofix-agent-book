"""LAB:chapter-03 STATUS:todo — make the fixture expose a stable failure."""


def divide(total: int, count: int) -> float:
    # TODO: reject a zero count with the documented exception.
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
