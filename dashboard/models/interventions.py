"""Pure, evidence-responsive intervention evaluation for contract 0.3.

The functions in this module do not read files or mutate application state.  They
turn match, movement, access, city, and factor inputs into the shared contract
outputs used by the dashboard and downloadable scenarios.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from math import inf
from typing import Any, Iterable, Mapping

from dashboard.mobility_platform.contracts import (
    AccessGapResult,
    EvidenceStatus,
    InterventionOutcome,
    InterventionPackage,
    InvestmentRecommendation,
    MatchEvent,
    MovementScenario,
)
from dashboard.models.equations import equation_ids
from dashboard.models.recommendation_policy import (
    assess_evidence,
    lead_time_rank,
    measure_policy,
)


@dataclass(frozen=True)
class FactorRange:
    """A nonnegative low/base/high planning range."""

    low: float
    base: float
    high: float

    def __post_init__(self) -> None:
        if self.low < 0 or self.base < 0 or self.high < 0:
            raise ValueError("Factor ranges must be nonnegative")
        if not self.low <= self.base <= self.high:
            raise ValueError("Factor ranges must satisfy low <= base <= high")

    def value(self, case: str) -> float:
        if case not in {"low", "base", "high"}:
            raise ValueError(f"Unknown uncertainty case: {case}")
        return float(getattr(self, case))


@dataclass(frozen=True)
class CityInterventionInputs:
    """City and corridor evidence needed to evaluate a package.

    Distances are round-trip miles unless the field explicitly says otherwise.
    Shares are fractions in the inclusive range [0, 1].
    """

    city: str
    match_id: str
    private_vehicle_share: float
    average_vehicle_occupancy: float
    average_private_trip_miles: float
    venue_area_leg_miles: float
    shuttle_round_trip_miles: float
    transit_round_trip_miles: float
    park_ride_feeder_round_trip_miles: float
    bike_access_distance_m: float
    walk_corridor_length_km: float
    arrival_window_hours: float = 3.0
    baseline_walk_share: float = 0.05

    def __post_init__(self) -> None:
        if not 0 <= self.private_vehicle_share <= 1:
            raise ValueError("private_vehicle_share must be between zero and one")
        if not 0 <= self.baseline_walk_share <= 1:
            raise ValueError("baseline_walk_share must be between zero and one")
        if self.average_vehicle_occupancy <= 0:
            raise ValueError("average_vehicle_occupancy must be greater than zero")
        positive = (
            "average_private_trip_miles",
            "venue_area_leg_miles",
            "shuttle_round_trip_miles",
            "transit_round_trip_miles",
            "park_ride_feeder_round_trip_miles",
            "bike_access_distance_m",
            "walk_corridor_length_km",
            "arrival_window_hours",
        )
        if any(float(getattr(self, name)) <= 0 for name in positive):
            raise ValueError("City distance and duration inputs must be greater than zero")
        if self.venue_area_leg_miles > self.average_private_trip_miles:
            raise ValueError("venue_area_leg_miles cannot exceed the full private trip")


@dataclass(frozen=True)
class InterventionFactorRegistry:
    """Versioned low/base/high planning factors supplied by the evidence pipeline."""

    registry_version: str
    artifact_sha256: str
    source_version: str
    shuttle_passengers_per_bus: FactorRange
    transit_passengers_per_departure: FactorRange
    service_load_factor: FactorRange
    park_ride_occupancy: FactorRange
    park_ride_utilization: FactorRange
    bike_hub_turnover: FactorRange
    bike_uptake_share: FactorRange
    walk_uptake_per_covered_km: FactorRange
    maximum_new_walk_share: FactorRange
    private_vehicle_co2e_kg_per_mile: FactorRange
    service_vehicle_co2e_kg_per_mile: FactorRange
    route_heat_reduction_c: FactorRange
    heat_exposure_hours_per_walker: FactorRange
    shuttle_cost_per_bus_hour: FactorRange
    transit_cost_per_departure: FactorRange
    park_ride_cost_per_space: FactorRange
    bike_hub_cost_per_space: FactorRange
    cooled_walkway_cost_per_km: FactorRange
    arrival_management_cost_per_pct: FactorRange
    arrival_eligible_share: FactorRange
    arrival_compliance_rate: FactorRange
    arrival_shoulder_capacity_share: FactorRange
    park_ride_reuse_events: FactorRange
    bike_hub_reuse_events: FactorRange
    cooled_walkway_reuse_events: FactorRange
    bike_max_distance_m: float = 5000.0

    def __post_init__(self) -> None:
        if not self.registry_version.strip():
            raise ValueError("registry_version is required")
        if len(self.artifact_sha256) != 64:
            raise ValueError("artifact_sha256 must be a SHA-256 digest")
        if not self.source_version.strip():
            raise ValueError("source_version is required")
        if self.bike_max_distance_m <= 0:
            raise ValueError("bike_max_distance_m must be greater than zero")


def default_factor_registry() -> InterventionFactorRegistry:
    """Return transparent MVP planning ranges.

    These defaults are fixtures, not observed local performance. Production
    callers should inject the pinned factor registry produced by W1.
    """

    return InterventionFactorRegistry(
        registry_version="contract-0.3-planning-fixture",
        artifact_sha256="0" * 64,
        source_version="unit-test-fixture",
        shuttle_passengers_per_bus=FactorRange(35, 45, 55),
        transit_passengers_per_departure=FactorRange(90, 140, 200),
        service_load_factor=FactorRange(0.60, 0.75, 0.90),
        park_ride_occupancy=FactorRange(1.5, 1.8, 2.1),
        park_ride_utilization=FactorRange(0.55, 0.70, 0.85),
        bike_hub_turnover=FactorRange(0.70, 0.90, 1.10),
        bike_uptake_share=FactorRange(0.01, 0.025, 0.05),
        walk_uptake_per_covered_km=FactorRange(0.002, 0.005, 0.009),
        maximum_new_walk_share=FactorRange(0.01, 0.03, 0.06),
        private_vehicle_co2e_kg_per_mile=FactorRange(0.25, 0.35, 0.48),
        service_vehicle_co2e_kg_per_mile=FactorRange(1.0, 1.35, 1.8),
        route_heat_reduction_c=FactorRange(0.5, 1.5, 2.5),
        heat_exposure_hours_per_walker=FactorRange(0.25, 0.50, 0.75),
        shuttle_cost_per_bus_hour=FactorRange(110, 160, 230),
        transit_cost_per_departure=FactorRange(240, 400, 650),
        park_ride_cost_per_space=FactorRange(3500, 7000, 14000),
        bike_hub_cost_per_space=FactorRange(350, 700, 1300),
        cooled_walkway_cost_per_km=FactorRange(750_000, 1_600_000, 3_200_000),
        arrival_management_cost_per_pct=FactorRange(1200, 2500, 5000),
        arrival_eligible_share=FactorRange(0.40, 0.65, 0.85),
        arrival_compliance_rate=FactorRange(0.20, 0.45, 0.70),
        arrival_shoulder_capacity_share=FactorRange(0.03, 0.08, 0.15),
        park_ride_reuse_events=FactorRange(15, 30, 60),
        bike_hub_reuse_events=FactorRange(20, 40, 80),
        cooled_walkway_reuse_events=FactorRange(30, 60, 120),
    )


FACTOR_UNITS = {
    "shuttle_passengers_per_bus": "passengers / bus",
    "transit_passengers_per_departure": "passengers / departure",
    "service_load_factor": "fraction",
    "park_ride_occupancy": "passengers / parked vehicle",
    "park_ride_utilization": "fraction",
    "bike_hub_turnover": "passengers / space / event",
    "bike_uptake_share": "fraction of attendance",
    "walk_uptake_per_covered_km": "fraction of attendance / covered km",
    "maximum_new_walk_share": "fraction of attendance",
    "private_vehicle_co2e_kg_per_mile": "kg CO2e / vehicle-mile",
    "service_vehicle_co2e_kg_per_mile": "kg CO2e / vehicle-mile",
    "route_heat_reduction_c": "degrees C",
    "heat_exposure_hours_per_walker": "person-hours / walker",
    "shuttle_cost_per_bus_hour": "2026 planning USD / bus-hour",
    "transit_cost_per_departure": "2026 planning USD / departure",
    "park_ride_cost_per_space": "2026 planning USD / space",
    "bike_hub_cost_per_space": "2026 planning USD / space",
    "cooled_walkway_cost_per_km": "2026 planning USD / km",
    "arrival_management_cost_per_pct": "2026 planning USD / percentage point",
    "arrival_eligible_share": "fraction of peak arrivals",
    "arrival_compliance_rate": "fraction of eligible arrivals",
    "arrival_shoulder_capacity_share": "fraction of peak demand",
    "park_ride_reuse_events": "event uses",
    "bike_hub_reuse_events": "event uses",
    "cooled_walkway_reuse_events": "event uses",
    "bike_max_distance_m": "meters",
}


def factor_registry_from_snapshot(snapshot: Mapping[str, Any]) -> InterventionFactorRegistry:
    """Strictly adapt one validated factor snapshot to the intervention model."""

    from dashboard.pipeline.public.common import artifact_hash

    if snapshot.get("snapshot_kind") != "planning_factor_registry":
        raise ValueError("Production interventions require a planning_factor_registry snapshot")
    digest = str(snapshot.get("artifact_sha256") or "")
    if digest != artifact_hash(dict(snapshot)):
        raise ValueError("Factor registry artifact hash mismatch")
    factors = snapshot.get("factors")
    sources = snapshot.get("sources")
    if not isinstance(factors, Mapping) or not isinstance(sources, Mapping):
        raise ValueError("Factor registry requires factors and source references")
    missing = sorted(set(FACTOR_UNITS) - set(factors))
    if missing:
        raise ValueError("Factor registry is incomplete: " + ", ".join(missing))

    ranges: dict[str, FactorRange] = {}
    for name, expected_unit in FACTOR_UNITS.items():
        row = factors[name]
        if not isinstance(row, Mapping):
            raise ValueError(f"Factor {name} must be an object")
        if str(row.get("unit")) != expected_unit:
            raise ValueError(f"Factor {name} must use {expected_unit}")
        source_ids = row.get("source_ids")
        if not isinstance(source_ids, list) or not source_ids or any(source_id not in sources for source_id in source_ids):
            raise ValueError(f"Factor {name} has invalid source references")
        if not str(row.get("basis") or "").strip():
            raise ValueError(f"Factor {name} requires a written basis")
        ranges[name] = FactorRange(float(row["low"]), float(row["base"]), float(row["high"]))

    return InterventionFactorRegistry(
        registry_version=str(snapshot.get("schema_version") or snapshot.get("generated_at_utc") or "unversioned"),
        artifact_sha256=digest,
        source_version=", ".join(sorted(str(source["version"]) for source in sources.values())),
        bike_max_distance_m=ranges.pop("bike_max_distance_m").base,
        **ranges,
    )


BASELINE_PACKAGE = InterventionPackage(name="Baseline")
OPERATIONAL_PACKAGE = InterventionPackage(
    name="Operational Package",
    shuttle_buses_per_hour=12,
    added_transit_departures_per_hour=6,
    arrival_spreading_pct=20,
)
CAPITAL_PACKAGE = InterventionPackage(
    name="Capital Package",
    shuttle_buses_per_hour=8,
    added_transit_departures_per_hour=4,
    park_ride_spaces=1500,
    park_ride_feeder_departures_per_hour=19,
    bike_hub_spaces=1000,
    cooled_walkway_km=2.0,
    arrival_spreading_pct=15,
)


def named_packages() -> dict[str, InterventionPackage]:
    """Return fresh mapping for the three product scenarios."""

    return {
        BASELINE_PACKAGE.name: BASELINE_PACKAGE,
        OPERATIONAL_PACKAGE.name: OPERATIONAL_PACKAGE,
        CAPITAL_PACKAGE.name: CAPITAL_PACKAGE,
    }


@dataclass(frozen=True)
class _CaseResult:
    gap_resolved: float
    venue_vehicle_trips: float
    net_vmt: float
    net_co2e_kg: float
    heat_person_hours_avoided: float
    cost: float
    capital_cost: float
    operating_cost: float
    arrival_shifted_pph: float


def _validate_inputs(
    match: MatchEvent,
    movement: MovementScenario,
    access: AccessGapResult,
    city: CityInterventionInputs,
) -> None:
    identities = {
        (match.city, match.match_id),
        (movement.city, movement.match_id),
        (access.city, access.match_id),
        (city.city, city.match_id),
    }
    if len(identities) != 1:
        raise ValueError("Match, movement, access, and city inputs must describe the same event")
    if match.capacity < 0 or min(
        movement.attendance_low, movement.attendance_base, movement.attendance_high
    ) < 0:
        raise ValueError("Capacity and attendance must be nonnegative")
    if not movement.attendance_low <= movement.attendance_base <= movement.attendance_high:
        raise ValueError("Attendance must satisfy low <= base <= high")
    numeric_access = (
        access.peak_demand_per_hour,
        access.transit_capacity_low,
        access.transit_capacity_base,
        access.transit_capacity_high,
        access.residual_passengers,
    )
    if min(numeric_access) < 0:
        raise ValueError("Access demand, capacity, and residual values must be nonnegative")


def _is_zero_package(package: InterventionPackage) -> bool:
    return all(
        float(getattr(package, field.name)) == 0
        for field in fields(package)
        if field.name != "name"
    )


def _case_result(
    case: str,
    package: InterventionPackage,
    movement: MovementScenario,
    access: AccessGapResult,
    city: CityInterventionInputs,
    factors: InterventionFactorRegistry,
) -> _CaseResult:
    attendance = float(getattr(movement, f"attendance_{case}"))
    base_attendance = max(float(movement.attendance_base), 1.0)
    peak_demand = access.peak_demand_per_hour * attendance / base_attendance
    transit_capacity = float(getattr(access, f"transit_capacity_{case}"))
    residual_peak = (
        access.residual_passengers
        if case == "base"
        else max(peak_demand - transit_capacity, 0.0)
    )
    occupancy = city.average_vehicle_occupancy
    arrival_hours = city.arrival_window_hours
    private_passengers = attendance * city.private_vehicle_share
    baseline_vehicle_trips = private_passengers / occupancy

    load = factors.service_load_factor.value(case)
    shuttle_per_hour = (
        package.shuttle_buses_per_hour
        * factors.shuttle_passengers_per_bus.value(case)
        * load
    )
    transit_per_hour = (
        package.added_transit_departures_per_hour
        * factors.transit_passengers_per_departure.value(case)
        * load
    )
    park_space_passengers = (
        package.park_ride_spaces
        * factors.park_ride_occupancy.value(case)
        * factors.park_ride_utilization.value(case)
    )
    feeder_capacity = max(
        factors.shuttle_passengers_per_bus.value(case) * load,
        1.0,
    )
    park_feeder_per_hour = (
        package.park_ride_feeder_departures_per_hour * feeder_capacity
    )
    park_per_hour = min(park_space_passengers / arrival_hours, park_feeder_per_hour)
    park_passengers = park_per_hour * arrival_hours

    bike_distance_factor = max(
        0.0, 1.0 - city.bike_access_distance_m / factors.bike_max_distance_m
    )
    bike_passengers = min(
        package.bike_hub_spaces * factors.bike_hub_turnover.value(case),
        attendance * factors.bike_uptake_share.value(case) * bike_distance_factor,
    )
    bike_per_hour = bike_passengers / arrival_hours

    cooled_coverage = min(package.cooled_walkway_km / city.walk_corridor_length_km, 1.0)
    heat_c = access.route_heat_exposure_c
    heat_need = 0.0 if heat_c is None else min(max((heat_c - 24.0) / 12.0, 0.0), 1.0)
    new_walk_share = min(
        package.cooled_walkway_km * factors.walk_uptake_per_covered_km.value(case),
        factors.maximum_new_walk_share.value(case),
    )
    walk_passengers = attendance * new_walk_share * cooled_coverage * heat_need
    walk_per_hour = walk_passengers / arrival_hours

    requested_spreading = peak_demand * package.arrival_spreading_pct / 100.0
    behavior_limited_spreading = (
        requested_spreading
        * factors.arrival_eligible_share.value(case)
        * factors.arrival_compliance_rate.value(case)
    )
    shoulder_capacity = peak_demand * factors.arrival_shoulder_capacity_share.value(case)
    spreading_peak_reduction = min(
        behavior_limited_spreading,
        shoulder_capacity,
    )
    physical_peak_capacity = shuttle_per_hour + transit_per_hour + park_per_hour + bike_per_hour + walk_per_hour
    gap_resolved = min(residual_peak, physical_peak_capacity + spreading_peak_reduction)

    total_modal_shift = min(
        private_passengers,
        shuttle_per_hour * arrival_hours
        + transit_per_hour * arrival_hours
        + park_passengers
        + bike_passengers
        + walk_passengers,
    )
    venue_vehicle_trips = max(baseline_vehicle_trips - total_modal_shift / occupancy, 0.0)

    non_park_shift = max(total_modal_shift - min(park_passengers, total_modal_shift), 0.0)
    avoided_private_vmt = (
        non_park_shift / occupancy * city.average_private_trip_miles
        + min(park_passengers, total_modal_shift) / occupancy * city.venue_area_leg_miles
    )
    shuttle_vmt = package.shuttle_buses_per_hour * arrival_hours * city.shuttle_round_trip_miles
    transit_vmt = (
        package.added_transit_departures_per_hour * arrival_hours * city.transit_round_trip_miles
    )
    park_feeder_trips = park_passengers / feeder_capacity
    park_feeder_vmt = park_feeder_trips * city.park_ride_feeder_round_trip_miles
    added_service_vmt = shuttle_vmt + transit_vmt + park_feeder_vmt
    net_vmt = avoided_private_vmt - added_service_vmt
    net_co2e = (
        avoided_private_vmt * factors.private_vehicle_co2e_kg_per_mile.value(case)
        - added_service_vmt * factors.service_vehicle_co2e_kg_per_mile.value(
            "high" if case == "low" else "low" if case == "high" else "base"
        )
    )

    heat_reduction_fraction = (
        0.0
        if heat_c is None or heat_c <= 24.0
        else min(factors.route_heat_reduction_c.value(case) / (heat_c - 24.0), 1.0)
    )
    heat_person_hours = (
        walk_passengers
        * factors.heat_exposure_hours_per_walker.value(case)
        * heat_reduction_fraction
        * cooled_coverage
    )
    capital_cost = (
        package.park_ride_spaces * factors.park_ride_cost_per_space.value(case)
        + package.bike_hub_spaces * factors.bike_hub_cost_per_space.value(case)
        + package.cooled_walkway_km * factors.cooled_walkway_cost_per_km.value(case)
    )
    operating_cost = (
        package.shuttle_buses_per_hour
        * arrival_hours
        * factors.shuttle_cost_per_bus_hour.value(case)
        + package.added_transit_departures_per_hour
        * arrival_hours
        * factors.transit_cost_per_departure.value(case)
        + package.park_ride_feeder_departures_per_hour
        * arrival_hours
        * factors.shuttle_cost_per_bus_hour.value(case)
        + package.arrival_spreading_pct * factors.arrival_management_cost_per_pct.value(case)
    )
    cost = capital_cost + operating_cost
    return _CaseResult(
        gap_resolved=gap_resolved,
        venue_vehicle_trips=venue_vehicle_trips,
        net_vmt=net_vmt,
        net_co2e_kg=net_co2e,
        heat_person_hours_avoided=heat_person_hours,
        cost=cost,
        capital_cost=capital_cost,
        operating_cost=operating_cost,
        arrival_shifted_pph=spreading_peak_reduction,
    )


def evaluate_intervention(
    package: InterventionPackage,
    match: MatchEvent,
    movement: MovementScenario,
    access: AccessGapResult,
    city: CityInterventionInputs,
    factors: InterventionFactorRegistry | None = None,
) -> InterventionOutcome:
    """Evaluate a named or custom intervention package.

    Positive net VMT/CO2e values mean avoided impacts. Negative values are
    deliberately retained when added service performs worse than avoided car use.
    """

    _validate_inputs(match, movement, access, city)
    registry = factors or default_factor_registry()
    cases = {
        case: _case_result(case, package, movement, access, city, registry)
        for case in ("low", "base", "high")
    }
    base = cases["base"]
    assumptions = (
        f"Factor registry: {registry.registry_version}.",
        f"Factor artifact SHA-256: {registry.artifact_sha256}.",
        f"Factor source versions: {registry.source_version}.",
        f"Private-mode share: {city.private_vehicle_share:.3f}; vehicle occupancy: {city.average_vehicle_occupancy:.2f} passengers.",
        f"Private round-trip distance: {city.average_private_trip_miles:.2f} miles; venue-area leg: {city.venue_area_leg_miles:.2f} miles.",
        f"Bike access distance: {city.bike_access_distance_m:.0f} m; base uptake threshold: {registry.bike_max_distance_m:.0f} m.",
        "Capacity is potential passenger throughput, not observed ridership or mode shift.",
        (
            "Park-and-ride retains upstream private travel, avoids only the venue-area leg, "
            "and is capped by explicitly scheduled feeder departures (EQ-PARK-RIDE-01)."
        ),
        "Park-and-ride feeder departures are costed as bus-hours over the arrival window.",
        "Arrival spreading moves peak demand to shoulder periods and does not change total travel or emissions.",
        (
            "Arrival spreading equation EQ-SPREAD-01 applies requested share × eligible share × compliance, "
            "capped by shoulder-period capacity and the residual gap."
        ),
        (
            "Arrival assumptions (base): eligible share "
            f"{registry.arrival_eligible_share.base:.3f}; compliance "
            f"{registry.arrival_compliance_rate.base:.3f}; shoulder capacity "
            f"{registry.arrival_shoulder_capacity_share.base:.3f} of peak demand."
        ),
        "Positive net values are avoided impacts; negative values indicate added service impacts exceed avoided driving.",
        f"Access evidence status: {access.status.value}; transit: {access.transit_status.value}; walking: {access.walking_status.value}; heat: {access.heat_status.value}; movement: {movement.status.value}.",
    )
    if access.route_heat_exposure_c is None and package.cooled_walkway_km:
        assumptions += ("Cooling has no quantified effect because route heat evidence is unavailable.",)
    if _is_zero_package(package):
        assumptions += ("Zero-intervention baseline preserves all baseline physical outcomes.",)

    return InterventionOutcome(
        city=match.city,
        match_id=match.match_id,
        package=package,
        status=EvidenceStatus.SCENARIO,
        gap_resolved_passengers=round(base.gap_resolved, 3),
        venue_vehicle_trips_low=round(cases["low"].venue_vehicle_trips, 3),
        venue_vehicle_trips_base=round(base.venue_vehicle_trips, 3),
        venue_vehicle_trips_high=round(cases["high"].venue_vehicle_trips, 3),
        net_vmt_low=round(cases["low"].net_vmt, 3),
        net_vmt_base=round(base.net_vmt, 3),
        net_vmt_high=round(cases["high"].net_vmt, 3),
        net_co2e_kg_low=round(cases["low"].net_co2e_kg, 3),
        net_co2e_kg_base=round(base.net_co2e_kg, 3),
        net_co2e_kg_high=round(cases["high"].net_co2e_kg, 3),
        heat_exposure_person_hours_avoided=round(base.heat_person_hours_avoided, 3),
        cost_low=round(cases["low"].cost, 2),
        cost_base=round(base.cost, 2),
        cost_high=round(cases["high"].cost, 2),
        capital_cost_low=round(cases["low"].capital_cost, 2),
        capital_cost_base=round(base.capital_cost, 2),
        capital_cost_high=round(cases["high"].capital_cost, 2),
        operating_cost_low=round(cases["low"].operating_cost, 2),
        operating_cost_base=round(base.operating_cost, 2),
        operating_cost_high=round(cases["high"].operating_cost, 2),
        arrival_shifted_pph_low=round(cases["low"].arrival_shifted_pph, 3),
        arrival_shifted_pph_base=round(base.arrival_shifted_pph, 3),
        arrival_shifted_pph_high=round(cases["high"].arrival_shifted_pph, 3),
        assumptions=assumptions,
    )


def recommendation_candidates() -> tuple[InterventionPackage, ...]:
    """Return comparable single-measure packages for Pareto screening."""

    return (
        InterventionPackage(name="Shuttle service", shuttle_buses_per_hour=10),
        InterventionPackage(name="Added transit frequency", added_transit_departures_per_hour=6),
        InterventionPackage(
            name="Park-and-ride feeder service",
            park_ride_spaces=1200,
            park_ride_feeder_departures_per_hour=15,
        ),
        InterventionPackage(name="Bike and micromobility hubs", bike_hub_spaces=800),
        InterventionPackage(name="Cooled walking corridors", cooled_walkway_km=2.0),
        InterventionPackage(
            name="Arrival spreading and curb management", arrival_spreading_pct=15
        ),
    )


def _comparison_cost(
    outcome: InterventionOutcome,
    factors: InterventionFactorRegistry,
    case: str = "base",
) -> float:
    policy = measure_policy(outcome.package.name)
    capital = float(getattr(outcome, f"capital_cost_{case}"))
    operating = float(getattr(outcome, f"operating_cost_{case}"))
    if policy.reuse_factor:
        reuse_range = getattr(factors, policy.reuse_factor)
        reuse_events = max(reuse_range.value(case), 1.0)
        capital /= reuse_events
    return capital + operating


def _dominates(
    left: InterventionOutcome,
    right: InterventionOutcome,
    access: AccessGapResult,
    factors: InterventionFactorRegistry,
) -> bool:
    left_evidence = assess_evidence(left.package.name, access)
    right_evidence = assess_evidence(right.package.name, access)
    if not left_evidence.screening_eligible and right_evidence.screening_eligible:
        return False
    left_cpp = _comparison_cost(left, factors) / left.gap_resolved_passengers if left.gap_resolved_passengers > 0 else inf
    right_cpp = _comparison_cost(right, factors) / right.gap_resolved_passengers if right.gap_resolved_passengers > 0 else inf
    no_worse = (
        left.gap_resolved_passengers >= right.gap_resolved_passengers
        and left.net_co2e_kg_base >= right.net_co2e_kg_base
        and left_cpp <= right_cpp
        and lead_time_rank(left.package.name) <= lead_time_rank(right.package.name)
        and left.heat_exposure_person_hours_avoided
        >= right.heat_exposure_person_hours_avoided
    )
    strictly_better = (
        left.gap_resolved_passengers > right.gap_resolved_passengers
        or left.net_co2e_kg_base > right.net_co2e_kg_base
        or left_cpp < right_cpp
        or lead_time_rank(left.package.name) < lead_time_rank(right.package.name)
        or left.heat_exposure_person_hours_avoided
        > right.heat_exposure_person_hours_avoided
        or left_evidence.screening_eligible > right_evidence.screening_eligible
    )
    return no_worse and strictly_better


def pareto_recommendations(
    match: MatchEvent,
    movement: MovementScenario,
    access: AccessGapResult,
    city: CityInterventionInputs,
    factors: InterventionFactorRegistry | None = None,
    candidates: Iterable[InterventionPackage] | None = None,
) -> list[InvestmentRecommendation]:
    """Return the nondominated investment choices without a composite optimum."""

    registry = factors or default_factor_registry()
    packages = tuple(candidates or recommendation_candidates())
    outcomes = [
        evaluate_intervention(package, match, movement, access, city, registry)
        for package in packages
    ]
    frontier = [
        outcome
        for outcome in outcomes
        if outcome.gap_resolved_passengers > 0
        and not any(
            _dominates(other, outcome, access, registry)
            for other in outcomes
            if other is not outcome
        )
    ]
    recommendations: list[InvestmentRecommendation] = []
    for outcome in frontier:
        name = outcome.package.name
        policy = measure_policy(name)
        evidence = assess_evidence(name, access)
        gap = outcome.gap_resolved_passengers
        comparison_cost = _comparison_cost(outcome, registry)
        cpp = comparison_cost / gap if gap > 0 else None
        recommendations.append(
            InvestmentRecommendation(
                city=outcome.city,
                match_id=outcome.match_id,
                intervention=name,
                rationale=(
                    f"Nondominated planning option resolving {gap:,.0f} peak passengers "
                    f"with {outcome.net_co2e_kg_base:,.0f} kg net CO2e in the base case. "
                    "It is not a selected optimum. "
                    + evidence.reason
                ),
                status=(
                    EvidenceStatus.SCENARIO
                    if evidence.screening_eligible
                    else EvidenceStatus.PARTIAL
                ),
                scope=policy.scope,
                cost_low=outcome.cost_low,
                cost_base=outcome.cost_base,
                cost_high=outcome.cost_high,
                gap_resolved_passengers=gap,
                cost_per_passenger=round(cpp, 2) if cpp is not None else None,
                net_co2e_kg=outcome.net_co2e_kg_base,
                lead_time_band=policy.lead_time_band,
                responsible_actor=policy.responsible_actor,
                dependencies=policy.dependencies,
                comparison_cost_base=round(comparison_cost, 2),
                cost_basis=policy.comparison_cost_basis,
                evidence_quality=evidence.quality,
                evidence_qualified=evidence.screening_eligible,
                evidence_reason=evidence.reason,
                heat_person_hours_avoided=outcome.heat_exposure_person_hours_avoided,
                equation_ids=equation_ids(),
            )
        )
    return sorted(
        recommendations,
        key=lambda item: (
            not item.evidence_qualified,
            item.intervention,
        ),
    )
