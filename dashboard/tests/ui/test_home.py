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
    assert workspace.options == ["Portfolio", "City action plan", "Scenario explorer", "Methods"]
    assert not [widget for widget in app.selectbox if widget.label in {"City focus", "Match"}]
    assert not app.multiselect
    assert not [widget for widget in app.segmented_control if widget.label == "Outcome to compare"]
    comparison = app.dataframe[0].value
    assert len(comparison) == 11
    assert set(comparison["City"]) >= {"Atlanta", "Miami", "New York/NJ"}
    assert list(comparison.columns) == [
        "City",
        "Readiness rank",
        "Combined readiness",
        "Transit proximity",
        "Heat safety",
        "Urban heat safety",
        "Venue support",
    ]
    assert comparison["Readiness rank"].notna().all()
    assert list(comparison.sort_values("Readiness rank")["City"][:1]) == ["Seattle"]
    access = app.dataframe[1].value
    traffic = app.dataframe[2].value
    climate = app.dataframe[3].value
    assert list(access.columns) == [
        "City",
        "Representative match",
        "Peak arrivals / hour",
        "Scheduled transit capacity / hour",
        "Scheduled coverage",
        "Remaining peak gap / hour",
    ]
    assert list(traffic.columns) == [
        "City",
        "Representative match",
        "Low input case",
        "Base input case",
        "High input case",
    ]
    assert list(climate.columns) == [
        "City",
        "Representative match",
        "Qualified single measure",
        "Proposed scale",
        "Net CO2e avoided (kg)",
        "Evidence quality",
    ]
    assert len(app.get("plotly_chart")) == 5
    assert [tab.label for tab in app.tabs] == [
        ":material/train: Access shortfall",
        ":material/traffic: Traffic pressure",
        ":material/eco: Climate outcome",
    ]
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "How do hosts rank on overall readiness?" in page_text
    assert "What drives the rank?" in page_text
    assert "What does each transportation task show?" in page_text
    assert page_text.index("How do hosts rank on overall readiness?") < page_text.index("What drives the rank?")
    assert page_text.index("What drives the rank?") < page_text.index("What does each transportation task show?")
    assert "Transit proximity" in page_text
    assert "Urban heat safety" in page_text
    assert "Planning evidence, not observed fan behavior" not in page_text
    assert "What the platform delivers" not in page_text
    assert "Competition outcomes and current limitations" not in page_text
    assert "Priority case:" not in page_text


def test_portfolio_keeps_composite_scenarios_out_of_the_decision_view():
    app = _app()
    assert not [widget for widget in app.selectbox if widget.label == "Scenario package"]
    page_text = "\n".join(str(element.value) for element in app.markdown)
    captions = "\n".join(str(element.value) for element in app.caption)
    assert "Median scheduled coverage" in page_text
    assert "Median base traffic pressure" in page_text
    assert "Median modeled climate benefit" in page_text
    assert "not measured roadway congestion" in captions
    assert "not an observed reduction" in captions
    assert "Single-measure efficiency" not in page_text
    assert "Median comparison cost / passenger" not in page_text
    assert "Operational Package" not in page_text
    assert "Capital Package" not in page_text


def test_priority_case_drills_into_the_same_city_explorer():
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
    next(button for button in app.button if button.label == "Explore New York/NJ maps and scenarios").click()
    app.run(timeout=60)
    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Explorer"
    city_focus = next(widget for widget in app.selectbox if widget.label == "City focus")
    assert city_focus.value == "New York/NJ"
    assert next(widget for widget in app.selectbox if widget.label == "Match")
    app.session_state["explorer_section"] = "Map & layers"
    app.run(timeout=60)
    traffic_scenario = next(widget for widget in app.segmented_control if widget.label == "Traffic scenario")
    assert traffic_scenario.value == "Operational Package"
    map_layers = next(widget for widget in app.multiselect if widget.label == "Map layers")
    assert "traffic_pressure" in map_layers.value


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


def test_overview_navigation_opens_methods():
    app = _app()
    next(button for button in app.button if button.label == "Review methods, assumptions, and sources").click()
    app.run(timeout=60)
    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Methods & QA"
    assert len(app.tabs) == 4
    assert max(len(table.value.columns) for table in app.dataframe) <= 11


def test_boston_explorer_surfaces_real_traffic_pressure_values():
    app = _app()
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    workspace.set_value("Explorer")
    app.run(timeout=60)
    city_focus = next(widget for widget in app.selectbox if widget.label == "City focus")
    city_focus.set_value("Boston")
    app.run(timeout=60)
    app.session_state["explorer_section"] = "Map & layers"
    app.run(timeout=60)

    assert not app.exception
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Baseline vehicle pressure" in page_text
    assert "20,909 trips" in page_text
    assert "Operational Package pressure" in page_text
    assert "19,497 trips" in page_text
    assert "-1,411 trips (-6.8%)" in page_text

    next(widget for widget in app.radio if widget.label == "Workspace").set_value("Methods & QA")
    app.run(timeout=60)
    next(widget for widget in app.radio if widget.label == "Workspace").set_value("Explorer")
    app.run(timeout=60)
    assert next(widget for widget in app.selectbox if widget.label == "City focus").value == "Boston"
