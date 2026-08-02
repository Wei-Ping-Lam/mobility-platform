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
    assert not [widget for widget in app.selectbox if widget.label in {"City focus", "Match"}]
    city_selection = next(widget for widget in app.multiselect if widget.label == "Filter cities (leave empty to show all 11)")
    assert city_selection.value == []
    comparison = app.dataframe[0].value
    assert len(comparison) == 11
    assert set(comparison["City"]) >= {"Atlanta", "Miami", "New York/NJ"}
    assert comparison["Readiness rank"].notna().all()
    assert list(comparison.sort_values("Readiness rank")["City"][:1]) == ["Seattle"]
    assert len(app.get("plotly_chart")) == 2
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "See which cities are most ready—and why" in page_text
    assert "Selected package outcomes" in page_text
    assert "Planning evidence, not observed fan behavior" not in page_text
    assert "What the platform delivers" not in page_text
    assert "Competition outcomes and current limitations" not in page_text
    assert "Priority case:" not in page_text


def test_package_selection_changes_visible_outcomes_without_changing_readiness():
    app = _app()
    package = next(widget for widget in app.selectbox if widget.label == "Scenario package")
    operational = app.dataframe[0].value.copy()
    package.set_value("Capital Package")
    app.run(timeout=60)
    assert not app.exception
    capital = app.dataframe[0].value
    assert operational["Readiness score"].equals(capital["Readiness score"])
    assert (capital["Traffic pressure after package (vehicle trips)"] < operational["Traffic pressure after package (vehicle trips)"]).all()
    assert (capital["Net CO2e avoided (kg)"] > operational["Net CO2e avoided (kg)"]).all()
    comparable_costs = capital["Package cost/passenger addressed"].notna() & operational["Package cost/passenger addressed"].notna()
    assert comparable_costs.any()
    assert (
        capital.loc[comparable_costs, "Package cost/passenger addressed"]
        > operational.loc[comparable_costs, "Package cost/passenger addressed"]
    ).all()


def test_city_selection_drills_into_the_same_city_explorer():
    app = _app()
    city_selection = next(widget for widget in app.multiselect if widget.label == "Filter cities (leave empty to show all 11)")
    city_selection.set_value(["Atlanta", "Miami", "Seattle", "Dallas", "Boston"])
    app.run(timeout=60)
    assert len(app.dataframe[0].value) == 5
    drill_city = next(widget for widget in app.selectbox if widget.label == "City to investigate")
    drill_city.set_value("Atlanta")
    app.run(timeout=60)
    explore = next(button for button in app.button if button.label == "Open city brief")
    explore.click()
    app.run(timeout=60)
    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "City Brief"
    city_focus = next(widget for widget in app.selectbox if widget.label == "City focus")
    assert city_focus.value == "Atlanta"
    page_text = "\n".join(str(element.value) for element in app.markdown)
    assert "Priority case: Atlanta" in page_text
    next(button for button in app.button if button.label == "Open Atlanta maps and match details").click()
    app.run(timeout=60)
    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Explorer"
    city_focus = next(widget for widget in app.selectbox if widget.label == "City focus")
    assert city_focus.value == "Atlanta"
    assert next(widget for widget in app.selectbox if widget.label == "Match")


def test_overview_navigation_opens_full_comparison():
    app = _app()
    next(button for button in app.button if button.label == "Open full city comparison").click()
    app.run(timeout=60)
    assert not app.exception
    workspace = next(widget for widget in app.radio if widget.label == "Workspace")
    assert workspace.value == "Compare Cities"
    assert len(app.tabs) == 3
