"""Configurable policy metadata for intervention screening and presentation."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from dashboard.mobility_platform.contracts import AccessGapResult, EvidenceStatus


@dataclass(frozen=True)
class MeasurePolicy:
    name: str
    lead_time_band: str
    responsible_actor: str
    dependencies: tuple[str, ...]
    comparison_cost_basis: str
    reuse_factor: str | None
    evidence_rule: str

    def to_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["dependencies"] = list(self.dependencies)
        return row


@dataclass(frozen=True)
class EvidenceAssessment:
    screening_eligible: bool
    quality: str
    reason: str


MEASURE_POLICIES = {
    "Shuttle service": MeasurePolicy(
        "Shuttle service",
        "0-6 months",
        "Venue operator and transit agency",
        ("Staging and layover space", "Event-day operator agreement"),
        "Per-event operating cost",
        None,
        "Requires a capacity-qualified access gap; fleet and operator availability remain local confirmations.",
    ),
    "Added transit frequency": MeasurePolicy(
        "Added transit frequency",
        "3-12 months",
        "Transit agency",
        ("Fleet and operator availability", "Event-window timetable"),
        "Per-event operating cost",
        None,
        "Requires a capacity-qualified access gap; added fleet capacity remains a scenario range.",
    ),
    "Park-and-ride feeder service": MeasurePolicy(
        "Park-and-ride feeder service",
        "6-24 months",
        "City, parking partner, and transit agency",
        ("Remote lot agreement", "Feeder fleet", "Traffic management plan"),
        "Capital divided by reusable event uses plus event operations",
        "park_ride_reuse_events",
        "Requires a verified remote lot and feeder operating plan; neither is currently supplied.",
    ),
    "Bike and micromobility hubs": MeasurePolicy(
        "Bike and micromobility hubs",
        "6-18 months",
        "City transportation department",
        ("Safe network connection", "Micromobility operating plan"),
        "Capital divided by reusable event uses",
        "bike_hub_reuse_events",
        "Requires a field-verified safe connection and operating plan; OSM tags are not a safety audit.",
    ),
    "Cooled walking corridors": MeasurePolicy(
        "Cooled walking corridors",
        "12-36 months",
        "City public works department",
        ("Right-of-way design", "Shade and cooling maintenance plan"),
        "Capital divided by reusable event uses",
        "cooled_walkway_reuse_events",
        "Requires a modeled network route and route-heat evidence; design and right-of-way remain unverified.",
    ),
    "Arrival spreading and curb management": MeasurePolicy(
        "Arrival spreading and curb management",
        "0-6 months",
        "City and venue operator",
        ("Ticket-holder communications", "Curb allocation and enforcement plan"),
        "Per-event operating cost",
        None,
        "Requires observed response, curb throughput, and shoulder capacity; none are currently supplied.",
    ),
}


LEAD_TIME_RANKS = {
    "0-6 months": 1,
    "3-12 months": 2,
    "6-18 months": 3,
    "6-24 months": 4,
    "12-36 months": 5,
    "Requires scoping": 6,
}


def measure_policy(name: str) -> MeasurePolicy:
    return MEASURE_POLICIES.get(
        name,
        MeasurePolicy(
            name,
            "Requires scoping",
            "Multi-agency delivery team",
            ("Implementation plan",),
            "Unspecified planning cost",
            None,
            "No evidence rule is registered; the option is exploratory.",
        ),
    )


def assess_evidence(name: str, access: AccessGapResult) -> EvidenceAssessment:
    if name in {"Shuttle service", "Added transit frequency"}:
        eligible = bool(access.capacity_qualified)
        return EvidenceAssessment(
            eligible,
            "medium" if eligible else "low",
            "Capacity-qualified scheduled-service gap is available; capacity, uptake, fleet, and operations remain scenarios."
            if eligible
            else "Event transit capacity is not qualified.",
        )
    if name == "Cooled walking corridors":
        eligible = (
            access.walking_status != EvidenceStatus.UNAVAILABLE
            and access.heat_status != EvidenceStatus.UNAVAILABLE
            and access.route_heat_exposure_c is not None
        )
        return EvidenceAssessment(
            eligible,
            "medium" if eligible else "low",
            "Network route and route-heat evidence are available; treatment performance remains a scenario."
            if eligible
            else "A network route and route-heat evidence are required.",
        )
    if name == "Arrival spreading and curb management":
        return EvidenceAssessment(
            False,
            "low",
            "No observed arrival-response, curb-throughput, or shoulder-capacity evidence is supplied; retain as an exploratory sensitivity.",
        )
    if name == "Park-and-ride feeder service":
        return EvidenceAssessment(
            False,
            "low",
            "No verified remote-lot inventory or feeder operating plan is supplied.",
        )
    if name == "Bike and micromobility hubs":
        return EvidenceAssessment(
            False,
            "low",
            "No field-verified safe bicycle connection or event operating plan is supplied.",
        )
    return EvidenceAssessment(False, "low", "No registered evidence gate is available.")


def lead_time_rank(name: str) -> int:
    return LEAD_TIME_RANKS.get(measure_policy(name).lead_time_band, 6)


def policy_records() -> list[dict[str, object]]:
    return [MEASURE_POLICIES[name].to_dict() for name in sorted(MEASURE_POLICIES)]
