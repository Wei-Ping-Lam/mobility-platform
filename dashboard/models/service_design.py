"""Shared explicit design assumptions, not measured fleet or grid performance."""

from math import floor, isfinite

# Electricity-related operating emissions relative to the conventional vehicle
# proxy. Procurement must validate energy use, grid intensity, and charging.
ELECTRIC_SERVICE_EMISSIONS_RATIO = 0.4
# Lease and temporary charging allowance relative to the registry's bus-hour proxy.
ELECTRIC_SERVICE_COST_MULTIPLIER = 1.2


def event_window_cycles(window_hours: float, cycle_hours: float) -> int:
    """Loaded arrivals per staged bus; the final empty return may finish later.

    Assume equal outbound/return time, including an equal share of turnaround.
    Count each delivery separately; emissions and costs must still include its
    complete return loop. Vehicles start at the boarding point, not the depot.
    """
    if not all(isfinite(x) and x > 0 for x in (window_hours, cycle_hours)):
        raise ValueError("Window and cycle durations must be finite and positive")
    first_arrival = cycle_hours / 2
    if window_hours < first_arrival:
        return 0
    return 1 + floor((window_hours - first_arrival) / cycle_hours + 1e-9)
