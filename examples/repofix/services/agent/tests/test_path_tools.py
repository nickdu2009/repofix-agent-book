from __future__ import annotations

from pathlib import Path

import pytest

from repofix_agent.path_tools import (
    WorkspacePathError,
    read_utf8_file,
    resolve_safe_path,
    write_utf8_file,
)


@pytest.mark.parametrize("path", ["../../etc/passwd", "/etc/passwd"])
def test_path_escape_is_rejected(tmp_path: Path, path: str) -> None:
    with pytest.raises(WorkspacePathError):
        resolve_safe_path(tmp_path, path)


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (tmp_path / "link.txt").symlink_to(outside)

    with pytest.raises(WorkspacePathError, match="escapes"):
        read_utf8_file(tmp_path, "link.txt")


def test_utf8_write_is_atomic_and_readable(tmp_path: Path) -> None:
    write_utf8_file(tmp_path, "src/message.txt", "你好，RepoFix\n")

    assert read_utf8_file(tmp_path, "src/message.txt") == "你好，RepoFix\n"
    assert not list((tmp_path / "src").glob(".repofix-*"))


def test_binary_and_large_files_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "binary.dat").write_bytes(b"a\x00b")
    (tmp_path / "large.txt").write_text("12345", encoding="utf-8")

    with pytest.raises(WorkspacePathError, match="binary"):
        read_utf8_file(tmp_path, "binary.dat")
    with pytest.raises(WorkspacePathError, match="size"):
        read_utf8_file(tmp_path, "large.txt", max_bytes=4)
