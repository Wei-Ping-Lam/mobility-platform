"""Prevent reintroduction of machine-specific preview runtimes."""

from pathlib import Path


def test_tracked_project_files_do_not_reference_external_preview_runtime():
    root = Path(__file__).resolve().parents[3]
    forbidden = (
        "Quantum" + "ATK",
        "atk" + "python",
        "PYTHON" + "PATH",
    )
    excluded = {Path(__file__).resolve(), root / "uv.lock"}
    violations = []
    for path in root.rglob("*"):
        if (
            not path.is_file()
            or path.resolve() in excluded
            or any(part in {".git", ".venv", ".worktrees", "Rice WC Hack", ".tmp"} for part in path.parts)
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for token in forbidden:
            if token in text:
                violations.append(f"{path.relative_to(root)}: {token}")
    assert not violations, "Machine-specific runtime references found: " + ", ".join(violations)
