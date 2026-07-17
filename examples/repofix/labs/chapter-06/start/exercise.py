"""LAB:chapter-06 STATUS:todo — keep file access inside one workspace."""

from pathlib import Path


def safe_path(root: Path, relative: str) -> Path:
    # TODO: resolve both paths and reject traversal outside root.
    return root / relative


if __name__ == "__main__":
    root = Path("/workspace/project")
    assert safe_path(root, "src/app.py") == root / "src/app.py"
