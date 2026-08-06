from __future__ import annotations

import pytest

from dashboard.domain.portfolio import build_portfolio_timeline, portfolio_summary
from dashboard.models.interventions import default_factor_registry

EVENTS = [
    {"match_id": "A-1", "city": "A", "kickoff_local": "2026-06-10T12:00:00-05:00"},
    {"match_id": "A-2", "city": "A", "kickoff_local": "2026-06-12T12:00:00-05:00"},
    {"match_id": "B-1", "city": "B", "kickoff_local": "2026-06-13T12:00:00-05:00"},
]
PACKAGE = {
    "name": "Capital Package",
    "shuttle_buses_per_hour": 2,
    "added_transit_departures_per_hour": 1,
    "park_ride_spaces": 10,
    "park_ride_feeder_departures_per_hour": 2,
    "bike_hub_spaces": 5,
    "cooled_walkway_km": 1,
    "arrival_spreading_pct": 5,
}
OUTCOMES = [
    {
        "match_id": event["match_id"],
        "city": event["city"],
        "package": PACKAGE,
        "status": "scenario",
        "gap_resolved_passengers": 100,
        "net_vmt_base": 200,
        "net_co2e_kg_base": 20,
        "heat_exposure_person_hours_avoided": 2,
    }
    for event in EVENTS
]
INPUTS = [{"match_id": event["match_id"], "arrival_window_hours": 3} for event in EVENTS]


def test_city_portfolio_counts_capital_once_and_operations_per_match():
    timeline = build_portfolio_timeline(
        EVENTS,
        OUTCOMES,
        INPUTS,
        default_factor_registry(),
        package_name="Capital Package",
        scope="city_tournament",
        city="A",
    )
    assert len(timeline) == 2
    assert timeline.iloc[0]["event_capital_cost_base"] > 0
    assert timeline.iloc[1]["event_capital_cost_base"] == 0
    assert timeline.iloc[0]["event_operating_cost_base"] > 0
    assert timeline.iloc[1]["operating_cost_base"] == pytest.approx(2 * timeline.iloc[0]["event_operating_cost_base"])
    assert portfolio_summary(timeline)["gap_resolved_passengers"] == 200


def test_us_portfolio_capitalizes_each_city_once():
    timeline = build_portfolio_timeline(
        EVENTS,
        OUTCOMES,
        INPUTS,
        default_factor_registry(),
        package_name="Capital Package",
        scope="us_tournament",
    )
    capital_events = timeline[timeline["event_capital_cost_base"] > 0]
    assert set(capital_events["city"]) == {"A", "B"}
    assert len(capital_events) == 2
    assert timeline.iloc[-1]["gap_resolved_passengers"] == 300


def test_match_scope_selects_exact_match_and_unknown_scope_fails():
    timeline = build_portfolio_timeline(
        EVENTS,
        OUTCOMES,
        INPUTS,
        default_factor_registry(),
        package_name="Capital Package",
        scope="match",
        match_id="A-2",
    )
    assert timeline["match_id"].tolist() == ["A-2"]
    with pytest.raises(ValueError):
        build_portfolio_timeline(EVENTS, OUTCOMES, INPUTS, default_factor_registry(), package_name="Capital Package", scope="bad")


def test_default_portfolio_excludes_nonqualified_access_but_opt_in_retains_status():
    access = [
        {"match_id": "A-1", "status": "scenario"},
        {"match_id": "A-2", "status": "partial"},
        {"match_id": "B-1", "status": "unavailable"},
    ]
    strict = build_portfolio_timeline(
        EVENTS,
        OUTCOMES,
        INPUTS,
        default_factor_registry(),
        package_name="Capital Package",
        scope="us_tournament",
        access_rows=access,
    )
    assert strict["match_id"].tolist() == ["A-1"]
    assert strict.iloc[-1]["omitted_matches"] == 2
    screening = build_portfolio_timeline(
        EVENTS,
        OUTCOMES,
        INPUTS,
        default_factor_registry(),
        package_name="Capital Package",
        scope="us_tournament",
        access_rows=access,
        include_partial=True,
    )
    assert set(screening["access_evidence_status"]) == {"scenario", "partial", "unavailable"}
