from pathlib import Path
import sys

FIXTURE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FIXTURE_ROOT))

from calculator import divide  # noqa: E402


def test_even_integer_division() -> None:
    assert divide(8, 2) == 4


def test_fractional_division() -> None:
    assert divide(5, 2) == 2.5
