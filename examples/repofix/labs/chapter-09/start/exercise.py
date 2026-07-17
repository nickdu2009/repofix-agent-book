"""LAB:chapter-09 STATUS:todo — model a service boundary without a server."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunRequest:
    run_id: str
    task: str


def validate_request(request: RunRequest) -> dict[str, str]:
    # TODO: reject empty boundary fields and return a stable response.
    raise NotImplementedError


if __name__ == "__main__":
    assert validate_request(RunRequest("run-1", "fix bug"))["status"] == "accepted"
