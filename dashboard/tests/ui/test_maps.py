import pandas as pd

from dashboard.ui.presentation import CityDecisionView, ScenarioView
from dashboard.ui.views import _layer_map, _traffic_pressure_envelope, _traffic_pressure_table
from dashboard.viz.portfolio import (
    portfolio_access_chart,
    portfolio_actions_chart,
    portfolio_climate_chart,
    portfolio_gap_quadrant_chart,
    portfolio_movement_chart,
    portfolio_package_benefit_chart,
    portfolio_resilience_chart,
    portfolio_stop_density_chart,
    portfolio_traffic_chart,
    portfolio_transit_capacity_chart,
    portfolio_visitor_forecast_chart,
    readiness_components_chart,
)
from dashboard.viz.strategy_overlap import access_overlap_map, operating_overlap_map


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
                "scheduled_transit_capacity_pph": 8_000,
                "scheduled_coverage_pct": 40.0,
                "stress_coverage_pct": 29.1,
                "stress_gap_pph": 15_600,
                "arrival_peak_low": 12_000,
                "arrival_peak_base": 16_000,
                "arrival_peak_high": 19_000,
                "arrival_peak_offset_hours": -1,
                "departure_peak_low": 15_000,
                "departure_peak_base": 20_000,
                "departure_peak_high": 23_000,
                "departure_peak_offset_hours": 2,
                "forecast_match_count": 8,
                "forecast_attendance_base": 500_000,
                "forecast_non_host_share_pct": 60.0,
                "forecast_anchor_match_id": "M095",
                "forecast_arrival_peak_low": 12_000,
                "forecast_arrival_peak_base": 16_000,
                "forecast_arrival_peak_high": 19_000,
                "forecast_arrival_peak_offset_hours": -1,
                "forecast_departure_peak_low": 15_000,
                "forecast_departure_peak_base": 20_000,
                "forecast_departure_peak_high": 23_000,
                "forecast_departure_peak_offset_hours": 2,
                "origin_host_market_share_pct": 40.0,
                "origin_host_market_attendees_base": 200_000,
                "origin_nearby_us_share_pct": 20.0,
                "origin_nearby_us_attendees_base": 100_000,
                "origin_long_distance_us_share_pct": 25.0,
                "origin_long_distance_us_attendees_base": 125_000,
                "origin_international_share_pct": 15.0,
                "origin_international_attendees_base": 75_000,
                "mode_scheduled_transit_share_pct": 20.0,
                "mode_scheduled_transit_attendees_base": 100_000,
                "mode_shuttle_coach_share_pct": 20.0,
                "mode_shuttle_coach_attendees_base": 100_000,
                "mode_private_taxi_share_pct": 55.0,
                "mode_private_taxi_attendees_base": 275_000,
                "mode_walk_bike_share_pct": 5.0,
                "mode_walk_bike_attendees_base": 25_000,
                "baseline_vehicle_trips_low": 11_000,
                "baseline_vehicle_trips_base": 12_000,
                "baseline_vehicle_trips_high": 13_000,
                "top_net_co2e_kg": 1_200,
                "top_cost_per_passenger": 85,
                "lowest_cost_intervention": "Added transit frequency",
                "top_scope": "Add 6 transit departures per hour in the event window",
                "top_evidence_quality": "medium",
                "top_intervention": "Shuttle service",
                "top_gap_resolved": 700,
                "top_vehicle_trips_avoided": 500,
                "top_net_vmt_base": 5_000,
                "top_cost_base": 90_000,
                "top_lead_time": "0-6 months",
                "representative_match_id": "M001",
                "qualified_interventions": "Shuttle service",
                "screening_confidence": "medium",
                "capacity": 70_000,
                "transit_score": 70.0,
                "first_last_mile_gap": 30.0,
                "avg_temp_c": 26.0,
                "transit_stops_0_5mi": 20,
                "gtfs_stops_1mi": 100,
                "gtfs_stops_2mi": 300,
                "nearest_stop_mi": 0.10,
                "gtfs_agencies": "MARTA",
            },
            {
                "city": "Seattle",
                "lat": 47.595,
                "lon": -122.332,
                "strict_score": 78.0,
                "strict_rank": 1,
                "peak_demand_pph": 20_000,
                "capacity_qualified_gap_pph": 5_000,
                "scheduled_transit_capacity_pph": 15_000,
                "scheduled_coverage_pct": 75.0,
                "stress_coverage_pct": 54.5,
                "stress_gap_pph": 10_000,
                "arrival_peak_low": 12_500,
                "arrival_peak_base": 15_000,
                "arrival_peak_high": 18_000,
                "arrival_peak_offset_hours": -1,
                "departure_peak_low": 16_000,
                "departure_peak_base": 20_000,
                "departure_peak_high": 24_000,
                "departure_peak_offset_hours": 2,
                "forecast_match_count": 6,
                "forecast_attendance_base": 400_000,
                "forecast_non_host_share_pct": 65.0,
                "forecast_anchor_match_id": "M088",
                "forecast_arrival_peak_low": 12_500,
                "forecast_arrival_peak_base": 15_000,
                "forecast_arrival_peak_high": 18_000,
                "forecast_arrival_peak_offset_hours": -1,
                "forecast_departure_peak_low": 16_000,
                "forecast_departure_peak_base": 20_000,
                "forecast_departure_peak_high": 24_000,
                "forecast_departure_peak_offset_hours": 2,
                "origin_host_market_share_pct": 35.0,
                "origin_host_market_attendees_base": 140_000,
                "origin_nearby_us_share_pct": 15.0,
                "origin_nearby_us_attendees_base": 60_000,
                "origin_long_distance_us_share_pct": 30.0,
                "origin_long_distance_us_attendees_base": 120_000,
                "origin_international_share_pct": 20.0,
                "origin_international_attendees_base": 80_000,
                "mode_scheduled_transit_share_pct": 45.0,
                "mode_scheduled_transit_attendees_base": 180_000,
                "mode_shuttle_coach_share_pct": 15.0,
                "mode_shuttle_coach_attendees_base": 60_000,
                "mode_private_taxi_share_pct": 35.0,
                "mode_private_taxi_attendees_base": 140_000,
                "mode_walk_bike_share_pct": 5.0,
                "mode_walk_bike_attendees_base": 20_000,
                "baseline_vehicle_trips_low": 7_000,
                "baseline_vehicle_trips_base": 8_000,
                "baseline_vehicle_trips_high": 9_000,
                "top_net_co2e_kg": 2_100,
                "top_cost_per_passenger": 70,
                "lowest_cost_intervention": "Added transit frequency",
                "top_scope": "Add 6 transit departures per hour in the event window",
                "top_evidence_quality": "medium",
                "top_intervention": "Added transit frequency",
                "top_gap_resolved": 630,
                "top_vehicle_trips_avoided": 450,
                "top_net_vmt_base": 6_000,
                "top_cost_base": 70_000,
                "top_lead_time": "3-12 months",
                "representative_match_id": "M002",
                "qualified_interventions": "Added transit frequency",
                "screening_confidence": "high",
                "capacity": 72_000,
                "transit_score": 90.0,
                "first_last_mile_gap": 10.0,
                "avg_temp_c": 18.0,
                "transit_stops_0_5mi": 50,
                "gtfs_stops_1mi": 150,
                "gtfs_stops_2mi": 400,
                "nearest_stop_mi": 0.12,
                "gtfs_agencies": "Sound Transit, King County Metro",
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


def test_portfolio_resilience_chart_compares_the_same_common_stress() -> None:
    figure = portfolio_resilience_chart(_portfolio_frame())

    assert [trace.name for trace in figure.data] == [
        "Baseline scheduled coverage",
        "Coverage after common stress",
    ]
    assert list(figure.data[1].x) == [29.1, 54.5]
    assert figure.layout.barmode == "group"


def test_portfolio_movement_chart_is_a_dumbbell_of_arrival_and_departure_peaks() -> None:
    figure = portfolio_movement_chart(_portfolio_frame())

    marker_traces = [trace for trace in figure.data if trace.mode == "markers"]
    line_traces = [trace for trace in figure.data if trace.mode == "lines"]
    assert [trace.name for trace in marker_traces] == ["Arrival peak", "Departure peak"]
    assert list(marker_traces[0].x) == [16_000, 15_000]
    assert list(marker_traces[1].x) == [20_000, 20_000]
    assert "Peak time" in marker_traces[0].hovertemplate
    # One connecting segment per city (arrival -> departure -> gap), unnamed and legend-free.
    assert len(line_traces) == 1
    assert line_traces[0].showlegend is False
    assert list(line_traces[0].x) == [16_000, 20_000, None, 15_000, 20_000, None]


def test_portfolio_transit_capacity_chart_ranks_hosts_by_departure_pressure() -> None:
    frame = pd.DataFrame(
        [
            {
                "city": "HighCapacity",
                "forecast_arrival_peak_base": 10_000,
                "forecast_departure_peak_base": 20_000,
                "mode_scheduled_transit_share_pct": 50.0,
                "scheduled_transit_capacity_pph": 10_000,
            },
            {
                "city": "LowCapacity",
                "forecast_arrival_peak_base": 10_000,
                "forecast_departure_peak_base": 20_000,
                "mode_scheduled_transit_share_pct": 50.0,
                "scheduled_transit_capacity_pph": 1_000,
            },
            {
                "city": "NoCapacity",
                "forecast_arrival_peak_base": 10_000,
                "forecast_departure_peak_base": 20_000,
                "mode_scheduled_transit_share_pct": 50.0,
                "scheduled_transit_capacity_pph": 0,
            },
        ]
    )
    figure = portfolio_transit_capacity_chart(frame)

    assert [trace.name for trace in figure.data] == ["Arrival peak", "Departure peak"]
    # Sorted by departure % descending: LowCapacity (1000%) outranks HighCapacity (100%).
    # NoCapacity is excluded from the bars entirely - a ratio against zero is undefined.
    assert list(figure.data[0].x) == ["LowCapacity", "HighCapacity"]
    assert list(figure.data[0].y) == [500.0, 50.0]
    assert list(figure.data[1].y) == [1_000.0, 100.0]
    assert figure.layout.yaxis.type == "log"
    assert any("NoCapacity" in str(annotation.text) for annotation in figure.layout.annotations)


def test_portfolio_gap_quadrant_chart_encodes_capacity_size_and_temperature_color() -> None:
    figure = portfolio_gap_quadrant_chart(_portfolio_frame())

    assert len(figure.data) == 1
    trace = figure.data[0]
    assert list(trace.x) == [70.0, 90.0]
    assert list(trace.y) == [30.0, 10.0]
    assert list(trace.text) == ["Atlanta", "Seattle"]
    assert list(trace.marker.size) == [70_000, 72_000]
    assert list(trace.marker.color) == [26.0, 18.0]
    assert figure.layout.yaxis.title.text == "First/last-mile gap score"


def test_portfolio_stop_density_chart_sorts_hosts_by_stops_within_one_mile() -> None:
    figure = portfolio_stop_density_chart(_portfolio_frame())

    assert [trace.name for trace in figure.data] == ["Within 0.5 mi", "Within 1 mi", "Within 2 mi"]
    assert list(figure.data[0].x) == ["Seattle", "Atlanta"]
    assert list(figure.data[0].y) == [50, 20]
    assert list(figure.data[1].y) == [150, 100]
    assert list(figure.data[2].y) == [400, 300]
    assert figure.layout.barmode == "group"


def test_portfolio_visitor_forecast_compares_origin_and_mode_mix_without_extra_panels() -> None:
    origins = portfolio_visitor_forecast_chart(_portfolio_frame(), "Attendee Origin")
    modes = portfolio_visitor_forecast_chart(_portfolio_frame(), "Mode mix")

    assert [trace.name for trace in origins.data] == [
        "Host market",
        "Nearby U.S.",
        "Long-distance U.S.",
        "International / unobserved",
    ]
    assert [trace.name for trace in modes.data] == [
        "Scheduled transit demand",
        "Shuttle / coach demand",
        "Private vehicle / taxi demand",
        "Walk / bike demand",
    ]
    assert origins.layout.barmode == "stack"
    assert modes.layout.barmode == "stack"
    for figure in (origins, modes):
        for city_index in range(2):
            assert sum(float(trace.x[city_index]) for trace in figure.data) == 100.0


def test_portfolio_actions_chart_uses_city_specific_priority_measures() -> None:
    actions = portfolio_actions_chart(_portfolio_frame())

    assert set(actions.data[0].text) == {"Shuttle service", "Added transit frequency"}
    assert list(actions.data[0].x) == [630, 700]


def test_portfolio_package_benefit_chart_omits_baseline_and_nets_vehicle_trips() -> None:
    city_row = {
        "baseline_vehicle_trips_base": 12_000,
        "operational_gap_resolved": 500.0,
        "operational_vehicle_trips_base": 10_000,
        "operational_net_co2e_base": 800.0,
        "capital_gap_resolved": 550.0,
        "capital_vehicle_trips_base": 9_000,
        "capital_net_co2e_base": 900.0,
    }
    figure = portfolio_package_benefit_chart(city_row)

    assert [trace.name for trace in figure.data] == ["Operational Package", "Capital Package"]
    operational, capital = figure.data
    # Vehicle trips avoided = baseline - package; the other two metrics are the
    # package's own value (baseline is trivially zero for both, by definition).
    assert list(operational.y) == [500.0, 2_000.0, 800.0]
    assert list(capital.y) == [550.0, 3_000.0, 900.0]
    assert list(operational.x) == [
        "Peak passengers\naddressed / hr",
        "Vehicle trips\navoided",
        "Net CO2e\navoided (kg)",
    ]
    assert figure.layout.barmode == "group"


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


def test_access_overlap_map_keeps_service_screen_routes_stops_and_walk_distinct() -> None:
    figure = access_overlap_map(
        {"name": "MetLife Stadium", "lat": 40.8135, "lon": -74.0745},
        {
            "gtfs_routes": [{"route_name": "Rail", "coordinates": [[-74.10, 40.82], [-74.07, 40.81]]}],
            "gtfs": [{"name": "Rutherford", "lat": 40.828, "lon": -74.101}],
            "walk": [{"name": "Network path", "coordinates": [[-74.08, 40.81], [-74.07, 40.82]]}],
        },
    )

    assert [trace.name for trace in figure.data] == [
        "Half-mile service screen",
        "Event-valid GTFS routes",
        "Event-relevant stops",
        "Walking evidence",
        "Venue",
    ]
    assert len(figure.data[0].lat) == 73
    assert figure.layout.map.zoom == 11.2


def test_operating_overlap_map_separates_selected_and_other_candidate_hubs() -> None:
    figure = operating_overlap_map(
        {
            "regional_hub_name": "Candidate Station",
            "regional_hub_lat": 32.80,
            "regional_hub_lon": -97.05,
            "regional_hub_status": "candidate",
        },
        {"name": "AT&T Stadium", "lat": 32.748, "lon": -97.0929},
        [
            {"name": "Candidate Station", "lat": 32.80, "lon": -97.05},
            {"name": "Other Station", "lat": 32.817, "lon": -97.053},
        ],
    )

    assert [trace.name for trace in figure.data] == [
        "Schematic transfer link",
        "Other screened candidates",
        "Selected engine anchor",
        "Venue",
    ]
    assert list(figure.data[1].text) == ["Other Station"]
