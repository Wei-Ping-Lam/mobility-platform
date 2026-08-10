"""Pure, evidence-gated match-day traffic strategy generation.

The v1 strategy artifact combines published operating-plan facts with derived
GTFS, movement, access, and intervention evidence.  Exact controls are retained
only when an official overlay supplies them; the model never invents named road
closures, curb locations, or engineering approvals.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from math import ceil
from typing import Any, Mapping, Sequence

from dashboard.mobility_platform.contracts import (
    AccessGapResult,
    EvidenceStatus,
    InvestmentRecommendation,
    MatchEvent,
    MovementScenario,
)
from dashboard.models.interventions import (
    CityInterventionInputs,
    InterventionFactorRegistry,
)
from dashboard.models.strategy_calibration import (
    StrategyFeatures,
    classify_strategy,
    compare_with_benchmark,
)

PHASES = ("Before match", "Arrival and transfer", "Curb and last mile", "Egress", "Contingency")
SINGLE_HUB_BUS_LIMIT_PER_HOUR = 60
QUEUE_TRIGGER_MINUTES = 15


@dataclass(frozen=True)
class TrafficStrategyAction:
    """One time-phased action in a match-day operating strategy."""

    phase: str
    title: str
    instruction: str
    time_window: str
    trigger: str
    location: str | None
    location_status: str
    evidence_status: EvidenceStatus
    source_ids: tuple[str, ...] = field(default_factory=tuple)
    dependencies: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ValueError(f"Unsupported traffic strategy phase: {self.phase}")
        if self.location_status not in {"published", "candidate", "not location-specific", "unavailable"}:
            raise ValueError(f"Unsupported location status: {self.location_status}")
        if not self.title.strip() or not self.instruction.strip():
            raise ValueError("Traffic strategy actions require a title and instruction")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence_status"] = self.evidence_status.value
        data["source_ids"] = list(self.source_ids)
        data["dependencies"] = list(self.dependencies)
        return data


@dataclass(frozen=True)
class TrafficStrategyPlan:
    """Serializable v1 operating strategy for one host-city match."""

    schema_version: str
    city: str
    match_id: str
    primary_pattern: str
    predicted_pattern: str
    prediction_strength: str
    prediction_reasons: tuple[str, ...]
    prediction_features: Mapping[str, Any]
    benchmark_pattern: str | None
    benchmark_agreement: str
    benchmark_source_url: str | None
    benchmark_evidence_level: str | None
    strategy_basis: str
    status: EvidenceStatus
    summary: str
    arrival_window: str
    egress_window: str
    regional_hub_name: str | None
    regional_hub_status: str
    regional_hub_lat: float | None
    regional_hub_lon: float | None
    required_buses_per_hour_low: int
    required_buses_per_hour_base: int
    required_buses_per_hour_high: int
    proposed_capacity_per_hour_base: float
    single_hub_feasibility: str
    peak_passengers_addressed: float | None
    venue_vehicle_trips_avoided: float | None
    net_vmt_avoided: float | None
    net_co2e_kg_avoided: float | None
    official_plan_available: bool
    published_controls: tuple[str, ...]
    actions: tuple[TrafficStrategyAction, ...]
    evidence_gaps: tuple[str, ...]
    assumptions: tuple[str, ...]
    equation_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        requirements = (
            self.required_buses_per_hour_low,
            self.required_buses_per_hour_base,
            self.required_buses_per_hour_high,
        )
        if min(requirements) < 0 or tuple(sorted(requirements)) != requirements:
            raise ValueError("Bus requirements must be nonnegative and ordered low <= base <= high")
        if self.proposed_capacity_per_hour_base < 0:
            raise ValueError("Proposed capacity must be nonnegative")
        if len(self.actions) != len(PHASES) or tuple(action.phase for action in self.actions) != PHASES:
            raise ValueError("A v1 traffic plan requires exactly one action for each ordered phase")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["published_controls"] = list(self.published_controls)
        data["prediction_reasons"] = list(self.prediction_reasons)
        data["prediction_features"] = dict(self.prediction_features)
        data["actions"] = [action.to_dict() for action in self.actions]
        data["evidence_gaps"] = list(self.evidence_gaps)
        data["assumptions"] = list(self.assumptions)
        return data


def _window(rows: Sequence[Mapping[str, Any]], field: str) -> str:
    timestamps: list[datetime] = []
    for row in rows:
        try:
            value = float(row.get(field) or 0)
            timestamp = datetime.fromisoformat(str(row.get("timestamp_local")))
        except (TypeError, ValueError):
            continue
        if value > 0:
            timestamps.append(timestamp)
    if not timestamps:
        return "Window unavailable"
    start, end = min(timestamps), max(timestamps)
    if start.date() == end.date():
        return f"{start:%b %d, %H:%M}-{end:%H:%M} local"
    return f"{start:%b %d, %H:%M}-{end:%b %d, %H:%M} local"


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def _case_gap(
    movement: MovementScenario,
    access: AccessGapResult,
    case: str,
) -> float:
    base_attendance = max(float(movement.attendance_base), 1.0)
    attendance = float(getattr(movement, f"attendance_{case}"))
    demand = float(access.peak_demand_per_hour) * attendance / base_attendance
    capacity = float(getattr(access, f"transit_capacity_{case}"))
    return max(demand - capacity, 0.0)


def _bus_requirements(
    movement: MovementScenario,
    access: AccessGapResult,
    factors: InterventionFactorRegistry,
) -> tuple[int, int, int, float]:
    capacity_low = factors.shuttle_passengers_per_bus.low * factors.service_load_factor.low
    capacity_base = factors.shuttle_passengers_per_bus.base * factors.service_load_factor.base
    capacity_high = factors.shuttle_passengers_per_bus.high * factors.service_load_factor.high
    requirements = sorted(
        (
            ceil(_case_gap(movement, access, "low") / max(capacity_high, 1.0)),
            ceil(_case_gap(movement, access, "base") / max(capacity_base, 1.0)),
            ceil(_case_gap(movement, access, "high") / max(capacity_low, 1.0)),
        )
    )
    low, base, high = requirements
    return low, base, high, base * capacity_base


def _recommendation(
    recommendations: Sequence[InvestmentRecommendation],
    intervention: str,
) -> InvestmentRecommendation | None:
    return next((item for item in recommendations if item.intervention == intervention), None)


def _hub(
    regional_hubs: Sequence[Mapping[str, Any]],
    official_plan: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    published = official_plan.get("transfer_hubs")
    if isinstance(published, list) and published:
        transfer = next(
            (dict(item) for item in published if str(item.get("role")) == "primary transfer"),
            dict(published[0]),
        )
        return transfer, "published"
    candidates = [dict(item) for item in regional_hubs if isinstance(item, Mapping)]
    return (candidates[0], "candidate") if candidates else (None, "unavailable")


def _identity_check(
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
        raise ValueError("Traffic strategy inputs must describe the same city and match")


def build_traffic_strategy_plan(
    match: MatchEvent,
    movement: MovementScenario,
    access: AccessGapResult,
    city: CityInterventionInputs,
    factors: InterventionFactorRegistry,
    recommendations: Sequence[InvestmentRecommendation],
    *,
    regional_hubs: Sequence[Mapping[str, Any]] = (),
    official_plan: Mapping[str, Any] | None = None,
    strategy_features: StrategyFeatures | None = None,
    strategy_benchmark: Mapping[str, Any] | None = None,
) -> TrafficStrategyPlan:
    """Build one evidence-gated, time-phased traffic strategy.

    The strategy is operational decision support, not a traffic engineering
    plan.  Published facts can name facilities and controls; derived actions
    use candidate locations and disclose the missing local evidence.
    """

    _identity_check(match, movement, access, city)
    official = dict(official_plan or {})
    official_available = bool(official)
    selected_hub, hub_status = _hub(regional_hubs, official)
    hub_name = str(selected_hub.get("name")) if selected_hub else None
    demand = float(access.peak_demand_per_hour)
    scheduled = float(access.transit_capacity_base)
    coverage = min(scheduled / demand, 1.0) if demand > 0 else 0.0

    if strategy_features is not None:
        prediction = classify_strategy(strategy_features)
        predicted_pattern = prediction.family
        prediction_strength = prediction.strength
        prediction_reasons = prediction.reasons
        prediction_features = prediction.features.to_dict()
    else:
        if scheduled > 0 and coverage >= 0.60:
            predicted_pattern = "Direct-transit reinforcement"
            prediction_reasons = ("Scheduled event-hour service covers at least 60% of the modeled peak.",)
        elif scheduled > 0:
            predicted_pattern = "Direct transit plus overflow shuttle"
            prediction_reasons = ("A serving route exists but leaves a residual peak gap.",)
        elif selected_hub:
            predicted_pattern = "Regional hub to event shuttle"
            prediction_reasons = ("No direct scheduled capacity is established and a regional hub candidate exists.",)
        else:
            predicted_pattern = "Dedicated event shuttle staging"
            prediction_reasons = ("Neither direct scheduled capacity nor a regional hub is established.",)
        prediction_strength = "limited"
        prediction_features = {}

    benchmark = compare_with_benchmark(predicted_pattern, strategy_benchmark)
    if official_available and official.get("primary_pattern"):
        pattern = str(official["primary_pattern"])
        basis = "Published operating plan over an independently generated strategy-family screen"
        primary_measure = str(official.get("modeled_measure") or "Shuttle service")
    else:
        pattern = predicted_pattern
        basis = (
            "Calibrated from event-valid service, access, walking, and regional-hub features"
            if strategy_features is not None
            else (
                "Derived from event-valid venue service and modeled peak coverage"
                if scheduled > 0
                else "Derived from zero direct venue capacity and regional-hub evidence"
            )
        )
        primary_measure = (
            "Added transit frequency"
            if pattern
            in {
                "Direct high-capacity transit reinforcement",
                "Downtown multimodal dispersal",
                "Direct transit plus distributed egress",
                "Multimodal rail-transfer network",
                "Direct-transit reinforcement",
                "Direct transit plus overflow shuttle",
            }
            else "Shuttle service"
        )

    buses_low, buses_base, buses_high, proposed_capacity = _bus_requirements(movement, access, factors)
    feasibility = (
        "Single-hub screen"
        if buses_base <= SINGLE_HUB_BUS_LIMIT_PER_HOUR
        else "Multiple hubs or demand spreading required"
    )
    recommendation = _recommendation(recommendations, primary_measure)
    baseline_vehicle_trips = movement.attendance_base * city.private_vehicle_share / city.average_vehicle_occupancy
    modeled_vehicle_trips = _number(recommendation.venue_vehicle_trips_base) if recommendation else None
    trips_avoided = (
        max(baseline_vehicle_trips - modeled_vehicle_trips, 0.0) if modeled_vehicle_trips is not None else None
    )

    source_ids = tuple(str(value) for value in official.get("source_ids", []) if str(value))
    published_controls = tuple(str(value) for value in official.get("published_controls", []) if str(value).strip())
    arrival_window = str(official.get("arrival_window") or _window(movement.hourly_rows, "arrivals_base"))
    egress_window = str(official.get("egress_window") or _window(movement.hourly_rows, "departures_base"))
    hub_location = hub_name or "Transfer or staging hub to be validated"
    hub_location_status = hub_status if selected_hub else "unavailable"
    trunk_instruction = (
        str(official.get("trunk_instruction"))
        if official.get("trunk_instruction")
        else (
            f"Use {hub_location} as the candidate transfer point and screen {buses_base:,} buses per hour in the base case."
            if selected_hub
            else f"Validate a regional staging hub before procuring the screened {buses_base:,} buses per hour."
        )
    )
    curb_instruction = str(
        official.get("curb_instruction")
        or "Separate transit, rideshare/taxi, private shuttle, and accessible-vehicle loading before assigning a specific curb or lot."
    )
    egress_instruction = str(
        official.get("egress_instruction")
        or "Stage return service against the modeled departure peak and preserve a protected pedestrian route from the venue to loading areas."
    )
    overflow_trigger = str(
        official.get("overflow_trigger")
        or (
            f"Activate overflow when projected demand exceeds scheduled plus proposed capacity, or the estimated queue exceeds {QUEUE_TRIGGER_MINUTES} minutes of shuttle throughput."
        )
    )
    official_status = EvidenceStatus.OBSERVED if official_available else EvidenceStatus.PARTIAL
    actions = (
        TrafficStrategyAction(
            phase="Before match",
            title="Open the managed arrival window",
            instruction="Publish one multimodal arrival plan and direct ticket holders to assigned trunk, shuttle, parking, or curb channels.",
            time_window=arrival_window,
            trigger="Begin before the first modeled arrival hour; adjust only with observed ticketing or operations data.",
            location=None,
            location_status="not location-specific",
            evidence_status=EvidenceStatus.SCENARIO,
            dependencies=("Ticket-holder communications", "Agency and venue operating plan"),
        ),
        TrafficStrategyAction(
            phase="Arrival and transfer",
            title=pattern,
            instruction=trunk_instruction,
            time_window=arrival_window,
            trigger=f"Screened residual peak gap: {access.residual_passengers:,.0f} passengers per hour.",
            location=hub_name,
            location_status=hub_location_status,
            evidence_status=official_status if hub_status == "published" else EvidenceStatus.PARTIAL,
            source_ids=source_ids if hub_status == "published" else (),
            dependencies=("Fleet and operator availability", "Staging and layover capacity"),
        ),
        TrafficStrategyAction(
            phase="Curb and last mile",
            title="Separate loading and protect the final approach",
            instruction=curb_instruction,
            time_window=arrival_window,
            trigger="Open only after curb, pedestrian, emergency-access, and accessible-service checks are signed off.",
            location=str(official.get("curb_location")) if official.get("curb_location") else None,
            location_status="published" if official.get("curb_location") else "candidate",
            evidence_status=official_status if official.get("curb_location") else EvidenceStatus.PARTIAL,
            source_ids=source_ids if official.get("curb_location") else (),
            dependencies=("Curb inventory and enforcement plan", "Field-verified pedestrian and ADA path"),
        ),
        TrafficStrategyAction(
            phase="Egress",
            title="Stage the post-match release",
            instruction=egress_instruction,
            time_window=egress_window,
            trigger="Hold service until venue release, pedestrian crossing, and downstream platform conditions are safe.",
            location=hub_name,
            location_status=hub_location_status,
            evidence_status=official_status if official_available else EvidenceStatus.SCENARIO,
            source_ids=source_ids,
            dependencies=("Post-match crowd-control plan", "Return-service and platform management"),
        ),
        TrafficStrategyAction(
            phase="Contingency",
            title="Activate overflow capacity",
            instruction=overflow_trigger,
            time_window=f"{arrival_window}; {egress_window}",
            trigger=overflow_trigger,
            location=hub_name,
            location_status=hub_location_status,
            evidence_status=official_status if official.get("overflow_trigger") else EvidenceStatus.SCENARIO,
            source_ids=source_ids if official.get("overflow_trigger") else (),
            dependencies=("Queue monitoring", "Dispatch authority", "Reserved overflow fleet"),
        ),
    )

    evidence_gaps = [
        "Observed match-hour arrivals, mode share, and queue response are unavailable.",
        "Curb throughput, enforcement capacity, staffing, and emergency-access constraints require local validation.",
        "The strategy does not estimate roadway speed, delay, signal timing, or intersection level of service.",
    ]
    if not selected_hub:
        evidence_gaps.append("No published or event-valid regional transfer hub is established.")
    if not official_available:
        evidence_gaps.append(
            "No published city operating-plan overlay is integrated; all named locations remain candidates."
        )
    if access.walking_status == EvidenceStatus.UNAVAILABLE:
        evidence_gaps.append("The final pedestrian connection is not modeled.")

    summary = (
        f"{pattern}: use {hub_name} as the published transfer hub and preserve the official operating controls."
        if hub_status == "published"
        else (
            f"{pattern}: use {hub_name} as a candidate transfer anchor; the one-hub equivalent is "
            f"{buses_base:,} buses per hour, so validate a distributed operating plan."
            if hub_name
            else f"{pattern}: establish distributed staging; the one-hub equivalent is "
            f"{buses_base:,} buses per hour and is not a fleet recommendation."
        )
    )
    return TrafficStrategyPlan(
        schema_version="1.0.0",
        city=match.city,
        match_id=match.match_id,
        primary_pattern=pattern,
        predicted_pattern=predicted_pattern,
        prediction_strength=prediction_strength,
        prediction_reasons=tuple(prediction_reasons),
        prediction_features=prediction_features,
        benchmark_pattern=benchmark["benchmark_pattern"],
        benchmark_agreement=str(benchmark["benchmark_agreement"]),
        benchmark_source_url=benchmark["benchmark_source_url"],
        benchmark_evidence_level=benchmark["benchmark_evidence_level"],
        strategy_basis=basis,
        status=EvidenceStatus.PARTIAL if official_available else EvidenceStatus.SCENARIO,
        summary=summary,
        arrival_window=arrival_window,
        egress_window=egress_window,
        regional_hub_name=hub_name,
        regional_hub_status=hub_status,
        regional_hub_lat=(_number(selected_hub.get("lat")) if selected_hub else None),
        regional_hub_lon=(_number(selected_hub.get("lon")) if selected_hub else None),
        required_buses_per_hour_low=buses_low,
        required_buses_per_hour_base=buses_base,
        required_buses_per_hour_high=buses_high,
        proposed_capacity_per_hour_base=round(proposed_capacity, 3),
        single_hub_feasibility=feasibility,
        peak_passengers_addressed=(round(float(recommendation.gap_resolved_passengers), 3) if recommendation else None),
        venue_vehicle_trips_avoided=round(trips_avoided, 3) if trips_avoided is not None else None,
        net_vmt_avoided=(
            round(float(recommendation.net_vmt_base), 3)
            if recommendation and recommendation.net_vmt_base is not None
            else None
        ),
        net_co2e_kg_avoided=(round(float(recommendation.net_co2e_kg), 3) if recommendation else None),
        official_plan_available=official_available,
        published_controls=published_controls,
        actions=actions,
        evidence_gaps=tuple(evidence_gaps),
        assumptions=(
            "Bus requirements are unconstrained screening needs, not fleet commitments.",
            f"A single hub is screened at no more than {SINGLE_HUB_BUS_LIMIT_PER_HOUR} buses per hour before multi-hub operations are required.",
            "Vehicle-trip, VMT, and CO2e outcomes reuse the existing single-measure intervention model.",
            "Exact controls appear only when supplied by an official operating-plan overlay.",
        ),
        equation_ids=(
            "EQ-DEMAND-01",
            "EQ-CAPACITY-01",
            "EQ-GAP-01",
            "EQ-TRAFFIC-SCALE-01",
            "EQ-VMT-01",
            "EQ-CO2-01",
        ),
    )


__all__ = [
    "PHASES",
    "SINGLE_HUB_BUS_LIMIT_PER_HOUR",
    "TrafficStrategyAction",
    "TrafficStrategyPlan",
    "build_traffic_strategy_plan",
]
