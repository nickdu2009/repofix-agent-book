#!/usr/bin/env python3
"""Prepare and inspect deterministic RepoFix chapter labs without executing them."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_BY_KIND = {
    "template": "DESIGN.md",
    "workspace": "DESIGN.md",
    "contract": "contract.json",
    "python": "exercise.py",
    "go": "main.go",
    "typescript": "exercise.ts",
}


class LabError(RuntimeError):
    """Raised when a catalog entry or workspace violates lab policy."""


@dataclass(frozen=True, slots=True)
class Chapter:
    id: str
    title: str
    doc: str
    kind: str


@dataclass(frozen=True, slots=True)
class CheckResult:
    passed: bool
    messages: tuple[str, ...]


class ChapterLab:
    """Read lab sources and copy them only into this project's .work tree."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()
        self.catalog_path = self.project_root / "chapters.json"
        self.labs_root = self.project_root / "labs"
        self.raw_work_root = self.project_root / ".work"
        self._chapters = self._load_catalog()

    @property
    def chapters(self) -> tuple[Chapter, ...]:
        return tuple(self._chapters.values())

    def chapter(self, chapter_id: str) -> Chapter:
        try:
            return self._chapters[chapter_id]
        except KeyError as exc:
            raise LabError(f"unknown chapter: {chapter_id}") from exc

    def prepare(
        self,
        chapter_id: str,
        *,
        workspace: Path | None = None,
        variant: str = "start",
    ) -> Path:
        chapter = self.chapter(chapter_id)
        if variant not in {"start", "solution"}:
            raise LabError(f"unsupported variant: {variant}")

        source = self._lab_source(chapter.id, variant)
        target = self.workspace_path(chapter.id, workspace)
        if target.exists():
            raise LabError(
                f"workspace already exists: {target}; move or remove it explicitly first"
            )

        self._reject_symlinks(source)
        self._ensure_work_root()
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target, copy_function=shutil.copy2)
        marker = {
            "schema_version": 1,
            "chapter_id": chapter.id,
            "variant": variant,
            "source": f"labs/{chapter.id}/{variant}",
        }
        (target / ".chapter-lab.json").write_text(
            json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return target

    def check(
        self,
        chapter_id: str,
        *,
        workspace: Path | None = None,
    ) -> CheckResult:
        chapter = self.chapter(chapter_id)
        target = self.workspace_path(chapter.id, workspace)
        if not target.is_dir() or target.is_symlink():
            raise LabError(f"workspace does not exist as a real directory: {target}")

        messages: list[str] = []
        marker_path = target / ".chapter-lab.json"
        marker = self._read_json_object(marker_path, "workspace marker")
        if marker.get("chapter_id") != chapter.id:
            messages.append("workspace marker belongs to a different chapter")

        artifact_name = ARTIFACT_BY_KIND[chapter.kind]
        artifact = target / artifact_name
        if not artifact.is_file() or artifact.is_symlink():
            messages.append(f"missing regular artifact: {artifact_name}")
        elif chapter.kind == "contract":
            payload = self._read_json_object(artifact, "contract artifact")
            if payload.get("_lab") != chapter.id:
                messages.append(f"contract _lab must equal {chapter.id}")
            if payload.get("_status") != "complete":
                messages.append("contract _status must equal complete")
            if "TODO" in artifact.read_text(encoding="utf-8"):
                messages.append("contract still contains TODO")
        else:
            text = artifact.read_text(encoding="utf-8")
            if f"LAB:{chapter.id}" not in text:
                messages.append(f"artifact is missing LAB:{chapter.id}")
            if "STATUS:complete" not in text:
                messages.append("artifact is not marked STATUS:complete")
            if "TODO" in text:
                messages.append("artifact still contains TODO")

        if messages:
            return CheckResult(False, tuple(messages))
        return CheckResult(True, (f"{chapter.id}: structural checks passed",))

    def workspace_path(self, chapter_id: str, workspace: Path | None) -> Path:
        self.chapter(chapter_id)
        if self.raw_work_root.is_symlink():
            raise LabError(".work must not be a symbolic link")
        work_root = self.raw_work_root.resolve(strict=False)

        if workspace is None:
            candidate_input = work_root / chapter_id
        else:
            if ".." in workspace.parts:
                raise LabError("workspace path must not contain '..'")
            candidate_input = (
                workspace if workspace.is_absolute() else self.project_root / workspace
            )
            if candidate_input.is_symlink():
                raise LabError("workspace must not be a symbolic link")

        candidate = candidate_input.resolve(strict=False)
        if candidate == work_root or work_root not in candidate.parents:
            raise LabError(f"workspace must be a child of {work_root}")
        return candidate

    def _load_catalog(self) -> dict[str, Chapter]:
        payload = self._read_json_object(self.catalog_path, "chapter catalog")
        if payload.get("schema_version") != 1:
            raise LabError("unsupported chapters.json schema_version")
        raw_chapters = payload.get("chapters")
        if not isinstance(raw_chapters, list):
            raise LabError("chapters.json chapters must be an array")

        chapters: dict[str, Chapter] = {}
        for raw in raw_chapters:
            if not isinstance(raw, dict):
                raise LabError("each chapter entry must be an object")
            chapter = Chapter(
                id=self._required_string(raw, "id"),
                title=self._required_string(raw, "title"),
                doc=self._required_string(raw, "doc"),
                kind=self._required_string(raw, "kind"),
            )
            if chapter.id in chapters:
                raise LabError(f"duplicate chapter id: {chapter.id}")
            if chapter.kind not in ARTIFACT_BY_KIND:
                raise LabError(f"unsupported chapter kind: {chapter.kind}")
            if not self._valid_chapter_id(chapter.id):
                raise LabError(f"invalid chapter id: {chapter.id}")
            chapters[chapter.id] = chapter
        return chapters

    def _lab_source(self, chapter_id: str, variant: str) -> Path:
        source = (self.labs_root / chapter_id / variant).resolve(strict=True)
        labs_root = self.labs_root.resolve(strict=True)
        if labs_root not in source.parents or not source.is_dir():
            raise LabError(f"invalid lab source: {source}")
        expected = ARTIFACT_BY_KIND[self.chapter(chapter_id).kind]
        if not (source / expected).is_file():
            raise LabError(f"lab source is missing {expected}: {source}")
        return source

    def _ensure_work_root(self) -> None:
        if self.raw_work_root.is_symlink():
            raise LabError(".work must not be a symbolic link")
        self.raw_work_root.mkdir(parents=False, exist_ok=True)

    @staticmethod
    def _reject_symlinks(source: Path) -> None:
        if source.is_symlink():
            raise LabError(f"lab source must not be a symbolic link: {source}")
        for entry in source.rglob("*"):
            if entry.is_symlink():
                raise LabError(f"lab source contains a symbolic link: {entry}")

    @staticmethod
    def _read_json_object(path: Path, label: str) -> dict[str, Any]:
        if not path.is_file() or path.is_symlink():
            raise LabError(f"missing regular {label}: {path}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise LabError(f"invalid {label}: {path}") from exc
        if not isinstance(value, dict):
            raise LabError(f"{label} must contain a JSON object: {path}")
        return value

    @staticmethod
    def _required_string(value: dict[str, Any], key: str) -> str:
        field = value.get(key)
        if not isinstance(field, str) or not field:
            raise LabError(f"chapter field {key!r} must be a non-empty string")
        return field

    @staticmethod
    def _valid_chapter_id(chapter_id: str) -> bool:
        return (
            len(chapter_id) == 10
            and chapter_id.startswith("chapter-")
            and chapter_id[-2:].isdigit()
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="list chapter ids and lab kinds")

    prepare = subparsers.add_parser("prepare", help="copy a lab into .work")
    prepare.add_argument("chapter")
    prepare.add_argument("--workspace", type=Path)
    prepare.add_argument("--variant", choices=("start", "solution"), default="start")

    check = subparsers.add_parser("check", help="check a prepared lab structurally")
    check.add_argument("chapter")
    check.add_argument("--workspace", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        labs = ChapterLab(PROJECT_ROOT)
        if args.command == "list":
            for chapter in labs.chapters:
                print(f"{chapter.id}\t{chapter.kind}\t{chapter.title}")
            return 0
        if args.command == "prepare":
            target = labs.prepare(
                args.chapter,
                workspace=args.workspace,
                variant=args.variant,
            )
            print(f"prepared {args.chapter} at {target}")
            return 0
        if args.command == "check":
            result = labs.check(args.chapter, workspace=args.workspace)
            stream = sys.stdout if result.passed else sys.stderr
            for message in result.messages:
                print(message, file=stream)
            return 0 if result.passed else 1
    except LabError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
