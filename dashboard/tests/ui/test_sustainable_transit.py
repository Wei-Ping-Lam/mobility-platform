import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard.models.action_impact import ACTION_SCOPES, estimate_action_impact
from dashboard.models.interventions import CityInterventionInputs, factor_registry_from_snapshot
from dashboard.models.solution_comparison import compare_transit_solutions


def test_all_host_match_base_designs_pass_operational_co2_screen():
    app = AppTest.from_file("dashboard/app.py").run(timeout=60)
    assert not app.exception
    bundle = app.session_state["_metrics_bundle_cache"][2]
    snapshot = json.loads(Path("data/snapshots/factors/planning_factors.json").read_text(encoding="utf-8"))
    factors = factor_registry_from_snapshot(snapshot)
    attendance = {
        (row["city"], row["match_id"]): row["attendance_base"]
        for row in bundle["movement_scenarios"]
    }
    checked_cities = set()
    failures = []
    for row in bundle["city_intervention_inputs"]:
        inputs = CityInterventionInputs(**row)
        total = attendance[(inputs.city, inputs.match_id)]
        cases = compare_transit_solutions(total, inputs, factors)
        action = estimate_action_impact(
            inputs.city, total, inputs.private_vehicle_share, inputs.average_vehicle_occupancy,
            inputs.average_private_trip_miles, inputs.venue_area_leg_miles,
            inputs.arrival_window_hours, factors,
        )[1]
        if action["net_co2e_kg"] <= 0:
            failures.append((inputs.city, inputs.match_id, "Recommended action requires positive savings", action["net_co2e_kg"]))
        for result in cases + [dict(action, solution="Recommended action")]:
            if result["net_co2e_kg"] < 0:
                failures.append((inputs.city, inputs.match_id, result["solution"], result["net_co2e_kg"]))
        checked_cities.add(inputs.city)
    assert checked_cities == set(ACTION_SCOPES)
    assert not failures, failures
