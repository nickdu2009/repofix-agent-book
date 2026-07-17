"""Constrained UTF-8 file helpers for trusted local exercises.

These helpers are not a sandbox. A live model may only use an executor backed by an
isolated environment such as Daytona.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

MAX_FILE_BYTES = 1_000_000


class WorkspacePathError(ValueError):
    pass


def resolve_safe_path(root: Path, relative_path: str) -> Path:
    if not relative_path:
        raise WorkspacePathError("path must not be empty")
    candidate = Path(relative_path)
    if candidate.is_absolute():
        raise WorkspacePathError("absolute paths are not allowed")

    resolved_root = root.resolve(strict=True)
    target = (resolved_root / candidate).resolve(strict=False)
    if target != resolved_root and resolved_root not in target.parents:
        raise WorkspacePathError("path escapes workspace")
    return target


def read_utf8_file(root: Path, relative_path: str, *, max_bytes: int = MAX_FILE_BYTES) -> str:
    target = resolve_safe_path(root, relative_path)
    if not target.is_file():
        raise WorkspacePathError("path is not a regular file")
    if target.stat().st_size > max_bytes:
        raise WorkspacePathError("file exceeds size limit")
    data = target.read_bytes()
    if b"\x00" in data:
        raise WorkspacePathError("binary files are not supported")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise WorkspacePathError("file is not valid UTF-8") from error


def write_utf8_file(
    root: Path,
    relative_path: str,
    content: str,
    *,
    max_bytes: int = MAX_FILE_BYTES,
) -> None:
    encoded = content.encode("utf-8")
    if len(encoded) > max_bytes:
        raise WorkspacePathError("content exceeds size limit")

    target = resolve_safe_path(root, relative_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not target.is_file():
        raise WorkspacePathError("target is not a regular file")

    file_descriptor, temporary_name = tempfile.mkstemp(dir=target.parent, prefix=".repofix-")
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(file_descriptor, "wb") as temporary_file:
            temporary_file.write(encoded)
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
