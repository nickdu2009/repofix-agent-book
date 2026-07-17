"""A zero-cloud evaluation checkpoint with an independent verification copy."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal

from jsonschema import Draft202012Validator, ValidationError

Outcome = Literal["passed", "agent_failed", "oracle_failed", "infrastructure_failed"]
Repairer = Callable[[Path], None]


@dataclass(frozen=True)
class EvalResult:
    case_id: str
    outcome: Outcome
    duration_ms: int
    changed_paths: tuple[str, ...]
    patch_sha256: str | None
    detail: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


def _tracked_files(root: Path) -> dict[str, bytes]:
    ignored = {"__pycache__", ".pytest_cache"}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and not ignored.intersection(path.parts)
    }


def _run_pytest(root: Path, *targets: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *targets],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _patch_hash(files: dict[str, bytes], changed_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for path in changed_paths:
        digest.update(path.encode())
        digest.update(b"\0")
        digest.update(files[path])
        digest.update(b"\0")
    return digest.hexdigest()


def run_eval(case_dir: Path, repairer: Repairer) -> EvalResult:
    """Run one trusted local case.

    The repairer sees only a copied repository. Hidden tests are introduced in a
    second clean directory after the candidate changes have been collected.
    """

    started = time.monotonic()
    metadata = json.loads((case_dir / "metadata.json").read_text(encoding="utf-8"))
    case_id = str(metadata.get("case_id", "unknown"))

    try:
        schema = json.loads(
            Path(__file__).with_name("case.schema.json").read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(metadata)
        forbidden = tuple(str(item) for item in metadata["forbidden_paths"])
        with TemporaryDirectory(prefix="repofix-eval-") as temporary:
            temporary_root = Path(temporary)
            workspace = temporary_root / "workspace"
            verifier = temporary_root / "verifier"
            shutil.copytree(case_dir / "repository", workspace)

            baseline = _run_pytest(workspace, "tests")
            if baseline.returncode != 1:
                raise RuntimeError(
                    f"baseline must fail with pytest code 1, got {baseline.returncode}"
                )

            before = _tracked_files(workspace)
            repairer(workspace)
            after = _tracked_files(workspace)
            changed_paths = tuple(
                sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
            )
            if not changed_paths:
                return _result(started, case_id, "agent_failed", (), None, "no candidate patch")
            deleted = [path for path in changed_paths if path not in after]
            if deleted:
                return _result(
                    started,
                    case_id,
                    "agent_failed",
                    changed_paths,
                    None,
                    f"deleting files is not allowed in this checkpoint: {deleted}",
                )
            forbidden_changes = [
                path
                for path in changed_paths
                if any(fnmatch.fnmatch(path, pattern) for pattern in forbidden)
            ]
            if forbidden_changes:
                return _result(
                    started,
                    case_id,
                    "agent_failed",
                    changed_paths,
                    None,
                    f"forbidden paths changed: {forbidden_changes}",
                )

            shutil.copytree(case_dir / "repository", verifier)
            for relative in changed_paths:
                destination = verifier / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(after[relative])
            shutil.copytree(case_dir / "hidden-tests", verifier / "oracle_tests")

            patch_sha256 = _patch_hash(after, changed_paths)
            oracle = _run_pytest(verifier, "tests", "oracle_tests")
            outcome: Outcome = "passed" if oracle.returncode == 0 else "oracle_failed"
            return _result(
                started,
                case_id,
                outcome,
                changed_paths,
                patch_sha256,
                oracle.stdout[-2_000:] + oracle.stderr[-2_000:],
            )
    except (
        OSError,
        KeyError,
        RuntimeError,
        TypeError,
        ValueError,
        ValidationError,
        subprocess.SubprocessError,
    ) as error:
        return _result(
            started,
            case_id,
            "infrastructure_failed",
            (),
            None,
            str(error),
        )


def _result(
    started: float,
    case_id: str,
    outcome: Outcome,
    changed_paths: tuple[str, ...],
    patch_sha256: str | None,
    detail: str,
) -> EvalResult:
    return EvalResult(
        case_id=case_id,
        outcome=outcome,
        duration_ms=round((time.monotonic() - started) * 1_000),
        changed_paths=changed_paths,
        patch_sha256=patch_sha256,
        detail=detail,
    )
