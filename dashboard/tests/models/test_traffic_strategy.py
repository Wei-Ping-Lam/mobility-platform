from __future__ import annotations

from dataclasses import replace

import pytest

from dashboard.mobility_platform.contracts import (
    AccessGapResult,
    EvidenceStatus,
    InvestmentRecommendation,
    MatchEvent,
    MovementScenario,
    SourceReference,
)
from dashboard.models.interventions import CityInterventionInputs, default_factor_registry
from dashboard.models.traffic_strategy import PHASES, build_traffic_strategy_plan


def _inputs(*, city_name: str = "Dallas", capacity: float = 0, demand: float = 18_000):
    match = MatchEvent(
        match_id="M011",
        city=city_name,
        venue="Dallas Stadium",
        kickoff_local="2026-06-14T18:00:00-05:00",
        stage="group",
        capacity=80_000,
        source=SourceReference(
            source="Official schedule fixture",
            url="https://example.test/schedule",
            publisher="Fixture",
            retrieved_at_utc="2026-01-01T00:00:00Z",
            version="fixture",
            sha256="0" * 64,
            license="test",
        ),
    )
    movement = MovementScenario(
        city=city_name,
        match_id="M011",
        status=EvidenceStatus.SCENARIO,
        uncertainty_type="planning range",
        attendance_low=60_000,
        attendance_base=70_000,
        attendance_high=80_000,
        hourly_rows=(
            {
                "timestamp_local": "2026-06-14T15:00:00-05:00",
                "arrivals_low": 15_000,
                "arrivals_base": 17_500,
                "arrivals_high": 20_000,
                "departures_low": 0,
                "departures_base": 0,
                "departures_high": 0,
            },
            {
                "timestamp_local": "2026-06-14T16:00:00-05:00",
                "arrivals_low": 45_000,
                "arrivals_base": 52_500,
                "arrivals_high": 60_000,
                "departures_low": 0,
                "departures_base": 0,
                "departures_high": 0,
            },
            {
                "timestamp_local": "2026-06-14T20:00:00-05:00",
                "arrivals_low": 0,
                "arrivals_base": 0,
                "arrivals_high": 0,
                "departures_low": 48_000,
                "departures_base": 56_000,
                "departures_high": 64_000,
            },
            {
                "timestamp_local": "2026-06-14T21:00:00-05:00",
                "arrivals_low": 0,
                "arrivals_base": 0,
                "arrivals_high": 0,
                "departures_low": 12_000,
                "departures_base": 14_000,
                "departures_high": 16_000,
            },
        ),
    )
    access = AccessGapResult(
        city=city_name,
        match_id="M011",
        status=EvidenceStatus.PARTIAL,
        peak_demand_per_hour=demand,
        transit_capacity_low=max(capacity * 0.75, 0),
        transit_capacity_base=capacity,
        transit_capacity_high=capacity * 1.25,
        residual_passengers=max(demand - capacity, 0),
        network_walk_distance_m=750,
        service_span_after_match_min=180,
        route_heat_exposure_c=40,
        transit_status=EvidenceStatus.OBSERVED,
        walking_status=EvidenceStatus.DERIVED,
        service_span_status=EvidenceStatus.OBSERVED,
        heat_status=EvidenceStatus.DERIVED,
        capacity_qualified=True,
    )
    city = CityInterventionInputs(
        city=city_name,
        match_id="M011",
        private_vehicle_share=0.6,
        average_vehicle_occupancy=2.2,
        average_private_trip_miles=24,
        venue_area_leg_miles=5,
        shuttle_round_trip_miles=16,
        transit_round_trip_miles=18,
        park_ride_feeder_round_trip_miles=16,
        bike_access_distance_m=2_000,
        walk_corridor_length_km=3,
    )
    return match, movement, access, city


def _recommendation(name: str, *, remaining_trips: float = 18_000) -> InvestmentRecommendation:
    return InvestmentRecommendation(
        city="Dallas",
        match_id="M011",
        intervention=name,
        rationale="Fixture option",
        status=EvidenceStatus.SCENARIO,
        cost_low=10_000,
        cost_base=15_000,
        cost_high=20_000,
        gap_resolved_passengers=1_500,
        cost_per_passenger=10,
        net_co2e_kg=2_000,
        lead_time_band="0-6 months",
        responsible_actor="Agency and venue",
        evidence_qualified=True,
        venue_vehicle_trips_base=remaining_trips,
        net_vmt_base=8_000,
    )


def _recommendations() -> tuple[InvestmentRecommendation, ...]:
    return (_recommendation("Shuttle service"), _recommendation("Added transit frequency"))


def test_published_dallas_plan_overrides_generated_pattern_and_locations() -> None:
    match, movement, access, city = _inputs()
    official = {
        "primary_pattern": "Regional rail to charter-bus bridge",
        "modeled_measure": "Shuttle service",
        "source_ids": ["dallas_fwc26_mobility_plan"],
        "arrival_window": "5 hours before kickoff through kickoff",
        "egress_window": "Match end through 3 hours after",
        "transfer_hubs": [{"name": "TRE CentrePort/DFW Airport Station", "role": "primary transfer"}],
        "curb_location": "Arlington Esports Stadium rideshare and taxi lot",
        "published_controls": ["AT&T Way closed on match days"],
        "overflow_trigger": "Dispatch dynamic charter buses when train capacity produces lines.",
    }

    plan = build_traffic_strategy_plan(
        match,
        movement,
        access,
        city,
        default_factor_registry(),
        _recommendations(),
        official_plan=official,
    )

    assert plan.primary_pattern == "Regional rail to charter-bus bridge"
    assert plan.regional_hub_name == "TRE CentrePort/DFW Airport Station"
    assert plan.regional_hub_status == "published"
    assert plan.official_plan_available
    assert plan.published_controls == ("AT&T Way closed on match days",)
    assert plan.actions[2].location_status == "published"
    assert plan.actions[-1].evidence_status is EvidenceStatus.OBSERVED


def test_zero_direct_capacity_uses_regional_hub_candidate_without_inventing_controls() -> None:
    match, movement, access, city = _inputs()
    plan = build_traffic_strategy_plan(
        match,
        movement,
        access,
        city,
        default_factor_registry(),
        _recommendations(),
        regional_hubs=[{"name": "Central Station", "distance_mi": 7.5, "status": "observed"}],
    )

    assert plan.primary_pattern == "Regional hub to event shuttle"
    assert plan.regional_hub_status == "candidate"
    assert plan.published_controls == ()
    assert plan.actions[1].location_status == "candidate"
    assert plan.actions[2].location is None
    assert "published" in plan.evidence_gaps[-1].lower()


def test_direct_service_changes_the_operating_pattern() -> None:
    match, movement, access, city = _inputs(capacity=12_000, demand=18_000)
    plan = build_traffic_strategy_plan(
        match,
        movement,
        access,
        city,
        default_factor_registry(),
        _recommendations(),
        regional_hubs=[{"name": "Central Station"}],
    )

    assert plan.primary_pattern == "Direct-transit reinforcement"
    assert "venue service" in plan.strategy_basis


def test_large_gap_fails_open_to_multi_hub_operations() -> None:
    match, movement, access, city = _inputs(demand=40_000)
    plan = build_traffic_strategy_plan(
        match,
        movement,
        access,
        city,
        default_factor_registry(),
        _recommendations(),
        regional_hubs=[{"name": "Central Station"}],
    )

    assert plan.required_buses_per_hour_low <= plan.required_buses_per_hour_base <= plan.required_buses_per_hour_high
    assert plan.required_buses_per_hour_base > 60
    assert plan.single_hub_feasibility == "Multiple hubs or demand spreading required"


def test_plan_reconciles_phases_windows_and_outcome_semantics() -> None:
    match, movement, access, city = _inputs()
    plan = build_traffic_strategy_plan(
        match,
        movement,
        access,
        city,
        default_factor_registry(),
        _recommendations(),
        regional_hubs=[{"name": "Central Station"}],
    )

    assert tuple(action.phase for action in plan.actions) == PHASES
    assert plan.arrival_window == "Jun 14, 15:00-16:00 local"
    assert plan.egress_window == "Jun 14, 20:00-21:00 local"
    assert plan.peak_passengers_addressed == 1_500
    baseline_trips = movement.attendance_base * city.private_vehicle_share / city.average_vehicle_occupancy
    assert plan.venue_vehicle_trips_avoided == pytest.approx(baseline_trips - 18_000, abs=0.001)
    assert plan.net_vmt_avoided == 8_000
    assert plan.net_co2e_kg_avoided == 2_000
    assert "EQ-TRAFFIC-SCALE-01" in plan.equation_ids


def test_cross_match_inputs_fail_closed() -> None:
    match, movement, access, city = _inputs()
    with pytest.raises(ValueError, match="same city and match"):
        build_traffic_strategy_plan(
            match,
            replace(movement, match_id="OTHER"),
            access,
            city,
            default_factor_registry(),
            _recommendations(),
        )
