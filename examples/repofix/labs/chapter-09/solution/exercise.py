"""LAB:chapter-09 STATUS:complete — validate before entering Agent logic."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RunRequest:
    run_id: str
    task: str


def validate_request(request: RunRequest) -> dict[str, str]:
    if not request.run_id or not request.task.strip():
        raise ValueError("run_id and task are required")
    return {"run_id": request.run_id, "status": "accepted"}


if __name__ == "__main__":
    assert validate_request(RunRequest("run-1", "fix bug")) == {
        "run_id": "run-1",
        "status": "accepted",
    }
    try:
        validate_request(RunRequest("", " "))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid request was accepted")
    print("chapter-09: PASS")
