import pandas as pd

from dashboard.ui.presentation import CityDecisionView, ScenarioView
from dashboard.ui.views import _layer_map, _traffic_pressure_envelope, _traffic_pressure_table
from dashboard.viz.portfolio import (
    portfolio_access_chart,
    portfolio_climate_chart,
    portfolio_traffic_chart,
    readiness_components_chart,
)


def _portfolio_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "city": "Atlanta",
                "lat": 33.755,
                "lon": -84.401,
                "strict_score": 62.0,
                "strict_rank": 2,
                "peak_demand_pph": 20_000,
                "capacity_qualified_gap_pph": 12_000,
                "baseline_vehicle_trips_low": 11_000,
                "baseline_vehicle_trips_base": 12_000,
                "baseline_vehicle_trips_high": 13_000,
                "top_net_co2e_kg": 1_200,
                "top_cost_per_passenger": 85,
                "lowest_cost_intervention": "Added transit frequency",
                "top_scope": "Add 6 transit departures per hour in the event window",
                "top_evidence_quality": "medium",
                "representative_match_id": "M001",
                "qualified_interventions": "Shuttle service",
                "screening_confidence": "medium",
            },
            {
                "city": "Seattle",
                "lat": 47.595,
                "lon": -122.332,
                "strict_score": 78.0,
                "strict_rank": 1,
                "peak_demand_pph": 20_000,
                "capacity_qualified_gap_pph": 5_000,
                "baseline_vehicle_trips_low": 7_000,
                "baseline_vehicle_trips_base": 8_000,
                "baseline_vehicle_trips_high": 9_000,
                "top_net_co2e_kg": 2_100,
                "top_cost_per_passenger": 70,
                "lowest_cost_intervention": "Added transit frequency",
                "top_scope": "Add 6 transit departures per hour in the event window",
                "top_evidence_quality": "medium",
                "representative_match_id": "M002",
                "qualified_interventions": "Added transit frequency",
                "screening_confidence": "high",
            },
        ]
    )


def test_portfolio_access_chart_separates_scheduled_capacity_from_remaining_gap() -> None:
    figure = portfolio_access_chart(_portfolio_frame())

    assert [trace.name for trace in figure.data] == ["Scheduled transit capacity", "Remaining peak gap"]
    assert list(figure.data[0].y) == ["Seattle", "Atlanta"]
    assert list(figure.data[0].x) == [15_000, 8_000]
    assert list(figure.data[1].x) == [5_000, 12_000]
    assert list(figure.data[1].text) == ["75% covered", "40% covered"]
    assert figure.layout.barmode == "stack"


def test_readiness_components_chart_exposes_all_four_defined_criteria() -> None:
    metrics = pd.DataFrame(
        [
            {
                "city": "Atlanta",
                "transit_score": 71,
                "transit_status": "observed",
                "heat_score": 74,
                "heat_status": "derived",
                "uhi_score": 30,
                "uhi_status": "derived",
                "access_score": 72,
                "access_status": "derived",
            },
            {
                "city": "Seattle",
                "transit_score": 100,
                "transit_status": "observed",
                "heat_score": 96,
                "heat_status": "derived",
                "uhi_score": 30,
                "uhi_status": "derived",
                "access_score": 100,
                "access_status": "derived",
            },
        ]
    )

    figure = readiness_components_chart(metrics, ["Atlanta", "Seattle"])

    assert list(figure.data[0].x) == ["Transit<br>proximity", "Heat<br>safety", "Urban heat<br>safety", "Venue<br>support"]
    assert list(figure.data[0].y) == ["Atlanta", "Seattle"]
    assert list(figure.data[0].z[0]) == [71, 74, 30, 72]


def test_portfolio_traffic_chart_uses_baseline_trip_cases_without_congestion_claims() -> None:
    figure = portfolio_traffic_chart(_portfolio_frame())

    assert list(figure.data[0].y) == ["Seattle", "Atlanta"]
    assert list(figure.data[0].x) == [8_000, 12_000]
    assert list(figure.data[0].error_x.array) == [1_000, 1_000]
    assert list(figure.data[0].error_x.arrayminus) == [1_000, 1_000]
    assert "not roadway congestion" in figure.data[0].hovertemplate


def test_portfolio_climate_chart_compares_the_common_single_measure() -> None:
    figure = portfolio_climate_chart(_portfolio_frame())

    assert list(figure.data[0].y) == ["Atlanta", "Seattle"]
    assert list(figure.data[0].x) == [1_200, 2_100]
    assert list(figure.data[0].customdata[:, 1]) == ["Added transit frequency", "Added transit frequency"]
    assert "Base-case net CO2e avoided" in figure.data[0].hovertemplate


def test_traffic_layer_uses_a_visible_change_label_instead_of_overlapping_markers() -> None:
    decision = CityDecisionView(
        city="Atlanta",
        venue="Mercedes-Benz Stadium",
        lat=33.755,
        lon=-84.401,
        matches=(),
        movements={},
        access_gaps={},
        scenarios={},
        recommendations={},
        metric={},
    )
    baseline = ScenarioView(
        name="Baseline",
        status="scenario",
        venue_vehicle_trips_low=9_000,
        venue_vehicle_trips_base=10_000,
        venue_vehicle_trips_high=11_000,
    )
    operational = ScenarioView(
        name="Operational Package",
        status="scenario",
        venue_vehicle_trips_low=6_000,
        venue_vehicle_trips_base=7_000,
        venue_vehicle_trips_high=8_000,
    )

    figure, readiness = _layer_map(
        decision,
        {},
        ["traffic_pressure"],
        traffic_baseline=baseline,
        traffic_scenario=operational,
    )
    traffic_table = _traffic_pressure_table(baseline, operational)

    assert [trace.name for trace in figure.data] == ["Operational Package traffic pressure", "Venue"]
    assert list(figure.data[0].text) == ["-30% trips"]
    assert figure.data[0].mode == "markers+text"
    traffic_readiness = readiness[readiness["Layer"] == "Modeled traffic pressure"].iloc[0]
    assert traffic_readiness["Status"] == "Scenario"
    assert traffic_readiness["Mapped records"] == "1"
    assert "10,000 baseline to 7,000 trips (-3,000)" in traffic_readiness["Meaning"]
    assert list(traffic_table["Base input case"]) == [10_000, 7_000]
    assert list(traffic_table["Change from baseline"]) == [0, -3_000]


def test_traffic_hover_uses_the_actual_case_envelope() -> None:
    scenario = ScenarioView(
        name="Operational Package",
        venue_vehicle_trips_low=10_050,
        venue_vehicle_trips_base=10_699,
        venue_vehicle_trips_high=10_465,
    )

    assert _traffic_pressure_envelope(scenario) == "10,050 to 10,699 trips across input cases"


def test_gtfs_shapes_share_one_legend_entry_without_dropping_geometry() -> None:
    decision = CityDecisionView(
        city="Boston",
        venue="Gillette Stadium",
        lat=42.0909,
        lon=-71.2643,
        matches=(),
        movements={},
        access_gaps={},
        scenarios={},
        recommendations={},
        metric={},
    )
    artifacts = {
        "map_layers": {
            "Boston": {
                "gtfs_routes": [
                    {
                        "agency": "MBTA",
                        "route_name": "Providence/Stoughton Line",
                        "coordinates": [[-71.30, 42.10], [-71.20, 42.05]],
                    },
                    {
                        "agency": "MBTA",
                        "route_name": "Franklin/Foxboro Line",
                        "coordinates": [[-71.40, 42.20], [-71.26, 42.09]],
                    },
                ]
            }
        }
    }

    figure, _ = _layer_map(decision, artifacts, ["gtfs_routes"])
    route_traces = [trace for trace in figure.data if trace.legendgroup == "gtfs_routes"]

    assert len(route_traces) == 1
    assert route_traces[0].name == "Event-valid GTFS routes"
    assert route_traces[0].showlegend is True
    assert list(route_traces[0].text) == [
        "Providence/Stoughton Line | MBTA",
        "Providence/Stoughton Line | MBTA",
        None,
        "Franklin/Foxboro Line | MBTA",
        "Franklin/Foxboro Line | MBTA",
        None,
    ]
    assert list(route_traces[0].lat).count(None) == 2


def test_walking_shapes_share_one_legend_entry_without_losing_hover_detail() -> None:
    decision = CityDecisionView(
        city="New York/NJ",
        venue="MetLife Stadium",
        lat=40.8135,
        lon=-74.0745,
        matches=(),
        movements={},
        access_gaps={},
        scenarios={},
        recommendations={},
        metric={},
    )
    artifacts = {
        "map_layers": {
            "New York/NJ": {
                "walk": [
                    {"name": "Network path to event-relevant stop", "coordinates": [[-74.08, 40.81], [-74.07, 40.82]]},
                    {"minutes": 15, "coordinates": [[-74.09, 40.80], [-74.06, 40.80]]},
                    {"minutes": 30, "coordinates": [[-74.10, 40.79], [-74.05, 40.79]]},
                ]
            }
        }
    }

    figure, _ = _layer_map(decision, artifacts, ["walk"])
    walk_traces = [trace for trace in figure.data if trace.legendgroup == "walk"]

    assert len(walk_traces) == 3
    assert sum(bool(trace.showlegend) for trace in walk_traces) == 1
    assert {trace.name for trace in walk_traces} == {"Walking network"}
    assert {str(trace.text[0]) for trace in walk_traces} == {
        "Network path to event-relevant stop",
        "15-minute isochrone",
        "30-minute isochrone",
    }
