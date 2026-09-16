from dataclasses import replace

import pytest

from dashboard.domain.action_plans import CITY_ACTION_PLANS
from dashboard.models.action_impact import ACTION_SCOPES, estimate_action_impact
from dashboard.models.electric_bus import electric_bus_kg_per_mile
from dashboard.models.interventions import default_factor_registry


def estimate(city, **overrides):
    inputs = dict(
        attendance=60000, private_vehicle_share=0.5, vehicle_occupancy=2,
        private_trip_miles=30, local_leg_miles=5, arrival_hours=3,
        factors=default_factor_registry(),
    )
    inputs.update(overrides)
    return estimate_action_impact(city, **inputs)


def test_every_curated_city_has_an_action_scope():
    assert ACTION_SCOPES.keys() == CITY_ACTION_PLANS.keys()


@pytest.mark.parametrize("city", ACTION_SCOPES)
def test_counts_and_costs_reconcile(city):
    for row in estimate(city):
        assert 0 <= row["shifted_passengers"] <= row["passengers"] <= 60000
        assert row["shifted_passengers"] <= 30000
        assert row["first_event_cost"] == row["capital_cost"] + row["operating_cost"]
        assert row["net_vehicle_miles"] == row["avoided_car_miles"] - row["service_miles"] + row["baseline_service_miles"]
        assert row["net_co2e_kg"] == pytest.approx(
            row["avoided_car_co2e_kg"] + row["baseline_service_co2e_kg"] - row["proposed_service_co2e_kg"]
        )


def test_electric_last_mile_shuttle_counts_riders_once_and_targets_car_replacement():
    base = estimate("Houston")[1]
    assert base["passengers"] == pytest.approx(4 * 8 * 45 * 0.75)
    assert base["arrival_cycles"] == 32
    assert base["service_hours"] == pytest.approx(25.6)
    assert base["paid_service_hours"] == pytest.approx(29.6)
    assert base["service_miles"] == pytest.approx(256 * 1.1)
    assert base["net_vehicle_miles"] == pytest.approx(864 - 256 * 1.1)
    assert base["net_co2e_kg"] == pytest.approx(864 * 0.35 - 256 * 1.1 * electric_bus_kg_per_mile("Houston"))
    assert base["operating_cost"] == pytest.approx(29.6 * 160 * 1.2 + 1000)
    assert base["minimum_car_shift_share"] < 0.4
    assert base["co2e_screen"] == "Pass"


def test_parking_mode_shift_is_limited_to_existing_car_passengers():
    base = estimate("Atlanta", private_vehicle_share=0.01)[1]
    assert base["passengers"] == 600
    assert base["net_vehicle_miles"] == 600 / 2 * 30


def test_path_improvement_only_avoids_local_vehicle_leg():
    base = estimate("New York/NJ")[1]
    assert base["passengers"] == 2400
    assert base["net_vehicle_miles"] == 2400 * 0.05 / 2 * 5
    assert base["capital_cost"] == 750000
    assert base["first_event_cost"] == 752000


def test_sf_detour_guidance_does_not_budget_a_permanent_bypass(monkeypatch):
    base = estimate("San Francisco")[1]
    assert base["capital_cost"] == 0
    assert base["operating_cost"] == base["first_event_cost"] == 1000
    assert base["car_round_trip_miles"] == 5
    monkeypatch.setitem(ACTION_SCOPES, "San Francisco", replace(
        ACTION_SCOPES["San Francisco"], private_shift_share=0,
    ))
    without_mode_shift = estimate("San Francisco")[1]
    assert without_mode_shift["passengers"] > 0
    assert without_mode_shift["net_co2e_kg"] == without_mode_shift["net_vehicle_miles"] == 0
    assert without_mode_shift["co2e_screen"] == "No reduction"


@pytest.mark.parametrize("city", ["Kansas City", "Los Angeles", "Philadelphia"])
def test_operations_alone_do_not_invent_emissions_savings(city, monkeypatch):
    monkeypatch.setitem(ACTION_SCOPES, city, replace(
        ACTION_SCOPES[city], buses=0, private_shift_share=0, incentive_per_shifted_rider=0,
    ))
    base = estimate(city)[1]
    assert base["passengers"] > 0
    assert base["net_vehicle_miles"] == base["net_co2e_kg"] == 0
    assert base["operating_cost"] > 0
    assert base["co2e_screen"] == "No reduction"


def test_seattle_targets_incremental_car_trips_and_budgets_credits():
    base = estimate("Seattle")[1]
    assert base["passengers"] == base["shifted_passengers"] == 1200
    assert base["incentive_cost"] == 12000
    assert base["first_event_cost"] == 14000
    assert base["net_co2e_kg"] == pytest.approx(1200 / 2 * 30 * 0.35)


def test_no_car_trips_to_replace_cannot_meet_positive_recommendation_target():
    base = estimate("Seattle", private_vehicle_share=0)[1]
    assert base["net_co2e_kg"] == base["incentive_cost"] == 0
    assert base["co2e_screen"] == "No reduction"


@pytest.mark.parametrize("city", ACTION_SCOPES)
def test_recommended_base_packages_have_positive_estimated_savings(city):
    base = estimate(city)[1]
    assert base["net_co2e_kg"] > 0
    assert base["co2e_screen"] == "Pass"


@pytest.mark.parametrize("city", ["Kansas City", "Los Angeles"])
def test_combined_actions_do_not_double_count_beneficiaries(city):
    base = estimate(city)[1]
    assert base["passengers"] == max(base["operations_passengers"], base["service_passengers"])
    assert base["shifted_passengers"] == 0
    assert base["net_co2e_kg"] > 0


def test_philadelphia_credits_only_the_targeted_incremental_mode_shift():
    base = estimate("Philadelphia")[1]
    assert base["passengers"] == 15000
    assert base["shifted_passengers"] == 300
    assert base["net_co2e_kg"] == pytest.approx(300 / 2 * 30 * 0.35)
    assert base["incentive_cost"] == 3000
    assert base["operating_cost"] == 9000


def test_low_attendance_caps_bus_beneficiaries_without_erasing_bus_cost():
    base = estimate("Boston", attendance=10)[1]
    assert base["passengers"] == 10
    assert base["shifted_passengers"] == 0
    assert base["service_hours"] == 6
    assert base["incentive_cost"] == 200
    assert base["net_vehicle_miles"] == 0
    assert base["net_co2e_kg"] > 0


def test_boston_fare_credits_and_replacement_service_do_not_invent_mode_shift():
    scope = ACTION_SCOPES["Boston"]
    for row in estimate("Boston"):
        assert row["passengers"] == row["service_passengers"]
        assert row["shifted_passengers"] == row["avoided_car_miles"] == 0
        assert row["net_vehicle_miles"] == 0
        assert row["baseline_service_miles"] == row["service_miles"]
        assert row["incentive_cost"] == row["passengers"] * 20
        assert row["net_co2e_kg"] == pytest.approx(
            row["baseline_service_co2e_kg"] - row["proposed_service_co2e_kg"]
        )
        case = row["case"]
        expected_service_cost = (
            row["paid_service_hours"] * default_factor_registry().shuttle_cost_per_bus_hour.value(case) * 1.2
        )
        assert row["operating_cost"] == pytest.approx(
            expected_service_cost + scope.operating_allowance * row["cost_scale"] + row["incentive_cost"]
        )


def test_boston_without_displaced_conventional_trips_cannot_claim_savings(monkeypatch):
    monkeypatch.setitem(ACTION_SCOPES, "Boston", replace(ACTION_SCOPES["Boston"], replaces_existing_service=False))
    base = estimate("Boston")[1]
    assert base["net_co2e_kg"] < 0
    assert base["co2e_screen"] == "Needs redesign"


def test_boston_zero_bookings_have_no_fleet_savings_or_fare_credits():
    base = estimate("Boston", attendance=0)[1]
    assert base["passengers"] == base["service_miles"] == base["baseline_service_miles"] == 0
    assert base["incentive_cost"] == base["net_co2e_kg"] == 0
    assert base["co2e_screen"] == "No reduction"


def test_electric_overflow_replaces_equivalent_conventional_trips():
    base = estimate("Dallas")[1]
    assert base["net_vehicle_miles"] == 0
    assert base["net_co2e_kg"] == pytest.approx(base["service_miles"] * (1.35 - electric_bus_kg_per_mile("Dallas")))


def test_fractional_bus_cycles_cannot_be_pooled_into_extra_trips():
    base = estimate("Boston", arrival_hours=2.5)[1]
    assert base["arrival_cycles"] == 12
    assert base["passengers"] == 405
    assert base["service_hours"] == 72
    assert base["paid_service_hours"] == 84


@pytest.mark.parametrize("city", ACTION_SCOPES)
def test_factor_sensitivity_brackets_base_without_forcing_positive_savings(city):
    base = estimate(city)[1]
    assert base["net_co2e_kg_low"] <= base["net_co2e_kg"] <= base["net_co2e_kg_high"]


def test_houston_adverse_factor_case_can_fail_even_when_base_passes():
    base = estimate("Houston")[1]
    assert base["net_co2e_kg"] > 0
    assert base["net_co2e_kg_low"] < 0


def test_walker_only_shuttle_demand_is_not_claimed_sustainable():
    base = estimate("Houston", private_vehicle_share=0)[1]
    assert base["net_co2e_kg"] < 0
    assert base["co2e_screen"] == "Needs redesign"


@pytest.mark.parametrize("overrides", [
    {"attendance": float("nan")}, {"vehicle_occupancy": 0},
    {"private_vehicle_share": 2}, {"local_leg_miles": 50},
])
def test_invalid_inputs_do_not_produce_plausible_estimates(overrides):
    with pytest.raises(ValueError):
        estimate("Boston", **overrides)
