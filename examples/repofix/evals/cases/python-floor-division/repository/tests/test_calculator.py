from calculator import divide


def test_fractional_division() -> None:
    assert divide(5, 2) == 2.5
