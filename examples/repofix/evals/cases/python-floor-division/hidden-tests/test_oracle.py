from calculator import divide


def test_negative_fractional_division() -> None:
    assert divide(-5, 2) == -2.5


def test_exact_division() -> None:
    assert divide(8, 4) == 2
