"""Deterministic checks for RepoFix's canonical contract files and wire enums."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError


ROOT = Path(__file__).parent
COMPANION_ROOT = ROOT.parent
SCHEMA_FILES = sorted(ROOT.glob("*.schema.json"))
EXPECTED_STATUSES = {
    "pending",
    "provisioning",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "timed_out",
}
EXPECTED_EVENTS = {
    "run.started",
    "sandbox.created",
    "sandbox.deleted",
    "sandbox.cleanup_failed",
    "step.started",
    "tool.started",
    "tool.completed",
    "tests.completed",
    "patch.created",
    "run.succeeded",
    "run.failed",
    "run.cancelled",
    "run.timed_out",
}


def load(name: str) -> dict[str, object]:
    with (ROOT / name).open(encoding="utf-8") as source:
        return json.load(source)


def validator(name: str) -> Draft202012Validator:
    document = load(name)
    Draft202012Validator.check_schema(document)
    return Draft202012Validator(document, format_checker=FormatChecker())


def expect_invalid(checker: Draft202012Validator, payload: object, label: str) -> None:
    try:
        checker.validate(payload)
    except ValidationError:
        return
    raise SystemExit(f"schema unexpectedly accepted {label}")


def go_wire_values(relative_path: str, type_name: str) -> set[str]:
    """Read string constants for one Go wire type without requiring a Go toolchain."""

    source = (COMPANION_ROOT / relative_path).read_text(encoding="utf-8")
    pattern = rf'^\s*\w+\s+{re.escape(type_name)}\s*=\s*"([^"]+)"'
    return set(re.findall(pattern, source, flags=re.MULTILINE))


def typescript_wire_values(const_name: str) -> set[str]:
    """Read one `as const` wire-value array from the Web boundary module."""

    source_path = COMPANION_ROOT / "apps/web/src/contracts.ts"
    source = source_path.read_text(encoding="utf-8")
    match = re.search(
        rf"export const {re.escape(const_name)} = \[(.*?)\] as const;",
        source,
        flags=re.DOTALL,
    )
    if match is None:
        raise SystemExit(f"missing TypeScript wire constant: {const_name}")
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def require_wire_values(label: str, actual: set[str], expected: set[str]) -> None:
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SystemExit(f"{label} wire values drifted: missing={missing}, extra={extra}")


def main() -> None:
    if not SCHEMA_FILES:
        raise SystemExit("no contract schemas found")

    schema_ids: set[str] = set()
    for path in SCHEMA_FILES:
        document = load(path.name)
        Draft202012Validator.check_schema(document)
        schema_id = str(document.get("$id", ""))
        if not schema_id or schema_id in schema_ids:
            raise SystemExit(f"missing or duplicate $id in {path.name}")
        schema_ids.add(schema_id)

    run_schema = load("run.schema.json")
    statuses = set(run_schema["properties"]["status"]["enum"])  # type: ignore[index]
    if statuses != EXPECTED_STATUSES:
        raise SystemExit(f"unexpected RunStatus values: {sorted(statuses)}")

    event_schema = load("run-event.schema.json")
    event_types = set(event_schema["properties"]["type"]["enum"])  # type: ignore[index]
    if event_types != EXPECTED_EVENTS:
        raise SystemExit(f"unexpected RunEvent values: {sorted(event_types)}")

    require_wire_values(
        "Go RunStatus",
        go_wire_values("services/control/internal/domain/run.go", "RunStatus"),
        EXPECTED_STATUSES,
    )
    require_wire_values(
        "Go RunEvent",
        go_wire_values("services/control/internal/domain/event.go", "EventType"),
        EXPECTED_EVENTS,
    )
    require_wire_values(
        "TypeScript RunStatus",
        typescript_wire_values("RUN_STATUSES"),
        EXPECTED_STATUSES,
    )
    require_wire_values(
        "TypeScript RunEvent",
        typescript_wire_values("RUN_EVENT_TYPES"),
        EXPECTED_EVENTS,
    )

    run = validator("run.schema.json")
    valid_run = {
        "id": "run_1",
        "task_id": "task_1",
        "status": "running",
        "created_at": "2026-07-17T10:00:00Z",
        "updated_at": "2026-07-17T10:00:01Z",
        "version": 1,
    }
    run.validate(valid_run)
    expect_invalid(run, {**valid_run, "status": "testing"}, "unknown RunStatus")
    expect_invalid(run, {**valid_run, "extra": True}, "extra Run field")

    event = validator("run-event.schema.json")
    valid_event = {
        "id": "event_1",
        "run_id": "run_1",
        "sequence": 1,
        "type": "run.started",
        "occurred_at": "2026-07-17T10:00:00Z",
        "schema_version": 1,
        "data": {},
    }
    event.validate(valid_event)
    expect_invalid(event, {**valid_event, "sequence": 0}, "non-positive sequence")
    expect_invalid(event, {**valid_event, "schema_version": 2}, "old client version")
    expect_invalid(event, {**valid_event, "unknown": None}, "extra event field")

    error = validator("error.schema.json")
    error.validate(
        {
            "code": "invalid_request",
            "message": "bad input",
            "request_id": "request_1",
            "retryable": False,
        }
    )

    artifact = validator("artifact.schema.json")
    artifact.validate(
        {
            "id": "artifact_1",
            "run_id": "run_1",
            "kind": "patch",
            "content_type": "text/x-diff",
            "size_bytes": 42,
            "sha256": "0" * 64,
            "created_at": "2026-07-17T10:00:00Z",
        }
    )

    print(f"validated {len(SCHEMA_FILES)} contract schemas and positive/negative examples")


if __name__ == "__main__":
    main()
