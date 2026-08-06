from __future__ import annotations

from dataclasses import replace

import pytest

from dashboard.mobility_platform.contracts import (
    AccessGapResult,
    EvidenceStatus,
    InterventionPackage,
    MatchEvent,
    MovementScenario,
    SourceReference,
)
from dashboard.models.interventions import (
    BASELINE_PACKAGE,
    CAPITAL_PACKAGE,
    OPERATIONAL_PACKAGE,
    CityInterventionInputs,
    FactorRange,
    default_factor_registry,
    evaluate_intervention,
    named_packages,
    pareto_recommendations,
)


@pytest.fixture
def event_inputs():
    source = SourceReference(
        source="Official match fixture",
        url="https://example.test/matches",
        publisher="Fixture publisher",
        retrieved_at_utc="2026-01-01T00:00:00Z",
        version="fixture-1",
        sha256="fixture",
        license="test",
    )
    match = MatchEvent(
        match_id="ATL-01",
        city="Atlanta",
        venue="Mercedes-Benz Stadium",
        kickoff_local="2026-06-15T15:00:00-04:00",
        stage="group",
        capacity=71_000,
        source=source,
    )
    movement = MovementScenario(
        city="Atlanta",
        match_id="ATL-01",
        status=EvidenceStatus.SCENARIO,
        uncertainty_type="planning range",
        attendance_low=60_000,
        attendance_base=67_000,
        attendance_high=71_000,
        hourly_rows=(),
    )
    access = AccessGapResult(
        city="Atlanta",
        match_id="ATL-01",
        status=EvidenceStatus.DERIVED,
        peak_demand_per_hour=18_000,
        transit_capacity_low=6_000,
        transit_capacity_base=8_000,
        transit_capacity_high=10_000,
        residual_passengers=10_000,
        network_walk_distance_m=500,
        service_span_after_match_min=180,
        route_heat_exposure_c=34.0,
        transit_status=EvidenceStatus.DERIVED,
        walking_status=EvidenceStatus.DERIVED,
        service_span_status=EvidenceStatus.DERIVED,
        heat_status=EvidenceStatus.DERIVED,
        capacity_qualified=True,
    )
    city = CityInterventionInputs(
        city="Atlanta",
        match_id="ATL-01",
        private_vehicle_share=0.55,
        average_vehicle_occupancy=2.0,
        average_private_trip_miles=18.0,
        venue_area_leg_miles=4.0,
        shuttle_round_trip_miles=12.0,
        transit_round_trip_miles=20.0,
        park_ride_feeder_round_trip_miles=12.0,
        bike_access_distance_m=1500.0,
        walk_corridor_length_km=3.0,
        arrival_window_hours=3.0,
    )
    return match, movement, access, city


def evaluate(package, event_inputs, **replacements):
    match, movement, access, city = event_inputs
    movement = replace(movement, **replacements.pop("movement", {}))
    access = replace(access, **replacements.pop("access", {}))
    city = replace(city, **replacements.pop("city", {}))
    factors = replacements.pop("factors", None)
    assert not replacements
    return evaluate_intervention(package, match, movement, access, city, factors)


def test_named_packages_and_custom_package_use_contract_outputs(event_inputs):
    assert set(named_packages()) == {"Baseline", "Operational Package", "Capital Package"}
    for package in (BASELINE_PACKAGE, OPERATIONAL_PACKAGE, CAPITAL_PACKAGE):
        outcome = evaluate(package, event_inputs)
        assert outcome.package == package
        assert outcome.city == "Atlanta"
        assert outcome.status is EvidenceStatus.SCENARIO
    custom = InterventionPackage(
        name="Custom",
        shuttle_buses_per_hour=3,
        bike_hub_spaces=250,
        cooled_walkway_km=0.5,
    )
    assert evaluate(custom, event_inputs).gap_resolved_passengers > 0


def test_zero_intervention_exactly_preserves_baseline(event_inputs):
    outcome = evaluate(BASELINE_PACKAGE, event_inputs)
    expected_trips = 67_000 * 0.55 / 2.0
    assert outcome.gap_resolved_passengers == 0
    assert outcome.net_vmt_low == outcome.net_vmt_base == outcome.net_vmt_high == 0
    assert outcome.net_co2e_kg_low == outcome.net_co2e_kg_base == outcome.net_co2e_kg_high == 0
    assert outcome.cost_low == outcome.cost_base == outcome.cost_high == 0
    assert outcome.heat_exposure_person_hours_avoided == 0
    assert outcome.venue_vehicle_trips_base == pytest.approx(expected_trips)


@pytest.mark.parametrize(
    ("package", "documented_effect"),
    [
        (InterventionPackage(name="shuttle", shuttle_buses_per_hour=5), "mobility"),
        (InterventionPackage(name="frequency", added_transit_departures_per_hour=3), "mobility"),
        (
            InterventionPackage(
                name="park ride",
                park_ride_spaces=500,
                park_ride_feeder_departures_per_hour=8,
            ),
            "mobility",
        ),
        (InterventionPackage(name="bike", bike_hub_spaces=300), "mobility"),
        (InterventionPackage(name="cooling", cooled_walkway_km=1), "heat"),
        (InterventionPackage(name="spreading", arrival_spreading_pct=10), "peak_only"),
    ],
)
def test_every_control_changes_its_documented_effect(package, documented_effect, event_inputs):
    baseline = evaluate(BASELINE_PACKAGE, event_inputs)
    outcome = evaluate(package, event_inputs)
    assert outcome.cost_base > baseline.cost_base
    assert outcome.gap_resolved_passengers > baseline.gap_resolved_passengers
    if documented_effect == "mobility":
        assert outcome.venue_vehicle_trips_base < baseline.venue_vehicle_trips_base
    elif documented_effect == "heat":
        assert outcome.heat_exposure_person_hours_avoided > 0
        assert outcome.venue_vehicle_trips_base < baseline.venue_vehicle_trips_base
    else:
        assert outcome.venue_vehicle_trips_base == baseline.venue_vehicle_trips_base
        assert outcome.net_vmt_base == baseline.net_vmt_base
        assert outcome.net_co2e_kg_base == baseline.net_co2e_kg_base


def test_arrival_spreading_is_behavior_and_shoulder_capacity_limited(event_inputs):
    package = InterventionPackage(name="spreading", arrival_spreading_pct=10)
    outcome = evaluate(package, event_inputs)
    expected = 18_000 * 0.10 * 0.65 * 0.45
    assert outcome.arrival_shifted_pph_base == pytest.approx(expected)
    assert outcome.gap_resolved_passengers == pytest.approx(expected)
    assert outcome.arrival_shifted_pph_base < 18_000 * 0.10


def test_zero_compliance_produces_zero_arrival_spreading(event_inputs):
    factors = replace(
        default_factor_registry(),
        arrival_compliance_rate=FactorRange(0, 0, 0),
    )
    outcome = evaluate(
        InterventionPackage(name="spreading", arrival_spreading_pct=15),
        event_inputs,
        factors=factors,
    )
    assert outcome.arrival_shifted_pph_base == 0
    assert outcome.gap_resolved_passengers == 0


def test_shoulder_capacity_caps_arrival_spreading(event_inputs):
    factors = replace(
        default_factor_registry(),
        arrival_eligible_share=FactorRange(1, 1, 1),
        arrival_compliance_rate=FactorRange(1, 1, 1),
        arrival_shoulder_capacity_share=FactorRange(0.02, 0.02, 0.02),
    )
    outcome = evaluate(
        InterventionPackage(name="spreading", arrival_spreading_pct=100),
        event_inputs,
        factors=factors,
    )
    assert outcome.arrival_shifted_pph_base == 360


def test_more_capacity_cannot_reduce_resolved_gap(event_inputs):
    small = evaluate(
        InterventionPackage(name="small", added_transit_departures_per_hour=2),
        event_inputs,
    )
    large = evaluate(
        InterventionPackage(name="large", added_transit_departures_per_hour=6),
        event_inputs,
    )
    assert large.gap_resolved_passengers >= small.gap_resolved_passengers
    assert large.venue_vehicle_trips_base <= small.venue_vehicle_trips_base


def test_more_cooling_increases_walk_and_heat_benefit(event_inputs):
    short = evaluate(InterventionPackage(name="short", cooled_walkway_km=0.5), event_inputs)
    long = evaluate(InterventionPackage(name="long", cooled_walkway_km=2.0), event_inputs)
    assert long.gap_resolved_passengers >= short.gap_resolved_passengers
    assert long.heat_exposure_person_hours_avoided > short.heat_exposure_person_hours_avoided


def test_bike_benefit_is_distance_limited(event_inputs):
    package = InterventionPackage(name="bike", bike_hub_spaces=1000)
    nearby = evaluate(package, event_inputs, city={"bike_access_distance_m": 1000})
    distant = evaluate(package, event_inputs, city={"bike_access_distance_m": 5000})
    assert nearby.gap_resolved_passengers > 0
    assert distant.gap_resolved_passengers == 0


def test_park_ride_retains_upstream_vmt(event_inputs):
    package = InterventionPackage(
        name="park ride",
        park_ride_spaces=1000,
        park_ride_feeder_departures_per_hour=15,
    )
    short_origin = evaluate(
        package,
        event_inputs,
        city={"average_private_trip_miles": 10, "venue_area_leg_miles": 3},
    )
    long_origin = evaluate(
        package,
        event_inputs,
        city={"average_private_trip_miles": 30, "venue_area_leg_miles": 3},
    )
    longer_venue_leg = evaluate(
        package,
        event_inputs,
        city={"average_private_trip_miles": 30, "venue_area_leg_miles": 8},
    )
    assert short_origin.net_vmt_base == long_origin.net_vmt_base
    assert longer_venue_leg.net_vmt_base > long_origin.net_vmt_base


def test_park_ride_requires_and_costs_feeder_capacity(event_inputs):
    spaces_only = evaluate(
        InterventionPackage(name="spaces only", park_ride_spaces=1000),
        event_inputs,
    )
    feeder = evaluate(
        InterventionPackage(
            name="lot plus feeder",
            park_ride_spaces=1000,
            park_ride_feeder_departures_per_hour=2,
        ),
        event_inputs,
    )

    assert spaces_only.gap_resolved_passengers == 0
    assert feeder.gap_resolved_passengers == pytest.approx(2 * 45 * 0.75)
    assert feeder.operating_cost_base == pytest.approx(2 * 3 * 160)
    assert feeder.cost_base > spaces_only.cost_base


def test_added_shuttle_vmt_and_emissions_are_deducted(event_inputs):
    package = InterventionPackage(name="shuttle", shuttle_buses_per_hour=10)
    outcome = evaluate(package, event_inputs)
    shifted_passengers = 10 * 45 * 0.75 * 3
    avoided_private_vmt = shifted_passengers / 2 * 18
    avoided_private_co2e = avoided_private_vmt * 0.35
    assert 0 < outcome.net_vmt_base < avoided_private_vmt
    assert outcome.net_co2e_kg_base < avoided_private_co2e


def test_inefficient_service_can_have_negative_net_benefit(event_inputs):
    sparse = {
        "attendance_low": 20,
        "attendance_base": 25,
        "attendance_high": 30,
    }
    access = {
        "peak_demand_per_hour": 10,
        "transit_capacity_low": 0,
        "transit_capacity_base": 0,
        "transit_capacity_high": 0,
        "residual_passengers": 10,
    }
    outcome = evaluate(
        InterventionPackage(name="empty shuttle", shuttle_buses_per_hour=5),
        event_inputs,
        movement=sparse,
        access=access,
    )
    assert outcome.net_vmt_base < 0
    assert outcome.net_co2e_kg_base < 0


def test_same_package_responds_to_city_evidence(event_inputs):
    package = InterventionPackage(
        name="city-sensitive",
        shuttle_buses_per_hour=5,
        bike_hub_spaces=500,
        cooled_walkway_km=1,
    )
    atlanta = evaluate(package, event_inputs)
    alternate = evaluate(
        package,
        event_inputs,
        city={
            "average_private_trip_miles": 30,
            "shuttle_round_trip_miles": 20,
            "bike_access_distance_m": 4000,
            "walk_corridor_length_km": 5,
        },
        access={"route_heat_exposure_c": 27},
    )
    assert atlanta.gap_resolved_passengers != alternate.gap_resolved_passengers
    assert atlanta.net_co2e_kg_base != alternate.net_co2e_kg_base
    assert atlanta.heat_exposure_person_hours_avoided != alternate.heat_exposure_person_hours_avoided


def test_outputs_keep_cost_capacity_and_vehicle_trips_nonnegative(event_inputs):
    outcome = evaluate(CAPITAL_PACKAGE, event_inputs)
    assert outcome.gap_resolved_passengers >= 0
    assert min(
        outcome.venue_vehicle_trips_low,
        outcome.venue_vehicle_trips_base,
        outcome.venue_vehicle_trips_high,
    ) >= 0
    assert min(outcome.cost_low, outcome.cost_base, outcome.cost_high) >= 0
    assert outcome.cost_low <= outcome.cost_base <= outcome.cost_high


def test_pareto_recommendations_are_contract_complete(event_inputs):
    match, movement, access, city = event_inputs
    recommendations = pareto_recommendations(match, movement, access, city)
    assert recommendations
    for recommendation in recommendations:
        assert recommendation.city == "Atlanta"
        assert recommendation.match_id == "ATL-01"
        if recommendation.intervention == "Arrival spreading and curb management":
            assert recommendation.status is EvidenceStatus.PARTIAL
            assert not recommendation.evidence_qualified
        else:
            assert recommendation.status in {EvidenceStatus.SCENARIO, EvidenceStatus.PARTIAL}
        assert recommendation.cost_low <= recommendation.cost_base <= recommendation.cost_high
        assert recommendation.gap_resolved_passengers >= 0
        assert recommendation.lead_time_band
        assert recommendation.responsible_actor
        assert recommendation.dependencies
        assert "Nondominated" in recommendation.rationale
        assert "not a selected optimum" in recommendation.rationale
        assert recommendation.cost_basis
        assert recommendation.equation_ids


def test_recommendation_list_places_qualified_options_before_exploratory(event_inputs):
    match, movement, access, city = event_inputs
    recommendations = pareto_recommendations(match, movement, access, city)
    flags = [item.evidence_qualified for item in recommendations]
    assert flags == sorted(flags, reverse=True)
    arrival = next(
        item
        for item in recommendations
        if item.intervention == "Arrival spreading and curb management"
    )
    assert arrival.evidence_quality == "low"
    assert "curb-throughput" in arrival.evidence_reason


def test_factor_ranges_and_city_inputs_validate_physical_bounds(event_inputs):
    with pytest.raises(ValueError):
        FactorRange(1, 3, 2)
    _, _, _, city = event_inputs
    with pytest.raises(ValueError):
        replace(city, average_vehicle_occupancy=0)
    with pytest.raises(ValueError):
        replace(city, venue_area_leg_miles=city.average_private_trip_miles + 1)
    assert default_factor_registry().registry_version
