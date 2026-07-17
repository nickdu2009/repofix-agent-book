"""LAB:chapter-04 STATUS:todo — restore Python typing and data modelling."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Step:
    number: int
    tool: str


def latest_tool(steps: list[Step]) -> str | None:
    # TODO: return the last tool without mutating the input.
    raise NotImplementedError


if __name__ == "__main__":
    sample = [Step(1, "read_file"), Step(2, "run_tests")]
    assert latest_tool(sample) == "run_tests"
