from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.ui.theme import status_badge
from dashboard.viz.style import STATUS_COLORS


@pytest.mark.parametrize(
    ("mode", "expected_tabs"),
    [
        ("Executive", 0),
        ("Explorer", 4),
        ("Methods & QA", 4),
    ],
)
def test_every_workspace_renders_without_exception(mode, expected_tabs):
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=30)
    if mode != "Executive":
        app.radio[0].set_value(mode)
        app.run(timeout=30)
    assert not app.exception
    assert len(app.tabs) == expected_tabs


@pytest.mark.parametrize("status", sorted(STATUS_COLORS))
def test_status_badges_pair_color_with_written_status(status):
    badge = status_badge(status)
    assert status.title() in badge
    assert f"status-{status}" in badge
    assert "status-dot" in badge


def test_ui_sources_have_no_mojibake_or_retired_dark_theme():
    root = Path(__file__).parents[2]
    source = "\n".join(
        (root / relative).read_text(encoding="utf-8")
        for relative in ("app.py", "ui/theme.py", "ui/views.py", "ui/presentation.py", "viz/style.py")
    )
    assert "Â" not in source
    assert "â€" not in source
    assert "plotly_dark" not in source
    assert "carto-darkmatter" not in source


def test_transportation_claim_language_is_bounded_and_mrs_is_secondary():
    source = (Path(__file__).parents[2] / "ui" / "views.py").read_text(encoding="utf-8")
    lowered = source.lower()
    assert "prediction" not in lowered
    assert "congestion" not in lowered
    assert "ada" not in lowered
    assert source.index("Peak access gap") < source.index("Mobility Readiness Score")


def test_theme_contains_narrow_screen_layout_rules():
    theme = (Path(__file__).parents[2] / "ui" / "theme.py").read_text(encoding="utf-8")
    assert "@media (max-width: 1000px)" in theme
    assert "@media (max-width: 640px)" in theme


def test_native_streamlit_theme_matches_the_visual_system():
    config = (Path(__file__).parents[3] / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert 'primaryColor = "#0B7169"' in config
    assert 'backgroundColor = "#F3F6F4"' in config
    assert 'textColor = "#16302F"' in config
