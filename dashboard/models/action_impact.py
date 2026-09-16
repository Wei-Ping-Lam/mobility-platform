"""Illustrative, action-specific scenarios for the curated transit recommendations.

Scope, uptake, staffing allowances, and construction budgets below are analyst
assumptions, not observed performance, local quotes, or calibrated forecasts.
Vehicle factors are supplied by the existing pinned intervention registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite

from dashboard.models.electric_bus import electric_bus_kg_per_mile, operating_co2e_range
from dashboard.models.interventions import InterventionFactorRegistry
from dashboard.models.service_design import ELECTRIC_SERVICE_COST_MULTIPLIER, event_window_cycles

DEPOT_MILEAGE_ALLOWANCE = 0.10
SETUP_HOURS_PER_BUS = 1.0


@dataclass(frozen=True)
class ActionScope:
    description: str
    beneficiary_share: float = 0.0
    private_shift_share: float = 0.0
    buses: int = 0
    cycle_hours: float = 1.0
    round_trip_miles: float = 0.0
    operating_allowance: float = 0.0
    capital_allowance: float = 0.0
    local_leg_only: bool = False
    car_round_trip_miles: float | None = None
    replaces_existing_service: bool = False
    incentive_per_shifted_rider: float = 0.0
    incentive_per_service_rider: float = 0.0


ACTION_SCOPES = {
    "Atlanta": ActionScope(
        "Parking management and station wayfinding; assume 6% of attendees switch from car to existing rail. "
        "Assumes spare rail capacity; rail expansion and parking-revenue changes are excluded.",
        beneficiary_share=0.06, private_shift_share=1.0, operating_allowance=6000,
    ),
    "Boston": ActionScope(
        "Improve a booked subset of existing express-bus service: replace up to 12 conventional buses "
        "with electric vehicles on equivalent trips and offer a $20 round-trip fare credit per rider. "
        "Assume a 3-hour cycle and 90-mile return route as planning proxies, not a measured route. "
        "Verify existing conventional trips, bookings, vehicle range and charging before procurement. "
        "Credit only fleet-replacement CO2e savings; no additional riders, car-trip reductions or "
        "new routes are assumed. Rail fare support is not included in this quantified bus package. "
        "Costs cover gross replacement service, administration and fare credits, not incremental cost.",
        buses=12, cycle_hours=3.0, round_trip_miles=90,
        operating_allowance=2000, replaces_existing_service=True, incentive_per_service_rider=20,
    ),
    "Dallas": ActionScope(
        "Pre-position up to 8 electric overflow buses instead of conventional overflow dispatch, with a "
        "1.5-hour cycle and 40-mile round trip. Same passenger demand and mileage as the assumed "
        "conventional overflow baseline; only fleet emissions improve. No mode shift credited.",
        buses=8, cycle_hours=1.5, round_trip_miles=40, operating_allowance=2000,
        replaces_existing_service=True,
    ),
    "Houston": ActionScope(
        "Up to four electric last-mile buses, a 24-minute cycle and matched 4-mile return corridor. "
        "Target 40% of riders replacing local car/rideshare trips; the remainder receive walking relief. "
        "Reservation-based dispatch must verify the car-trip replacement target.",
        buses=4, cycle_hours=0.4, round_trip_miles=4, operating_allowance=1000,
        private_shift_share=0.40, car_round_trip_miles=4,
    ),
    "Kansas City": ActionScope(
        "Open additional entrances and replace four conventional Stadium Direct buses with leased electric "
        "buses on equivalent booked trips. Assume a 1-hour cycle and 16-mile return route. "
        "Gate improvements benefit 15% of attendees; bus riders overlap that group, so counts are not added. "
        "CO2e savings come only from fleet replacement, not inferred queue or idling improvements.",
        beneficiary_share=0.15, operating_allowance=6000, buses=4,
        cycle_hours=1, round_trip_miles=16, replaces_existing_service=True,
    ),
    "Los Angeles": ActionScope(
        "Enforce connector lanes and signal priority, paired with six leased electric buses replacing "
        "equivalent conventional connector trips. Assume a 1-hour cycle and 12-mile return route. "
        "Priority benefits 12% of attendees, including replacement-bus riders. CO2e savings come from "
        "fleet replacement; no unmeasured speed or mode-shift benefit is credited.",
        beneficiary_share=0.12, operating_allowance=8000, capital_allowance=100000,
        buses=6, cycle_hours=1, round_trip_miles=12, replaces_existing_service=True,
    ),
    "Miami": ActionScope(
        "Up to twelve electric buses across existing hubs, a 1-hour cycle and matched 16-mile return "
        "corridor. Target 40% car-trip replacement, verified by reservations. Both event windows operate.",
        buses=12, cycle_hours=1.0, round_trip_miles=16, private_shift_share=0.40,
        operating_allowance=3000, car_round_trip_miles=16,
    ),
    "New York/NJ": ActionScope(
        "Sanctioned-path improvements; assume 4% of attendees benefit and 5% of those replace a "
        "local vehicle leg with walking. Construction is a placeholder budget, not a designed project.",
        beneficiary_share=0.04, private_shift_share=0.05, local_leg_only=True,
        operating_allowance=2000, capital_allowance=750000,
    ),
    "Philadelphia": ActionScope(
        "Combine platform marshals and signage with a targeted $10 rail-travel credit for attendees "
        "who would otherwise drive. Assume 25% of attendees benefit from crowd management and 2% of "
        "that group replaces a car trip (0.5% of attendance). Confirm spare capacity on existing trains; "
        "additional rail service is not included. No queue-related fuel savings credited.",
        beneficiary_share=0.25, operating_allowance=6000, capital_allowance=15000,
        private_shift_share=0.02, incentive_per_shifted_rider=10,
    ),
    "San Francisco": ActionScope(
        "Temporary wayfinding and crossing guidance on approved detours, not a new permanent bypass. "
        "Retain an illustrative uptake case of 3% of attendees assisted and 10% of that group replacing "
        "a local vehicle leg; neither affected-user counts nor mode shift have been measured. "
        "CO2e savings are conditional on that assumed mode shift, not established by the closure notice. "
        "Assume a $1,000 per-match operating allowance; no construction cost or shorter route is modeled. "
        "Audit routes and obtain staffing quotes before funding; resident benefits are not quantified.",
        beneficiary_share=0.03, private_shift_share=0.10, local_leg_only=True,
        operating_allowance=1000,
    ),
    "Seattle": ActionScope(
        "Offer a targeted $10 rail-travel credit and station guidance to attendees who would otherwise "
        "drive. Target 2% of attendance shifting to existing transit, capped at the private-mode rider pool. "
        "Confirm spare service capacity and measure uptake; no new vehicle service or infrastructure assumed.",
        beneficiary_share=0.02, private_shift_share=1, operating_allowance=2000,
        incentive_per_shifted_rider=10,
    ),
}


def estimate_action_impact(
    city: str,
    attendance: float,
    private_vehicle_share: float,
    vehicle_occupancy: float,
    private_trip_miles: float,
    local_leg_miles: float,
    arrival_hours: float,
    factors: InterventionFactorRegistry,
) -> list[dict[str, float | str]]:
    """Compare three scope cases at the selected match's base attendance.

    Passengers are per-match beneficiaries, not hourly capacity or unique
    tournament visitors. Shuttle riders count once across ingress and egress;
    bus mileage and hours cover both windows, including empty return legs.
    """
    scope = ACTION_SCOPES[city]
    values = (attendance, private_vehicle_share, vehicle_occupancy,
              private_trip_miles, local_leg_miles, arrival_hours)
    if not all(isfinite(value) for value in values):
        raise ValueError("Action impact inputs must be finite")
    if attendance < 0 or not 0 <= private_vehicle_share <= 1:
        raise ValueError("Invalid attendance or private-vehicle share")
    if min(vehicle_occupancy, private_trip_miles, local_leg_miles, arrival_hours) <= 0:
        raise ValueError("Occupancy, distances, and duration must be positive")
    if local_leg_miles > private_trip_miles:
        raise ValueError("Local leg cannot exceed the full trip")

    rows = []
    for case, scope_scale, cost_scale in (("low", 0.6, 0.6), ("base", 1.0, 1.0), ("high", 1.4, 1.6)):
        buses = round(scope.buses * scope_scale)
        capacity = factors.shuttle_passengers_per_bus.value(case) * factors.service_load_factor.value(case)
        cycles_per_bus = event_window_cycles(arrival_hours, scope.cycle_hours)
        planned_cycles = buses * cycles_per_bus
        operations_passengers = min(attendance, attendance * scope.beneficiary_share * scope_scale)
        if scope.buses:
            service_passengers = min(attendance, planned_cycles * capacity)
            # Whole deliveries per bus; attendance is a cap, not evidence of bookings.
            cycles = min(planned_cycles, ceil(service_passengers / capacity)) if capacity > 0 else 0
        else:
            service_passengers = 0
            cycles = 0
        # Use the larger beneficiary group, assuming overlap rather than counting both.
        passengers = max(operations_passengers, service_passengers)
        service_hours = cycles * scope.cycle_hours * 2
        active_buses = ceil(cycles / cycles_per_bus) if cycles_per_bus else 0
        longest_bus_duty = 2 * ceil(cycles / active_buses) * scope.cycle_hours if active_buses else 0
        paid_hours = active_buses * (max(arrival_hours * 2, longest_bus_duty) + SETUP_HOURS_PER_BUS)
        route_miles = cycles * scope.round_trip_miles * 2
        service_miles = route_miles * (1 + DEPOT_MILEAGE_ALLOWANCE)
        shift_eligible = service_passengers if scope.buses else passengers
        shifted = min(shift_eligible * scope.private_shift_share, attendance * private_vehicle_share)
        if scope.private_shift_share == 1:
            passengers = shifted
        distance = local_leg_miles if scope.local_leg_only else private_trip_miles
        if scope.car_round_trip_miles is not None:
            distance = scope.car_round_trip_miles
        avoided_car_miles = shifted / vehicle_occupancy * distance
        baseline_service_miles = service_miles if scope.replaces_existing_service else 0
        net_miles = avoided_car_miles - (service_miles - baseline_service_miles)
        conventional_factor = factors.service_vehicle_co2e_kg_per_mile.value(case)
        electric_factor = electric_bus_kg_per_mile(city) if service_miles else 0
        added_service_co2 = service_miles * electric_factor
        baseline_service_co2 = baseline_service_miles * conventional_factor
        net_co2 = (
            avoided_car_miles * factors.private_vehicle_co2e_kg_per_mile.value(case)
            + baseline_service_co2 - added_service_co2
        )
        car_savings_per_shifted = distance / vehicle_occupancy * factors.private_vehicle_co2e_kg_per_mile.value(case)
        required_shifted = max(added_service_co2 - baseline_service_co2, 0) / car_savings_per_shifted if car_savings_per_shifted else 0
        co2_low, co2_high = operating_co2e_range(
            city, avoided_car_miles, service_miles, baseline_service_miles,
            factors.private_vehicle_co2e_kg_per_mile, factors.service_vehicle_co2e_kg_per_mile,
        )
        incentive_cost = (
            shifted * scope.incentive_per_shifted_rider
            + service_passengers * scope.incentive_per_service_rider
        )
        operating = (
            paid_hours * factors.shuttle_cost_per_bus_hour.value(case) * ELECTRIC_SERVICE_COST_MULTIPLIER
            + scope.operating_allowance * cost_scale
            + incentive_cost
        )
        capital = scope.capital_allowance * cost_scale
        rows.append({
            "case": case,
            "passengers": passengers,
            "shifted_passengers": shifted,
            "service_passengers": service_passengers,
            "operations_passengers": operations_passengers,
            "net_vehicle_miles": net_miles,
            "net_co2e_kg": net_co2,
            "net_co2e_kg_low": co2_low,
            "net_co2e_kg_high": co2_high,
            "operating_cost": operating,
            "capital_cost": capital,
            "first_event_cost": operating + capital,
            "buses": buses,
            "service_hours": service_hours,
            "paid_service_hours": paid_hours,
            "active_buses": active_buses,
            "arrival_cycles": cycles,
            "cycles_per_bus": cycles_per_bus,
            "route_miles": route_miles,
            "electric_kg_per_mile": electric_factor,
            "service_miles": service_miles,
            "baseline_service_miles": baseline_service_miles,
            "avoided_car_co2e_kg": avoided_car_miles * factors.private_vehicle_co2e_kg_per_mile.value(case),
            "baseline_service_co2e_kg": baseline_service_co2,
            "proposed_service_co2e_kg": added_service_co2,
            "incentive_cost": incentive_cost,
            "car_round_trip_miles": distance,
            "minimum_car_shift_share": required_shifted / passengers if passengers else 0,
            "co2e_screen": "Pass" if net_co2 > 0 else "No reduction" if net_co2 == 0 else "Needs redesign",
            "avoided_car_miles": avoided_car_miles,
            "scope_scale": scope_scale,
            "cost_scale": cost_scale,
        })
    return rows
