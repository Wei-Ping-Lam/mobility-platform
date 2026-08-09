from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parents[2]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("package", ["pipeline", "models", "domain"])
def test_analytics_layers_do_not_import_streamlit_or_ui(package: str) -> None:
    violations: list[str] = []
    for path in (PACKAGE_ROOT / package).rglob("*.py"):
        imports = _imports(path)
        if any(name == "streamlit" or name.startswith("dashboard.ui") for name in imports):
            violations.append(str(path.relative_to(PACKAGE_ROOT.parent)))
    assert violations == []


def test_public_app_shell_does_not_import_deferred_workspace_renderers() -> None:
    imports = _imports(PACKAGE_ROOT / "app.py")
    assert "dashboard.ui.views" not in imports
