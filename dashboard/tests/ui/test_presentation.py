import json

import pandas as pd

from dashboard.mobility_platform.contracts import (
    AccessGapResult,
    EvidenceStatus,
    InterventionOutcome,
    InterventionPackage,
    InvestmentRecommendation,
    MatchEvent,
    MovementScenario,
    SourceReference,
)
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.ui.presentation import NAMED_SCENARIOS, build_presentation, city_layer_records
from dashboard.ui.views import _before_after


def _metrics() -> pd.DataFrame:
    rows = []
    for city, metadata in HOST_CITIES.items():
        rows.append(
            {
                "city": city,
                "venue": metadata["venue"],
                "lat": metadata["lat"],
                "lon": metadata["lon"],
                "capacity": metadata["capacity"],
                "games": metadata["games"],
                "peak_visitors": int(metadata["capacity"] * .95),
                "score": 60.0,
                "rankable": False,
                "score_status": "partial",
                "transit_score": None,
                "transit_status": "unavailable",
                "heat_score": 70.0,
                "heat_status": "derived",
                "uhi_score": 60.0,
                "uhi_status": "derived",
                "access_score": 50.0,
                "access_status": "derived",
                "data_coverage": .75,
                "demand_status": "derived",
            }
        )
    return pd.DataFrame(rows)


def _contract_artifacts() -> dict:
    source = SourceReference(
        source="Official FIFA schedule",
        url="https://www.fifa.com/",
        publisher="FIFA",
        retrieved_at_utc="2026-01-01T00:00:00Z",
        version="fixture-1",
        sha256="fixture-sha256",
        license="reference-only",
        coverage_start="2026-06-11",
        coverage_end="2026-07-19",
        status=EvidenceStatus.OBSERVED,
    )
    match = MatchEvent(
        match_id="ATL-01",
        city="Atlanta",
        venue="Mercedes-Benz Stadium",
        kickoff_local="2026-06-15T15:00:00-04:00",
        stage="group",
        capacity=71000,
        source=source,
    )
    movement = MovementScenario(
        city="Atlanta",
        match_id="ATL-01",
        status=EvidenceStatus.SCENARIO,
        uncertainty_type="planning range",
        attendance_low=60000,
        attendance_base=67000,
        attendance_high=71000,
        hourly_rows=(
            {"hour": "12:00", "arrivals_low": 2000, "arrivals_base": 3000, "arrivals_high": 4000, "departures_base": 0},
            {"hour": "13:00", "arrivals_low": 6000, "arrivals_base": 9000, "arrivals_high": 12000, "departures_base": 0},
            {"hour": "14:00", "arrivals_low": 3000, "arrivals_base": 5000, "arrivals_high": 7000, "departures_base": 0},
        ),
        assumptions=("Illustrative fixture",),
    )
    access = AccessGapResult(
        city="Atlanta",
        match_id="ATL-01",
        status=EvidenceStatus.SCENARIO,
        peak_demand_per_hour=18000,
        transit_capacity_low=6000,
        transit_capacity_base=8000,
        transit_capacity_high=10000,
        residual_passengers=10000,
        network_walk_distance_m=420,
        service_span_after_match_min=180,
        route_heat_exposure_c=33.2,
    )
    packages = (
        InterventionPackage(name="Baseline"),
        InterventionPackage(name="Operational Package", shuttle_buses_per_hour=20, arrival_spreading_pct=20),
        InterventionPackage(name="Capital Package", added_transit_departures_per_hour=12, cooled_walkway_km=2.5),
    )
    outcomes = []
    for index, package in enumerate(packages):
        outcomes.append(
            InterventionOutcome(
                city="Atlanta",
                match_id="ATL-01",
                package=package,
                status=EvidenceStatus.SCENARIO,
                gap_resolved_passengers=index * 3500,
                venue_vehicle_trips_low=9000 - index * 500,
                venue_vehicle_trips_base=10000 - index * 700,
                venue_vehicle_trips_high=11000 - index * 900,
                net_vmt_low=index * 2000,
                net_vmt_base=index * 3000,
                net_vmt_high=index * 4000,
                net_co2e_kg_low=index * 200,
                net_co2e_kg_base=index * 300,
                net_co2e_kg_high=index * 400,
                heat_exposure_person_hours_avoided=index * 25,
                cost_low=index * 100000,
                cost_base=index * 150000,
                cost_high=index * 200000,
            )
        )
    recommendation = InvestmentRecommendation(
        city="Atlanta",
        match_id="ATL-01",
        intervention="Operational Package",
        rationale="Closes part of the documented match-hour gap.",
        status=EvidenceStatus.SCENARIO,
        cost_low=100000,
        cost_base=150000,
        cost_high=200000,
        gap_resolved_passengers=3500,
        cost_per_passenger=42.857,
        net_co2e_kg=300,
        lead_time_band="0-6 months",
        responsible_actor="MARTA and venue operations",
    )
    return {
        "match_events": [match],
        "movement_scenarios": [movement],
        "access_gaps": [access],
        "intervention_outcomes": outcomes,
        "investment_recommendations": [recommendation],
        "source_references": [source],
        "factor_registry": [{"factor": "car CO2e", "low": .2, "base": .3, "high": .4, "source_sha256": "factor-sha"}],
        "network_coverage": [{"city": "Atlanta", "walk_edges": 100, "sidewalk_tag_coverage": .55}],
    }


def test_legacy_adapter_renders_all_11_cities_and_named_scenarios():
    presentation = build_presentation(_metrics(), {})
    assert sorted(presentation.cities) == sorted(HOST_CITIES)
    for decision in presentation.cities.values():
        match = decision.match()
        assert tuple(item.name for item in decision.scenario_set(match.match_id)) == NAMED_SCENARIOS
        assert decision.access(match.match_id).status == "unavailable"


def test_contract_adapter_preserves_gap_ranges_sources_and_exact_download():
    presentation = build_presentation(_metrics(), _contract_artifacts())
    decision = presentation.city("Atlanta")
    access = decision.access("ATL-01")
    assert access.residual_passengers == 10000
    assert access.transit_capacity_low == 6000
    scenarios = decision.scenario_set("ATL-01")
    assert scenarios[1].cost_low == 100000
    assert scenarios[1].net_co2e_kg_high == 400
    payload = json.loads(presentation.scenario_json("Atlanta", "ATL-01"))
    assert payload["access_gap"]["residual_passengers"] == access.residual_passengers
    assert payload["scenarios"] == [scenario.to_dict() for scenario in scenarios]
    assert presentation.source_rows[0]["sha256"] == "fixture-sha256"


def test_missing_gtfs_and_walking_layers_stay_empty_without_inference():
    assert city_layer_records({}, "Atlanta", "gtfs") == []
    assert city_layer_records({}, "Atlanta", "walk") == []


def test_layer_adapter_accepts_frozen_map_bundle():
    artifacts = {
        "map_layers": {
            "Atlanta": {
                "gtfs": [{"lat": 33.75, "lon": -84.39, "name": "Station"}],
                "walk": [{"coordinates": [[-84.4, 33.7], [-84.39, 33.75]]}],
            }
        }
    }
    assert len(city_layer_records(artifacts, "Atlanta", "gtfs")) == 1
    assert len(city_layer_records(artifacts, "Atlanta", "walk")) == 1


def test_arrival_spreading_preserves_total_and_reduces_fixture_peak():
    presentation = build_presentation(_metrics(), _contract_artifacts())
    decision = presentation.city("Atlanta")
    movement = decision.movement("ATL-01")
    operational = decision.scenario_set("ATL-01")[1]
    timeline = _before_after(movement, operational)
    assert timeline["Before"].sum() == timeline["After"].sum()
    assert timeline["After"].max() < timeline["Before"].max()


def test_sensitivity_is_available_for_every_named_profile_and_city():
    presentation = build_presentation(_metrics(), {})
    sensitivity = pd.DataFrame(presentation.sensitivity_rows)
    assert sensitivity["Profile"].nunique() == 5
    assert sensitivity["City"].nunique() == 11
