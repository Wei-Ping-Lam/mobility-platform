import ast
from pathlib import Path

PORTFOLIO_ROOT = Path(__file__).parents[2] / "ui" / "portfolio"
TAB_MODULES = {
    "resilience",
    "visitor_movement",
    "first_last_mile",
    "investments",
    "traffic_management",
}


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_each_objective_has_an_independent_renderer_module() -> None:
    assert TAB_MODULES == {path.stem for path in PORTFOLIO_ROOT.glob("*.py") if path.stem in TAB_MODULES}


def test_objective_renderers_consume_context_without_importing_analytics() -> None:
    for module in TAB_MODULES:
        imports = _imports(PORTFOLIO_ROOT / f"{module}.py")
        assert not any(
            name.startswith("dashboard.domain") or name.startswith("dashboard.models") for name in imports
        ), module
        assert not any(
            name == f"dashboard.ui.portfolio.{other}" for other in TAB_MODULES - {module} for name in imports
        ), module


def test_page_is_the_only_objective_composition_module() -> None:
    tree = ast.parse(
        (PORTFOLIO_ROOT / "page.py").read_text(encoding="utf-8"),
        filename="page.py",
    )
    imported_tabs = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "dashboard.ui.portfolio"
        for alias in node.names
    }
    assert imported_tabs == TAB_MODULES
