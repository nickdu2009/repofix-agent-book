"""LAB:chapter-04 STATUS:complete — typed immutable records and None."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Step:
    number: int
    tool: str


def latest_tool(steps: list[Step]) -> str | None:
    return steps[-1].tool if steps else None


if __name__ == "__main__":
    sample = [Step(1, "read_file"), Step(2, "run_tests")]
    before = sample.copy()
    assert latest_tool(sample) == "run_tests"
    assert latest_tool([]) is None
    assert sample == before
    print("chapter-04: PASS")
