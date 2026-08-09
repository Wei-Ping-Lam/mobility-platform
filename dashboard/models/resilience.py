"""Transparent transportation resilience stress tests in physical units."""

from __future__ import annotations

from math import isfinite
from typing import Any


def stress_access_capacity(
    peak_demand_per_hour: Any,
    scheduled_capacity_per_hour: Any,
    *,
    demand_surge_pct: float = 10.0,
    capacity_loss_pct: float = 20.0,
) -> dict[str, float]:
    """Apply a common demand-and-service shock to one event-hour access screen.

    This is a sensitivity test, not a probability-weighted disruption forecast.
    Coverage is scheduled passenger capacity divided by modeled peak movement.
    """

    demand = _nonnegative(peak_demand_per_hour, "peak_demand_per_hour")
    capacity = _nonnegative(scheduled_capacity_per_hour, "scheduled_capacity_per_hour")
    surge = _percentage(demand_surge_pct, "demand_surge_pct")
    loss = _percentage(capacity_loss_pct, "capacity_loss_pct")

    stressed_demand = demand * (1.0 + surge / 100.0)
    stressed_capacity = capacity * (1.0 - loss / 100.0)
    baseline_coverage = min(capacity / demand * 100.0, 100.0) if demand else 0.0
    stressed_coverage = (
        min(stressed_capacity / stressed_demand * 100.0, 100.0)
        if stressed_demand
        else 0.0
    )
    stressed_gap = max(stressed_demand - stressed_capacity, 0.0)
    return {
        "baseline_coverage_pct": round(baseline_coverage, 3),
        "stressed_demand_pph": round(stressed_demand, 3),
        "stressed_capacity_pph": round(stressed_capacity, 3),
        "stressed_coverage_pct": round(stressed_coverage, 3),
        "stressed_gap_pph": round(stressed_gap, 3),
        "coverage_change_points": round(stressed_coverage - baseline_coverage, 3),
        "demand_surge_pct": surge,
        "capacity_loss_pct": loss,
    }


def _nonnegative(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return number


def _percentage(value: Any, name: str) -> float:
    number = _nonnegative(value, name)
    if number > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return number
