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
    assert not [widget for widget in app.radio if widget.label == "City Focus"]
    assert not [widget for widget in app.selectbox if widget.label == "Match"]
    assert not app.multiselect
    assert not app.dataframe
    assert len(app.get("plotly_chart")) == 3
    assert [tab.label for tab in app.tabs] == [
        ":material/health_and_safety: Overview",
        ":material/route: Visitor movement",
        ":material/transfer_within_a_station: Venue access",
    ]
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Host City Readiness Ranking" in page_text
    assert "City Focus" not in page_text
    # Comparison settings moved from the sidebar into the Overview tab.
    assert any(e.label.startswith("Comparison settings") for e in app.get("expander"))
    assert next(w for w in app.selectbox if w.label == "Weight profile").value == "balanced"


def test_portfolio_tabs_make_cross_city_objectives_explicit():
    app = _app()
    assert not [widget for widget in app.selectbox if widget.label == "Scenario package"]

    app.session_state["track1_objective"] = ":material/route: Visitor movement"
    app.run(timeout=60)
    # The movement table (exact values) is whichever dataframe actually has its columns,
    # independent of which forecast view is currently selected.
    movement = next(df.value for df in app.dataframe if "Hosted matches" in df.value.columns)
    assert {
        "Hosted matches",
        "Peak forecast stage",
        "Non-host-market attendee-visits (base)",
        "International / unobserved share",
        "Scheduled transit demand",
        "Arrival peak base",
        "Departure peak base",
        "Validation status",
    }.issubset(movement.columns)
    forecast_view = next(
        widget for widget in app.segmented_control if widget.label == "Forecast view"
    )
    assert forecast_view.value == "Peak timing"
    assert forecast_view.options == ["Peak timing", "Transportation Mode Mix", "Attendee Origin"]
    planner_city = next(w for w in app.selectbox if w.label == "Select host city")
    assert planner_city.value
    captions = "\n".join(str(element.value) for element in app.caption)
    assert "not calibrated to ticket scans" in captions

    app.session_state["track1_objective"] = ":material/transfer_within_a_station: Venue access"
    app.run(timeout=60)
    access = next(df.value for df in app.dataframe if "Peak direction" in df.value.columns)
    takeaway = next(element.value for element in app.info if element.value.startswith("Access takeaway:"))
    assert "Atlanta stands out for strong access but a low sustainability score" in takeaway
    assert not any("First/last-mile takeaway:" in element.value for element in app.info)
    assert {"Peak direction", "Zero-capacity matches", "Network walk (m)", "Accessibility audit"}.issubset(
        access.columns
    )


def test_city_action_plan_tabs_split_overview_transit_and_traffic_solutions():
    app = _app()
    next(widget for widget in app.radio if widget.label == "Workspace").set_value("City Brief")
    app.run(timeout=60)
    assert [tab.label for tab in app.tabs] == [
        ":material/location_city: City overview",
        ":material/directions_bus: Transit solution",
        ":material/traffic: Traffic management solution",
    ]

    # Shared header carries demand; the city problem follows the mobility summary.
    page_text = "\n".join(str(element.value) for element in app.markdown)
    problem_index = page_text.index("specific problem")
    summary_index = page_text.index("Mobility summary")
    readiness_index = page_text.index("Readiness Scores")
    assert summary_index < problem_index < readiness_index
    assert "Estimated peak movement demand" in page_text
    header = next(str(element.value) for element in app.markdown if "hero-shell" in str(element.value) and "City action plan" in str(element.value))
    assert "Estimated peak movement demand" in header
    assert "Base attendance scenario" in header
    assert page_text.count("Estimated peak movement demand") == 1
    assert "**Traffic**" in page_text

    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Recommended first action" in page_text
    assert "Estimated peak movement demand" in page_text
    assert "Projected impact" in page_text
    assert "Compare transit solutions" in page_text
    assert "How the modeled options compare" not in page_text
    comparison = next(df.value for df in app.dataframe if "Solution" in df.value.columns)
    assert comparison["Solution"].tolist() == [
        "Dedicated event bus/shuttle lanes", "Remote park-and-ride + shuttle hubs",
        "Increase rail/transit frequency", "Electric shuttle/bus fleet",
    ]
    assert "Passengers addressed / match" in page_text
    assert "Net CO2e avoided / match" in page_text
    assert "Net vehicle-miles saved / match" in page_text
    assert "Estimated first-event cost" in page_text
    assert "Where this recommendation plays out" not in page_text
    caption_text = "\n".join(str(element.value) for element in app.caption)
    assert "Illustrative planning estimate for this action" in caption_text
    assert "The real place(s) this recommendation names" not in caption_text
    assert "doesn't center on one specific" not in caption_text
    lens_table = next(
        df.value for df in app.dataframe if "Net CO2e avoided (emissions)" in df.value.columns
    )
    assert {
        "Peak passengers (access)",
        "Net CO2e avoided (emissions)",
        "Net VMT avoided (traffic)",
    }.issubset(lens_table.columns)
    assert not [widget for widget in app.toggle if widget.label != "Show advanced composite model tests"]
    # Atlanta has no recommendation-specific mapped locations, so only the comparison renders.
    assert not app.slider
    assert len(app.get("plotly_chart")) == 1

    app.session_state["city_brief_objective"] = ":material/traffic: Traffic management solution"
    app.run(timeout=60)
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Recommended traffic management solution" in page_text
    assert "How this plan relates to access, emissions, and traffic" not in page_text
    assert not any("Engine-derived transit-bridging" in expander.label for expander in app.expander)
    hotspots = next(
        df.value for df in app.dataframe if "What happens here" in df.value.columns
    )
    assert not hotspots.empty
    assert hotspots["Source"].map(lambda url: str(url).startswith("https://")).all()

    next(widget for widget in app.radio if widget.label == "City Focus").set_value("Boston")
    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 2
    assert any("Providence Station" in str(element.value) for element in app.caption)


def test_no_nearby_departures_notice_is_below_city_map():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "City Brief"
    app.session_state["selected_city_context"] = "New York/NJ"
    app.session_state["city_focus"] = "New York/NJ"
    app.run(timeout=60)

    assert not app.exception
    notice = "No nearby event-window departures"
    columns = app.get("column")
    map_column = next(column for column in columns if column.get("plotly_chart"))
    assert sum(notice in element.value for element in app.markdown) == 1
    assert any(notice in element.value for element in map_column.markdown)
    children = list(map_column.children.values())
    map_index = next(i for i, element in enumerate(children) if element.type == "plotly_chart")
    notice_index = next(
        i for i, element in enumerate(children)
        if element.type == "markdown" and notice in element.value
    )
    assert map_index < notice_index
    assert not any("specific problem" in element.value for element in map_column.markdown)


def test_advanced_composites_define_every_modeled_quantity():
    app = _app()
    next(widget for widget in app.radio if widget.label == "Workspace").set_value("City Brief")
    app.run(timeout=60)
    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    next(widget for widget in app.toggle if widget.label == "Show advanced composite model tests").set_value(True)
    # st.tabs' selection (set above via session_state, not a real tab click) isn't
    # preserved by AppTest across an unrelated widget interaction's rerun, so
    # re-assert it immediately before the run that should still show this tab.
    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)

    assert not app.exception
    composites = next(frame.value for frame in app.dataframe if "Composite" in frame.value.columns)
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
        button for button in app.button if "methods" in button.label.lower() or "scenario" in button.label.lower()
    ]


def test_stale_deferred_workspace_state_returns_to_portfolio():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "Explorer"
    app.run(timeout=60)

    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Overview"
