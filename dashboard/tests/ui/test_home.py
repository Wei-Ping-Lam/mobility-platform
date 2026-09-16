import json

from streamlit.testing.v1 import AppTest


def _app() -> AppTest:
    app = AppTest.from_file("dashboard/app.py")
    app.run(timeout=60)
    assert not app.exception
    return app


def test_boston_dedicated_service_fares_render_as_text():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "City Brief"
    app.session_state["selected_city_context"] = "Boston"
    app.session_state["city_focus"] = "Boston"
    app.run(timeout=60)

    assert not app.exception
    description = next(element.value for element in app.markdown if "**Dedicated service**" in element.value)
    assert r"\$80 round-trip stadium trains" in description
    assert r"\$95 round-trip express buses" in description


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
    assert {slider.label: slider.value for slider in app.slider} == {
        "First/last-mile access": 0.30,
        "Traffic management": 0.30,
        "Heat safety": 0.25,
        "Venue support": 0.15,
    }


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
    assert "Readiness rank #" in header
    assert page_text.count("Estimated peak movement demand") == 1
    assert "**Traffic**" in page_text

    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Recommended first action" in page_text
    assert "Estimated peak movement demand" in page_text
    assert "Projected impact" in page_text
    assert "Compare transit solutions" not in page_text
    assert "High-investment, High-impact alternative" not in page_text
    assert "How the modeled options compare" not in page_text
    assert "Passengers addressed / match" in page_text
    assert "Net CO2e avoided / match" in page_text
    assert "Net vehicle-miles saved / match" in page_text
    assert "Estimated first-event cost" in page_text
    assert "Where this recommendation plays out" not in page_text
    caption_text = "\n".join(str(element.value) for element in app.caption)
    assert "Illustrative planning estimate for this action" not in caption_text
    assert "Recommended actions require positive savings under the stated operating conditions" not in caption_text
    assert any(expander.label == "Estimate assumptions and scenario range" for expander in app.expander)
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
    assert not app.toggle
    # Atlanta needs neither a recommendation map nor a high-capital alternative.
    assert not app.slider
    assert len(app.get("plotly_chart")) == 0

    app.session_state["city_brief_objective"] = ":material/traffic: Traffic management solution"
    app.run(timeout=60)
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Recommended traffic management solution" in page_text
    assert "How this plan relates to access, emissions, and traffic" not in page_text
    assert not any("Engine-derived transit-bridging" in expander.label for expander in app.expander)
    controls = next(element.value for element in app.markdown if "<table class='traffic-controls-table'>" in element.value)
    assert "What happens here" in controls and "https://" in controls
    assert "white-space: normal; overflow-wrap: anywhere" in page_text

    next(widget for widget in app.radio if widget.label == "City Focus").set_value("Boston")
    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 0
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "High-investment, High-impact alternative" in page_text
    assert "Estimated capital cost" in page_text
    assert "Potential passengers addressed / match" in page_text
    capital_cards = [element.value for element in app.markdown if "metric-card" in element.value and (
        "Estimated capital cost" in element.value or "Potential passengers addressed / match" in element.value
    )]
    assert len(capital_cards) == 2
    assert all("status-scenario" in card and "status-unavailable" not in card for card in capital_cards)
    assert "Offer fare support on existing stadium trains and express buses" in page_text
    assert "already included direct Rhode Island express buses" in page_text
    assert r"\$80 train and \$95 bus" in page_text
    assert "run a reserved electric Providence-to-Foxborough" not in page_text
    assert not any("Providence Station" in str(element.value) for element in app.caption)
    assert any("Fare-credit assumption:" in str(element.value) for element in app.caption)
    fare_note = next(element.value for element in app.caption if "Fare-credit assumption:" in element.value)
    assert r"\$20" in fare_note
    budget_note = next(element.value for element in app.markdown if "Base non-bus operating allowance:" in element.value)
    assert r"\$2K" in budget_note and r"\$0" in budget_note

    next(widget for widget in app.radio if widget.label == "City Focus").set_value("Dallas")
    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert any("Victory Station" in str(element.value) for element in app.caption)


def test_sf_recommendation_targets_approved_detours_not_new_construction():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "City Brief"
    app.session_state["selected_city_context"] = "San Francisco"
    app.session_state["city_focus"] = "San Francisco"
    app.run(timeout=60)
    assert not app.exception
    page_text = "\n".join(element.value for element in app.markdown)
    assert "some visitors and local residents" in page_text
    assert "two-mile" not in page_text

    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)
    assert not app.exception
    page_text = "\n".join(element.value for element in app.markdown)
    assert "Improve wayfinding and crossing guidance on the approved" in page_text
    assert "Recommended actions" in page_text
    assert "Improve post-match transfers at Mountain View and Milpitas" in page_text
    assert "VTA already planned extra service and transit ambassadors" in page_text
    assert any(
        "Detour improvements only. Transfer-improvement benefits and costs are not yet estimated." in element.value
        for element in app.caption
    )
    assert "Build a permanent" not in page_text
    assert "CO2e savings are conditional" in page_text
    assert len(app.get("plotly_chart")) == 0


def test_city_map_omits_service_screen_and_no_departures_notice():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "City Brief"
    app.session_state["selected_city_context"] = "New York/NJ"
    app.session_state["city_focus"] = "New York/NJ"
    app.run(timeout=60)

    assert not app.exception
    notice = "No nearby event-window departures"
    columns = app.get("column")
    map_column = next(column for column in columns if column.get("plotly_chart"))
    assert not any(notice in element.value for element in app.markdown)
    assert not any("The pinned schedule contains no departures" in element.value for element in app.markdown)
    assert not any("specific problem" in element.value for element in map_column.markdown)
    spec = json.loads(map_column.get("plotly_chart")[0].proto.spec)
    assert not any(trace.get("name") == "Half-mile service screen" for trace in spec["data"])
    rail = next(trace for trace in spec["data"] if trace["name"] == "Meadowlands Rail Line")
    stations = next(trace for trace in spec["data"] if trace["name"] == "Rail connection stations")
    assert stations["text"] == ["Secaucus Junction", "Meadowlands (Sports Complex)"]
    assert len(rail["lat"]) > 10
    assert abs(rail["lat"][0] - 40.813053) < 0.001
    assert abs(rail["lat"][-2] - 40.761188) < 0.001
    assert 40.77 < spec["layout"]["map"]["center"]["lat"] < 40.80
    assert spec["layout"]["height"] == 460
    assert not any(trace.get("legendgroup") == "road_closed" for trace in spec["data"])


def test_documented_dallas_closures_are_visible_in_overview_and_traffic_maps():
    app = AppTest.from_file("dashboard/app.py")
    app.session_state["workspace"] = "City Brief"
    app.session_state["selected_city_context"] = "Dallas"
    app.session_state["city_focus"] = "Dallas"
    app.run(timeout=60)
    assert not app.exception
    spec = json.loads(app.get("plotly_chart")[0].proto.spec)
    closures = [trace for trace in spec["data"] if trace.get("legendgroup") == "road_closed"]
    assert len(closures) == 2
    assert all(trace["line"]["color"] == "#C9343D" for trace in closures)
    app.session_state["city_brief_objective"] = ":material/traffic: Traffic management solution"
    app.run(timeout=60)
    assert not app.exception
    spec = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert sum(trace.get("legendgroup") == "road_closed" for trace in spec["data"]) == 2
    assert any("Published 2026 event plans, not live status" in element.value for element in app.caption)


def test_advanced_composite_model_tests_are_not_displayed():
    app = _app()
    next(widget for widget in app.radio if widget.label == "Workspace").set_value("City Brief")
    app.run(timeout=60)
    app.session_state["city_brief_objective"] = ":material/directions_bus: Transit solution"
    app.run(timeout=60)

    assert not app.exception
    assert not app.toggle
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Composite scenario sensitivity" not in page_text
    assert "Tournament sensitivity" not in page_text
    assert not any("Composite" in frame.value.columns for frame in app.dataframe)
    assert not any(expander.label == "Exact composite outcome table" for expander in app.expander)


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
