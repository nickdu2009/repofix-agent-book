"""LAB:chapter-06 STATUS:complete — lexical traversal is rejected."""

from pathlib import Path


def safe_path(root: Path, relative: str) -> Path:
    root = root.resolve()
    target = (root / relative).resolve()
    if target != root and root not in target.parents:
        raise ValueError("path escapes workspace")
    return target


if __name__ == "__main__":
    root = Path("/workspace/project")
    assert safe_path(root, "src/app.py") == root / "src/app.py"
    try:
        safe_path(root, "../../etc/passwd")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal was accepted")
    print("chapter-06: PASS")
