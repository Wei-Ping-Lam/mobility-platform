from dataclasses import replace

import pandas as pd
import pytest

from dashboard.domain.solution_context import ELECTRIC, FREQUENCY, HUBS, LANES, solution_context
from dashboard.models.interventions import CityInterventionInputs, default_factor_registry
from dashboard.models.solution_comparison import compare_transit_solutions
from dashboard.viz.portfolio import transit_solution_comparison_chart


@pytest.fixture
def inputs():
    return CityInterventionInputs(
        city="Houston", match_id="test", private_vehicle_share=0.5,
        average_vehicle_occupancy=2, average_private_trip_miles=30,
        venue_area_leg_miles=5, shuttle_round_trip_miles=15,
        transit_round_trip_miles=18, park_ride_feeder_round_trip_miles=15,
        bike_access_distance_m=1000, walk_corridor_length_km=1,
    )


def test_four_distinct_solutions_with_bounded_beneficiaries(inputs):
    rows = compare_transit_solutions(60000, inputs, default_factor_registry())
    assert [row["solution"] for row in rows] == [
        "Dedicated event bus/shuttle lanes", "Remote park-and-ride + shuttle hubs",
        "Increase rail/transit frequency", "Electric shuttle/bus fleet",
    ]
    for row in rows:
        assert 0 <= row["shifted_passengers"] <= row["passengers"] <= 60000


def test_lane_improvements_credit_only_incremental_shift_and_service(inputs):
    lanes = compare_transit_solutions(60000, inputs, default_factor_registry())[0]
    # 12 buses x 3 hours, cycle improves from 1h to 0.75h.
    assert lanes["passengers"] == pytest.approx(48 * 45 * 0.75)
    assert lanes["shifted_passengers"] == pytest.approx((48 - 36) * 45 * 0.75 * 0.5)
    assert lanes["added_service_miles"] == (48 - 36) * 2 * 15


def test_park_ride_does_not_credit_entire_drive_to_hub(inputs):
    row = compare_transit_solutions(60000, inputs, default_factor_registry())[1]
    assert row["passengers"] == 1400
    assert row["net_vehicle_miles"] == 1400 / 2 * 5 - 42 * 2 * 5
    assert row["co2e_screen"] == "Pass"
    longer_drive = replace(inputs, average_private_trip_miles=100)
    assert row == compare_transit_solutions(60000, longer_drive, default_factor_registry())[1]


def test_electrification_replaces_existing_service_without_new_capacity(inputs):
    row = compare_transit_solutions(60000, inputs, default_factor_registry())[3]
    assert row["passengers"] == 36 * 45 * 0.75
    assert row["shifted_passengers"] == 0
    assert row["net_vehicle_miles"] == 0
    assert row["net_co2e_kg"] == pytest.approx(36 * 2 * 15 * 1.35 * 0.6)


def test_low_attendance_and_car_pool_cap_benefits(inputs):
    inputs = replace(inputs, private_vehicle_share=0.1)
    for row in compare_transit_solutions(10, inputs, default_factor_registry()):
        assert row["passengers"] <= 10
        assert row["shifted_passengers"] <= 1


def test_negative_emissions_savings_remain_visible(inputs):
    rows = compare_transit_solutions(
        60000, replace(inputs, average_private_trip_miles=5, transit_round_trip_miles=100), default_factor_registry()
    )
    assert rows[2]["net_co2e_kg"] < 0
    assert rows[2]["co2e_screen"] == "Needs redesign"
    figure = transit_solution_comparison_chart(pd.DataFrame(rows))
    assert len(figure.data) == 4
    assert figure.layout.yaxis.range[0] < rows[2]["net_co2e_kg"]
    assert figure.layout.yaxis.zeroline
    assert figure.layout.xaxis.title.text == "Passengers addressed per match"
    assert figure.layout.yaxis.title.text == "Net CO2e avoided (kg / match)"
    for row, trace in zip(rows, figure.data):
        assert trace.x[0] == row["passengers"]
        assert trace.y[0] == row["net_co2e_kg"]
        assert "Shifted from cars" in trace.hovertemplate


def test_no_car_demand_does_not_trigger_empty_additional_services(inputs):
    rows = compare_transit_solutions(60000, replace(inputs, private_vehicle_share=0), default_factor_registry())
    for row in rows[:3]:
        assert row["added_service_miles"] == 0
        assert row["net_co2e_kg"] == 0


def test_empty_event_has_no_fleet_replacement_benefit(inputs):
    rows = compare_transit_solutions(0, inputs, default_factor_registry())
    assert all(row["net_co2e_kg"] == row["passengers"] == 0 for row in rows)


@pytest.mark.parametrize("attendance", [-1, float("nan"), float("inf")])
def test_invalid_attendance_rejected(inputs, attendance):
    with pytest.raises(ValueError):
        compare_transit_solutions(attendance, inputs, default_factor_registry())


def test_city_context_distinguishes_related_services_from_exact_solution():
    benchmark = {
        "dedicated_service_evidence": {"basis": "Reviewed service evidence", "source_url": "https://example.org/service"},
        "sustainability_evidence": {"fleet_electrification_basis": "Reviewed fleet evidence", "source_url": "https://example.org/fleet"},
    }
    houston = solution_context("Houston", benchmark)
    assert houston[HUBS]["city_context"] == "Related approach"
    assert "rail" in houston[HUBS]["context_note"]
    assert solution_context("Kansas City", benchmark)[HUBS]["city_context"] == "Existing approach"
    assert solution_context("Los Angeles", benchmark)[LANES]["city_context"] == "Published plan"
    assert houston[ELECTRIC]["city_context"] == "Related approach"
    assert solution_context("Boston", benchmark)[ELECTRIC]["city_context"] == "Not documented"
    assert solution_context("Seattle", benchmark)[FREQUENCY]["city_context"] == "Related approach"


def test_missing_city_evidence_does_not_claim_existing_implementation():
    for row in solution_context("Houston", {}).values():
        assert row["city_context"] == "Not documented"
        assert row["context_source"] == ""


def test_recommended_action_is_separate_from_four_solution_examples(inputs):
    rows = compare_transit_solutions(60000, inputs, default_factor_registry())
    rows[0]["city_context"] = "Published plan"
    recommended = {
        "solution": "Recommended: Faster entry", "passengers": 9000,
        "net_co2e_kg": 0, "shifted_passengers": 0, "net_vehicle_miles": 0,
    }
    figure = transit_solution_comparison_chart(pd.DataFrame(rows), recommended)
    assert len(figure.data) == 5
    assert figure.data[-1].marker.symbol == "star"
    assert figure.data[-1].name == "Recommended first action"
    assert figure.data[-1].x[0] == 9000
    assert figure.data[-1].y[0] == 0
    assert figure.layout.xaxis.range[1] > 9000
    assert figure.data[0].marker.symbol == "diamond"
    assert "Published plan" in figure.data[0].name
    assert figure.data[1].marker.symbol == "circle"
