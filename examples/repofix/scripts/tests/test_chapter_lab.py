from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import uuid
from pathlib import Path

from scripts.chapter_lab import ChapterLab, LabError, PROJECT_ROOT


class ChapterLabTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "labs/chapter-01/start").mkdir(parents=True)
        (self.root / "labs/chapter-01/solution").mkdir(parents=True)
        (self.root / "chapters.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "chapters": [
                        {
                            "id": "chapter-01",
                            "title": "Test chapter",
                            "doc": "test.md",
                            "kind": "template",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (self.root / "labs/chapter-01/start/DESIGN.md").write_text(
            "<!-- LAB:chapter-01 STATUS:todo -->\nTODO\n",
            encoding="utf-8",
        )
        (self.root / "labs/chapter-01/solution/DESIGN.md").write_text(
            "<!-- LAB:chapter-01 STATUS:complete -->\nDecision recorded.\n",
            encoding="utf-8",
        )
        self.labs = ChapterLab(self.root)

    def test_prepare_refuses_overwrite_and_check_distinguishes_variants(self) -> None:
        start = self.labs.prepare("chapter-01")
        self.assertFalse(self.labs.check("chapter-01").passed)
        with self.assertRaisesRegex(LabError, "already exists"):
            self.labs.prepare("chapter-01")

        solution_path = self.root / ".work/chapter-01-solution"
        self.labs.prepare(
            "chapter-01",
            workspace=solution_path,
            variant="solution",
        )
        self.assertTrue(
            self.labs.check("chapter-01", workspace=solution_path).passed
        )
        self.assertTrue((start / ".chapter-lab.json").is_file())

    def test_rejects_chapter_and_workspace_traversal(self) -> None:
        with self.assertRaisesRegex(LabError, "unknown chapter"):
            self.labs.prepare("../chapter-01")
        with self.assertRaisesRegex(LabError, "must not contain"):
            self.labs.prepare(
                "chapter-01",
                workspace=Path(".work/../outside"),
            )
        with self.assertRaisesRegex(LabError, "must be a child"):
            self.labs.prepare(
                "chapter-01",
                workspace=self.root.parent / "outside",
            )

    def test_rejects_symlink_in_source(self) -> None:
        link = self.root / "labs/chapter-01/start/escape"
        try:
            link.symlink_to(self.root.parent)
        except OSError:
            self.skipTest("symbolic links are unavailable")
        with self.assertRaisesRegex(LabError, "symbolic link"):
            self.labs.prepare("chapter-01")

    def test_rejects_work_root_symlink_to_external_directory(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside, True)
        try:
            (self.root / ".work").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symbolic links are unavailable")
        with self.assertRaisesRegex(LabError, "must not be a symbolic link"):
            self.labs.prepare("chapter-01")

    def test_all_real_starts_fail_and_solutions_pass_structural_policy(self) -> None:
        real = ChapterLab(PROJECT_ROOT)
        self.assertEqual(19, len(real.chapters))
        suite_root = PROJECT_ROOT / ".work" / f"lab-test-{uuid.uuid4().hex}"
        try:
            for chapter in real.chapters:
                doc = PROJECT_ROOT.parents[1] / "docs" / chapter.doc
                text = doc.read_text(encoding="utf-8")
                self.assertIn("## 快速开始", text)
                self.assertIn(
                    f"make chapter-prepare CHAPTER={chapter.id}",
                    text,
                )
                self.assertIn(f"labs/{chapter.id}/start/", text)
                self.assertIn(f".work/{chapter.id}/", text)
                self.assertIn(f"labs/{chapter.id}/solution/", text)
                with self.subTest(chapter=chapter.id, variant="start"):
                    start = suite_root / f"{chapter.id}-start"
                    real.prepare(chapter.id, workspace=start, variant="start")
                    self.assertFalse(real.check(chapter.id, workspace=start).passed)
                with self.subTest(chapter=chapter.id, variant="solution"):
                    solution = suite_root / f"{chapter.id}-solution"
                    real.prepare(chapter.id, workspace=solution, variant="solution")
                    self.assertTrue(real.check(chapter.id, workspace=solution).passed)
        finally:
            shutil.rmtree(suite_root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
