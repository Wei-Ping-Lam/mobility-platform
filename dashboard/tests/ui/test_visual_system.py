from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.ui.theme import status_badge
from dashboard.viz.style import STATUS_COLORS


@pytest.mark.parametrize(
    ("mode", "expected_tabs"),
    [
        ("Overview", 4),
        ("City Brief", 2),
    ],
)
def test_every_workspace_renders_without_exception(mode, expected_tabs):
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=30)
    if mode != "Overview":
        workspace = next(widget for widget in app.radio if widget.label == "Workspace")
        workspace.set_value(mode)
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
        for relative in (
            "app.py",
            "ui/theme.py",
            "ui/views.py",
            "ui/presentation.py",
            "ui/judging.py",
            "ui/pages/home.py",
            "ui/pages/overview.py",
            "ui/portfolio/context.py",
            "ui/portfolio/first_last_mile.py",
            "ui/portfolio/investments.py",
            "ui/portfolio/page.py",
            "ui/portfolio/resilience.py",
            "ui/portfolio/shared.py",
            "ui/portfolio/tables.py",
            "ui/portfolio/visitor_movement.py",
            "ui/city/traffic_plan.py",
            "viz/portfolio.py",
            "viz/style.py",
        )
    )
    assert "Â" not in source
    assert "â€" not in source
    assert "plotly_dark" not in source
    assert "carto-darkmatter" not in source


def test_transportation_claim_language_is_bounded_and_mrs_is_secondary():
    source = "\n".join(
        (Path(__file__).parents[2] / relative).read_text(encoding="utf-8")
        for relative in ("ui/views.py", "ui/pages/home.py")
    )
    lowered = source.lower()
    assert "validated prediction" not in lowered
    assert "measured congestion" not in lowered
    assert "reduces congestion" not in lowered
    assert "ada compliant" not in lowered
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


@pytest.mark.parametrize("city", sorted(HOST_CITIES))
def test_every_city_renders_in_the_action_plan(city):
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=30)
    workspace_selector = next(widget for widget in app.radio if widget.label == "Workspace")
    workspace_selector.set_value("City Brief")
    app.run(timeout=30)
    city_selector = next(widget for widget in app.selectbox if widget.label == "City focus")
    city_selector.set_value(city)
    app.run(timeout=30)
    assert not app.exception
    assert city_selector.value == city
    # The two overlap-map sub-tabs (venue access / operating) live inside a
    # collapsed expander; City Brief itself still has no top-level tab nav.
    assert {tab.label for tab in app.tabs} == {"Venue access overlap", "Operating overlap"}
