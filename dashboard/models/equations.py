"""Auditable equation registry for transportation decision outputs.

The registry is intentionally independent from Streamlit. Model code cites stable
equation IDs, while the Methods view and scenario downloads render the same
definitions for reviewers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class EquationDefinition:
    equation_id: str
    outcome: str
    equation: str
    variables: str
    interpretation: str
    evidence_limit: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


EQUATIONS = (
    EquationDefinition(
        "EQ-DEMAND-01",
        "Hourly movement",
        "arrivals_h = attendance × normalized_arrival_share_h",
        "attendance is the selected low/base/high scenario; hourly shares sum to 1",
        "Allocates the attendance scenario across local event hours.",
        "Attendance and event response are scenarios, not observed ticket scans.",
    ),
    EquationDefinition(
        "EQ-VISITOR-FLOW-01",
        "World Cup attendee origin forecast",
        "origin_attendees_case = attendance_case × stage_origin_share_case",
        "domestic origin shares use the supplied commercial-origin context; international share is an explicit tournament-stage scenario",
        "Allocates every hosted match attendance case to host-market, nearby U.S., long-distance U.S., and international/unobserved origin types.",
        "Commercial origins are not FIFA fan observations, and international share is unobserved; this is a scenario forecast.",
    ),
    EquationDefinition(
        "EQ-CAPACITY-01",
        "Scheduled transit capacity",
        "capacity_h = departures_h × vehicle_capacity × usable_load_factor",
        "departures come from event-valid GTFS; vehicle capacity and load factor are ranges",
        "Estimates potential scheduled passenger throughput near the venue.",
        "This is not observed ridership, delivered service, crowding, or reliability.",
    ),
    EquationDefinition(
        "EQ-MODE-SPLIT-01",
        "Broad venue-access mode demand",
        "mode_attendees = origin_attendees × conditional_mode_share(readiness, scheduled_coverage, walking_path)",
        "conditional shares cover scheduled transit, shuttle/coach, private vehicle/taxi, and walk/bike demand and sum to one within each origin type",
        "Estimates broad venue-access mode demand under the current evidence and scenario inputs.",
        "This is not calibrated mode choice, delivered service, exact route assignment, travel time, or observed roadway flow.",
    ),
    EquationDefinition(
        "EQ-GAP-01",
        "Residual access gap",
        "gap_h = max(demand_h − scheduled_capacity_h, 0)",
        "demand and capacity use the same hourly planning case",
        "Reports passengers per hour not covered by modeled scheduled capacity.",
        "It is not roadway congestion or a queue measurement.",
    ),
    EquationDefinition(
        "EQ-RESILIENCE-01",
        "Common access stress",
        "stress_coverage = capacity_h × (1 − 0.20) ÷ (demand_h × (1 + 0.10))",
        "the portfolio applies the same 10% demand surge and 20% scheduled-capacity loss to every representative match",
        "Reports retained scheduled coverage and the remaining stressed gap in passengers per hour.",
        "This is a sensitivity test, not a disruption probability, reliability forecast, or recovery model.",
    ),
    EquationDefinition(
        "EQ-SPREAD-01",
        "Effective arrival spreading",
        "shift_pph = min(peak × requested_share × eligible_share × compliance, peak × shoulder_capacity_share)",
        "requested_share is the control; eligible share, compliance, and shoulder capacity are low/base/high assumptions",
        "Moves only the feasible participating share from the peak to shoulder periods.",
        "No city has observed FIFA response or curb-throughput evidence; this remains exploratory.",
    ),
    EquationDefinition(
        "EQ-INTERVENTION-01",
        "Peak gap resolved",
        "resolved = min(residual_gap, physical_capacity_added + feasible_arrival_shift)",
        "physical capacity includes shuttle, transit, feeder-constrained park-and-ride, bike, and eligible walking uptake",
        "Caps modeled benefit at the residual passenger gap.",
        "Potential throughput is not observed mode shift.",
    ),
    EquationDefinition(
        "EQ-PARK-RIDE-01",
        "Park-and-ride throughput",
        "park_pph = min(space_passengers / arrival_hours, feeder_departures_h × passengers_per_bus × usable_load_factor)",
        "space passengers depend on lot spaces, vehicle occupancy, and utilization; feeder operations are separately specified and costed",
        "Prevents parking inventory from becoming passenger throughput without a feeder fleet.",
        "Remote-lot inventory, fleet availability, and travel time remain planning inputs requiring local verification.",
    ),
    EquationDefinition(
        "EQ-VMT-01",
        "Net vehicle-miles avoided",
        "net_VMT = avoided_private_VMT − added_service_VMT",
        "park-and-ride avoids only the venue-area leg; shuttle, transit, and feeder VMT are added",
        "Retains upstream driving and operating mileage.",
        "Trip distance, occupancy, mode share, and uptake are planning assumptions.",
    ),
    EquationDefinition(
        "EQ-CO2-01",
        "Net CO2e avoided",
        "net_CO2e = avoided_private_VMT × private_factor − added_service_VMT × service_factor",
        "factors are pinned low/base/high planning ranges",
        "Allows negative results when added service emits more than displaced driving.",
        "This is not a local MOVES inventory or causal emissions estimate.",
    ),
    EquationDefinition(
        "EQ-COST-01",
        "Total planning cost",
        "total_cost = one_time_capital + per_event_operations",
        "capital covers installed assets; operations recur for each modeled event",
        "Preserves the actual order-of-magnitude project cost range.",
        "National factors are not bids, budgets, or local engineering estimates.",
    ),
    EquationDefinition(
        "EQ-COST-02",
        "Comparison cost per passenger",
        "comparison_CPP = (event_operations + capital ÷ reusable_event_uses) ÷ peak_gap_resolved",
        "reusable event uses are explicit low/base/high scenario factors by capital measure",
        "Compares operating and capital options on a common event-use basis without hiding total cost.",
        "Reuse is a scenario assumption; users should change it for their planning horizon.",
    ),
    EquationDefinition(
        "EQ-PARETO-01",
        "Nondominated option set",
        "A dominates B only if A is no worse on resolved gap, net CO2e, comparison CPP, lead time, and heat benefit, and better on at least one",
        "screening eligibility is shown separately and eligible options sort before exploratory sensitivities",
        "Retains tradeoffs instead of manufacturing one composite optimum.",
        "A frontier position is not an agency recommendation or implementation approval.",
    ),
)


def equation_records() -> list[dict[str, str]]:
    return [definition.to_dict() for definition in EQUATIONS]


def equation_ids() -> tuple[str, ...]:
    return tuple(definition.equation_id for definition in EQUATIONS)
