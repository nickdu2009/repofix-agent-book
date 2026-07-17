from __future__ import annotations

import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOOK_ROOT = PROJECT_ROOT.parents[1]


class PlaygroundAssetsTest(unittest.TestCase):
    def test_runner_is_pinned_worker_based_and_does_not_read_secrets(self) -> None:
        script = (
            BOOK_ROOT / "docs/assets/javascripts/python-runner.js"
        ).read_text(encoding="utf-8")
        self.assertIn('PYODIDE_VERSION = "314.0.2"', script)
        self.assertIn("new Worker", script)
        self.assertIn("EXECUTION_TIMEOUT_MS", script)
        self.assertIn("textContent", script)
        self.assertIn("document$.subscribe", script)
        self.assertIn("runnerMounted", script)
        for forbidden in (
            "OPENAI_API_KEY",
            "DAYTONA_API_KEY",
            "document.cookie",
            "localStorage",
            "loadPackagesFromImports",
        ):
            self.assertNotIn(forbidden, script)

    def test_page_uses_official_playgrounds_and_explains_check_boundary(self) -> None:
        page = (BOOK_ROOT / "docs/playgrounds/index.md").read_text(encoding="utf-8")
        self.assertIn("https://go.dev/play/", page)
        self.assertIn("https://www.typescriptlang.org/play/", page)
        self.assertIn("不会执行学习者代码", page)
        self.assertIn("python .work/chapter-03/exercise.py", page)
        self.assertIn("go run .work/chapter-10/main.go", page)
        self.assertIn("node .work/chapter-15/exercise.ts", page)


if __name__ == "__main__":
    unittest.main()
