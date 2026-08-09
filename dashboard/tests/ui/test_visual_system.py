import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.ui.theme import status_badge
from dashboard.viz.style import STATUS_COLORS


@pytest.mark.parametrize(
    ("mode", "expected_tabs"),
    [
        ("Overview", 5),
        ("City Brief", 0),
        ("Explorer", 4),
        ("Methods & QA", 4),
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
def test_every_city_and_match_renders_across_workspaces(city):
    schedule_path = Path(__file__).parents[3] / "data" / "snapshots" / "fifa" / "fifa_2026_us_schedule.json"
    events = json.loads(schedule_path.read_text(encoding="utf-8"))["events"]
    match_ids = [event["match_id"] for event in events if event["city"] == city]

    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=30)
    workspace_selector = next(widget for widget in app.radio if widget.label == "Workspace")
    workspace_selector.set_value("Explorer")
    app.run(timeout=30)
    city_selector = next(widget for widget in app.selectbox if widget.label == "City focus")
    city_selector.set_value(city)
    app.run(timeout=30)
    assert not app.exception

    for match_id in match_ids:
        match_selector = next(widget for widget in app.selectbox if widget.label == "Match")
        match_selector.set_value(match_id)
        app.run(timeout=30)
        assert not app.exception, f"{city} {match_id} failed Explorer AppTest"
        assert len(app.tabs) == 4

    workspace_selector = next(widget for widget in app.radio if widget.label == "Workspace")
    workspace_selector.set_value("Methods & QA")
    app.run(timeout=30)
    assert not app.exception
    assert len(app.tabs) == 4
