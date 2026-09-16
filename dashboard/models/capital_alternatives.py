"""Early-stage capital concepts, not approved projects or ridership forecasts."""

from dataclasses import dataclass
from math import floor, isfinite

from dashboard.models.service_design import event_window_cycles


@dataclass(frozen=True)
class CapitalAlternative:
    title: str
    rationale: str
    buses: int
    cycle_hours: float
    corridor_miles: float = 0


ALTERNATIVES = {
    "Boston": CapitalAlternative(
        "Electric regional express-bus fleet",
        "Replace conventional stadium express buses with a fleet that also serves regional events. "
        "Long-distance range and depot charging need validation.", 40, 3,
    ),
    "Dallas": CapitalAlternative(
        "Electric BRT connection to the stadium district",
        "Study a dedicated bus corridor connecting regional transit with the stadium district. "
        "Proceed only if year-round demand and a feasible right-of-way justify it.", 60, 1.5, 10,
    ),
    "Kansas City": CapitalAlternative(
        "Electric event-bus fleet and charging depot",
        "Electrify existing Stadium Direct trips for recurring events. This reduces fleet emissions; "
        "it does not replace the immediate need to fix entrance operations.", 40, 1,
    ),
    "Los Angeles": CapitalAlternative(
        "Electric stadium-connector fleet",
        "Replace conventional connector buses and reuse the fleet across major events. "
        "Coordinate procurement with Metro's existing fleet plans to avoid duplicate investment.", 60, 1,
    ),
    "Miami": CapitalAlternative(
        "Electric BRT links from existing transit hubs",
        "Study dedicated bus priority linking existing hubs to the stadium district. "
        "A permanent corridor needs everyday ridership and right-of-way evidence.", 60, 1, 10,
    ),
}

BUS_COST_SOURCE = "https://www.auditor.ca.gov/reports/2025-120/"
BRT_COST_SOURCE = (
    "https://cityofraleigh0drupal.blob.core.usgovcloudapi.net/drupal-prod/COR28/"
    "northern-bus-rapid-transit-major-investment-study-spring26.pdf"
)
SPARE_FLEET_SOURCE = "https://www.transit.dot.gov/sites/fta.dot.gov/files/2021-01/FTA-Report-No-0182.pdf"
SPARE_RATIO = 0.20
SLOW_CYCLE_MULTIPLIER = 1.25


def estimate_capital_alternative(city: str, attendance: float, arrival_hours: float) -> dict | None:
    concept = ALTERNATIVES.get(city)
    if concept is None:
        return None
    if not all(isfinite(x) for x in (attendance, arrival_hours)) or attendance < 0 or arrival_hours <= 0:
        raise ValueError("Attendance must be nonnegative and the arrival window must be positive")
    # Purchased fleet includes reserves. FTA spare ratios use peak service as
    # the denominator; this is a planning allowance, not an availability forecast.
    active_buses = floor(concept.buses / (1 + SPARE_RATIO))
    cycles = event_window_cycles(arrival_hours, concept.cycle_hours)
    slow_cycles = event_window_cycles(arrival_hours, concept.cycle_hours * SLOW_CYCLE_MULTIPLIER)
    fleet_low = concept.buses * 1_300_000
    fleet_high = concept.buses * 1_700_000
    infrastructure_low = fleet_low * 0.20
    infrastructure_high = fleet_high * 0.40
    contingency_low = (fleet_low + infrastructure_low) * 0.15
    contingency_high = (fleet_high + infrastructure_high) * 0.30
    # Corridor ROM rates already carry broad design uncertainty. Do not add
    # the fleet contingency again to the corridor allowance.
    corridor_low = concept.corridor_miles * 10_000_000
    corridor_high = concept.corridor_miles * 25_000_000
    return {
        "concept": concept,
        "capital_low": fleet_low + infrastructure_low + contingency_low + corridor_low,
        "capital_high": fleet_high + infrastructure_high + contingency_high + corridor_high,
        "fleet_low": fleet_low, "fleet_high": fleet_high,
        "infrastructure_low": infrastructure_low, "infrastructure_high": infrastructure_high,
        "contingency_low": contingency_low, "contingency_high": contingency_high,
        "corridor_low": corridor_low, "corridor_high": corridor_high,
        "passengers_low": min(attendance, floor(active_buses * slow_cycles * 45 * 0.65)),
        "passengers_high": min(attendance, floor(active_buses * cycles * 45 * 0.85)),
        "active_buses": active_buses,
        "reserve_buses": concept.buses - active_buses,
        "cycles_per_bus": cycles,
        "slow_cycles_per_bus": slow_cycles,
    }
