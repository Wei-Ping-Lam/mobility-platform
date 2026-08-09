from streamlit.testing.v1 import AppTest


def _app() -> AppTest:
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=60)
    assert not app.exception
    return app


def test_default_landing_page_starts_with_all_city_portfolio():
    app = _app()
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Overview"
    assert workspace.options == ["Portfolio", "City action plan"]
    assert not [widget for widget in app.selectbox if widget.label in {"City focus", "Match"}]
    assert not app.multiselect
    assert not [widget for widget in app.segmented_control if widget.label == "Outcome to compare"]
    comparison = app.dataframe[0].value
    assert len(comparison) == 11
    assert set(comparison["City"]) >= {"Atlanta", "Miami", "New York/NJ"}
    assert list(comparison.columns) == [
        "City",
        "Readiness rank",
        "Readiness score",
        "Representative match",
        "Baseline scheduled coverage",
        "Stress-test coverage",
        "Remaining stressed gap / hour",
    ]
    assert comparison["Readiness rank"].notna().all()
    assert list(comparison.sort_values("Readiness rank")["City"][:1]) == ["Seattle"]
    assert len(app.get("plotly_chart")) == 3
    assert [tab.label for tab in app.tabs] == [
        ":material/health_and_safety: Resilience",
        ":material/route: Visitor movement",
        ":material/transfer_within_a_station: First/last mile",
        ":material/construction: Investments & strategies",
        ":material/monitoring: Outcomes",
    ]
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Compare every Track 1 objective" in page_text
    assert "How do hosts rank, and how much scheduled coverage survives a common stress?" in page_text
    assert "Transportation stress test" in page_text
    assert "City focus" not in page_text


def test_portfolio_tabs_make_every_track1_objective_explicit():
    app = _app()
    assert not [widget for widget in app.selectbox if widget.label == "Scenario package"]

    app.session_state["track1_objective"] = ":material/route: Visitor movement"
    app.run(timeout=60)
    movement = app.dataframe[0].value
    assert {
        "Hosted matches",
        "Peak forecast stage",
        "Non-host-market attendees",
        "International / unobserved share",
        "Scheduled transit demand",
        "Arrival peak base",
        "Departure peak base",
        "Validation status",
    }.issubset(movement.columns)
    assert next(
        widget for widget in app.segmented_control if widget.label == "Forecast view"
    ).value == "Origin mix"
    captions = "\n".join(str(element.value) for element in app.caption)
    assert "commercial customer origins shape only the U.S. prior" in captions
    assert "Neither is observed FIFA fan behavior" in captions

    app.session_state["track1_objective"] = ":material/transfer_within_a_station: First/last mile"
    app.run(timeout=60)
    access = app.dataframe[0].value
    assert {"Peak direction", "Zero-capacity matches", "Network walk (m)", "Accessibility audit"}.issubset(access.columns)

    app.session_state["track1_objective"] = ":material/construction: Investments & strategies"
    app.run(timeout=60)
    actions = app.dataframe[0].value
    assert actions["Priority screen"].nunique() >= 3
    assert {"Why this bottleneck", "Delivery owner", "Dependencies"}.issubset(actions.columns)

    app.session_state["track1_objective"] = ":material/monitoring: Outcomes"
    app.run(timeout=60)
    outcomes = app.dataframe[0].value
    assert {"Peak passengers addressed / hour", "Venue-area vehicle trips avoided", "Net CO2e avoided (kg)"}.issubset(outcomes.columns)
    assert next(widget for widget in app.segmented_control if widget.label == "Outcome to compare").value == "Access"
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Single-measure efficiency" not in page_text
    assert "Operational Package" not in page_text
    assert "Capital Package" not in page_text


def test_priority_case_drills_into_the_same_city_action_plan():
    app = _app()
    explore = next(button for button in app.button if button.label == "Open New York/NJ action plan")
    explore.click()
    app.run(timeout=60)
    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "City Brief"
    city_focus = next(widget for widget in app.selectbox if widget.label == "City focus")
    assert city_focus.value == "New York/NJ"
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "New York/NJ: from access gap to action" in page_text
    assert "Competition evidence" not in page_text
    assert "Required deliverables" not in page_text
    assert len(app.get("plotly_chart")) == 1
    assert len(app.dataframe) == 2
    investment_screen = app.dataframe[1].value
    assert set(investment_screen["Decision"]) >= {"Screen first"}
    assert "Proposed scale" in investment_screen
    composite_toggle = next(widget for widget in app.toggle if widget.label == "Show advanced composite model tests")
    assert composite_toggle.value is False
    assert not [
        button
        for button in app.button
        if "maps and scenarios" in button.label.lower()
    ]


def test_advanced_composites_define_every_modeled_quantity():
    app = _app()
    next(widget for widget in app.radio if widget.label == "Workspace").set_value("City Brief")
    app.run(timeout=60)
    next(widget for widget in app.toggle if widget.label == "Show advanced composite model tests").set_value(True)
    app.run(timeout=60)

    assert not app.exception
    composites = app.dataframe[2].value
    operational = composites[composites["Composite"] == "Operational Package"].iloc[0]
    capital = composites[composites["Composite"] == "Capital Package"].iloc[0]
    assert operational["What it combines"] == (
        "12 shuttle buses/hour; 6 added transit departures/hour; 20% peak arrivals shifted"
    )
    assert "1500 park-and-ride spaces" in capital["What it combines"]
    assert "19 feeder departures/hour" in capital["What it combines"]


def test_deferred_workspaces_have_no_navigation_or_calls_to_action():
    app = _app()
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.options == ["Portfolio", "City action plan"]
    assert not [
        button
        for button in app.button
        if "methods" in button.label.lower() or "scenario" in button.label.lower()
    ]


def test_stale_deferred_workspace_state_returns_to_portfolio():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "Explorer"
    app.run(timeout=60)

    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Overview"
