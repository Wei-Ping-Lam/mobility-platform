"""Four illustrative solution types evaluated against explicit counterfactuals."""

from __future__ import annotations

from math import ceil, floor, isfinite

from dashboard.models.interventions import CityInterventionInputs, InterventionFactorRegistry
from dashboard.models.service_design import ELECTRIC_SERVICE_EMISSIONS_RATIO


def compare_transit_solutions(
    attendance: float,
    inputs: CityInterventionInputs,
    factors: InterventionFactorRegistry,
) -> list[dict[str, str | float]]:
    """Return per-match beneficiaries and incremental operational emissions.

    These are independent planning examples, not equal-budget alternatives or
    locally assigned services. The shared 12-bus baseline is hypothetical.
    Passengers count once; service miles include ingress, egress, and empty legs.
    """
    numeric = (
        attendance, inputs.private_vehicle_share, inputs.average_vehicle_occupancy,
        inputs.average_private_trip_miles, inputs.venue_area_leg_miles,
        inputs.shuttle_round_trip_miles, inputs.park_ride_feeder_round_trip_miles,
        inputs.transit_round_trip_miles, inputs.arrival_window_hours,
    )
    if not all(isfinite(value) for value in numeric) or attendance < 0:
        raise ValueError("Solution comparison requires finite inputs and nonnegative attendance")
    hours = inputs.arrival_window_hours
    car_riders = attendance * inputs.private_vehicle_share
    car_factor = factors.private_vehicle_co2e_kg_per_mile.base
    service_factor = factors.service_vehicle_co2e_kg_per_mile.base
    electric_factor = service_factor * ELECTRIC_SERVICE_EMISSIONS_RATIO
    seats = factors.shuttle_passengers_per_bus.base * factors.service_load_factor.base
    cycle = inputs.shuttle_round_trip_miles / 20.0 + 0.25
    baseline_cycles = floor(12 * hours / cycle)
    baseline_riders = min(attendance, baseline_cycles * seats)
    baseline_cycles = min(baseline_cycles, ceil(baseline_riders / seats)) if seats > 0 else 0
    baseline_miles = baseline_cycles * 2 * inputs.shuttle_round_trip_miles
    rows = []

    def add(name, label, passengers, shifted, car_distance, service_miles, emissions, basis):
        car_miles = shifted / inputs.average_vehicle_occupancy * car_distance
        net_co2 = car_miles * car_factor - emissions
        savings_per_car_rider = car_distance / inputs.average_vehicle_occupancy * car_factor
        required_riders = max(emissions, 0) / savings_per_car_rider if savings_per_car_rider > 0 else 0
        rows.append({
            "solution": name, "label": label, "passengers": passengers,
            "shifted_passengers": shifted, "net_co2e_kg": net_co2,
            "net_vehicle_miles": car_miles - service_miles,
            "added_service_miles": service_miles, "basis": basis,
            "minimum_car_shift_share": required_riders / passengers if passengers else 0,
            "co2e_screen": "Pass" if net_co2 >= 0 else "Needs redesign",
        })

    # Faster cycles benefit existing riders; only extra riders can replace cars.
    extra_capacity = max(floor(12 * hours / (cycle * 0.75)) - baseline_cycles, 0) * seats
    extra_riders = min(extra_capacity, max(attendance - baseline_riders, 0), car_riders / 0.5)
    lane_riders = baseline_riders + extra_riders
    extra_cycles = ceil(extra_riders / seats) if seats > 0 else 0
    extra_miles = extra_cycles * 2 * inputs.shuttle_round_trip_miles
    add(
        "Dedicated event bus/shuttle lanes", "Event bus lanes", lane_riders,
        min(extra_riders * 0.5, car_riders), inputs.average_private_trip_miles,
        extra_miles, extra_miles * electric_factor,
        "Dedicated lanes shorten the assumed cycle by 25%. Existing riders benefit without extra mileage; "
        "additional departures use electric vehicles and reserved demand, targeting 50% car-trip replacement. "
        "No idling or speed-related emissions savings assumed. Deploy extra service only if its CO2e screen passes.",
    )

    # The replaced car leg and the feeder follow the same assumed hub-venue corridor.
    feeder_distance = inputs.venue_area_leg_miles
    feeder_cycle = feeder_distance / 20.0 + 0.25
    feeder_cycles = floor(12 * hours / feeder_cycle)
    park_riders = min(
        attendance, car_riders, feeder_cycles * seats,
        1000 * factors.park_ride_utilization.base * inputs.average_vehicle_occupancy,
    )
    feeder_cycles = min(feeder_cycles, ceil(park_riders / seats)) if seats > 0 else 0
    feeder_miles = feeder_cycles * 2 * feeder_distance
    add(
        "Remote park-and-ride + shuttle hubs", "Park-and-ride hubs", park_riders,
        park_riders, feeder_distance, feeder_miles, feeder_miles * electric_factor,
        "Reuse up to 1,000 existing remote spaces, with at most 12 electric feeder buses dispatched to "
        "reserved demand. The shuttle and avoided car leg use the same assumed return corridor; driving to "
        "the hub remains. Empty return legs are charged. Validate the hub location and minimum load before deployment.",
    )

    departures = floor(6 * hours)
    transit_riders = min(
        attendance, car_riders / 0.5, departures * factors.transit_passengers_per_departure.base
        * factors.service_load_factor.base,
    )
    transit_seats = factors.transit_passengers_per_departure.base * factors.service_load_factor.base
    departures = min(departures, ceil(transit_riders / transit_seats)) if transit_seats > 0 else 0
    transit_miles = departures * 2 * inputs.transit_round_trip_miles
    add(
        "Increase rail/transit frequency", "More transit service", transit_riders,
        min(transit_riders * 0.5, car_riders), inputs.average_private_trip_miles,
        transit_miles, transit_miles * electric_factor,
        "Up to six added electric transit-vehicle departures/hour, sized to reserved demand with a 50% "
        "car-trip replacement target. Capacity uses the transit registry; emissions use an electric "
        "service-vehicle proxy, not a calibrated rail-train factor. Require a passing CO2e screen and validate network capacity.",
    )

    add(
        "Electric shuttle/bus fleet", "Electric bus fleet", baseline_riders,
        0, 0, 0, -baseline_miles * (service_factor - electric_factor),
        "Replace the hypothetical 12-bus conventional fleet on the same timetable. "
        "Assume electricity-related operating CO2e is 40% of the conventional fleet's CO2e "
        "(a scenario assumption, not a local grid estimate). Riders receive cleaner service; "
        "no new riders, additional capacity, or vehicle-mile savings are credited.",
    )
    return rows
