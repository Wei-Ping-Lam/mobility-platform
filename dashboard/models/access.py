"""Physical first/last-mile access gaps and transparent friction indicators."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite
from typing import Any

import pandas as pd

from dashboard.mobility_platform.contracts import (
    AccessGapResult,
    EvidenceStatus,
    MovementScenario,
)

CAPACITY_COLUMNS = (
    "vehicle_capacity_low",
    "vehicle_capacity_base",
    "vehicle_capacity_high",
)
DEFAULT_FRICTION_WEIGHTS = {
    "residual_gap": 0.40,
    "network_walk": 0.25,
    "service_span": 0.15,
    "route_heat": 0.20,
}


def build_access_gap_result(
    movement: MovementScenario | Mapping[str, Any],
    event_service: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    walk_metrics: Mapping[str, Any] | pd.Series | None = None,
    *,
    service_span_after_match_min: float | None = None,
    route_heat_exposure_c: float | None = None,
) -> AccessGapResult:
    """Calculate a match-specific peak access gap in physical units.

    ``event_service`` has one row per mode/service contribution and requires
    ``departures_per_hour`` plus low/base/high vehicle-capacity columns. Optional
    ``direction`` values are ``arrival``, ``departure``, or ``both``. Optional
    ``hour_start_local`` values limit capacity to the movement peak hour. Each row
    may carry an evidence ``status``. Vehicle capacities are planning assumptions,
    even when the departure count itself is observed from GTFS.

    ``walk_metrics`` may contain ``network_walk_distance_m``,
    ``straight_line_distance_m``, and ``status``. Network distance must not be
    shorter than straight-line distance beyond a one-metre numeric tolerance.
    """

    movement_data = movement.to_dict() if isinstance(movement, MovementScenario) else dict(movement)
    city = _required_text(movement_data, "city")
    match_id = _required_text(movement_data, "match_id")
    peak = _peak_movement(movement_data.get("hourly_rows", []))
    peak_demand = peak["demand"]
    service = _as_frame(event_service)
    walk = _as_mapping(walk_metrics)

    network_distance = _optional_nonnegative(
        walk.get("network_walk_distance_m"), "network_walk_distance_m"
    )
    straight_distance = _optional_nonnegative(
        walk.get("straight_line_distance_m"), "straight_line_distance_m"
    )
    if (
        network_distance is not None
        and straight_distance is not None
        and network_distance + 1.0 < straight_distance
    ):
        raise ValueError("network walk distance cannot be shorter than straight-line distance")

    span = service_span_after_match_min
    if span is None and "service_span_after_match_min" in service.columns and not service.empty:
        values = pd.to_numeric(service["service_span_after_match_min"], errors="coerce").dropna()
        span = float(values.max()) if not values.empty else None
    span = _optional_nonnegative(span, "service_span_after_match_min")

    heat = route_heat_exposure_c
    if heat is None:
        heat = walk.get("route_heat_exposure_c")
    heat = _optional_number(heat, "route_heat_exposure_c")

    assumptions = [
        "Peak demand is the maximum base-scenario arrivals plus departures in one modeled hour.",
        "Scheduled capacity equals event departures per hour multiplied by low/base/high vehicle-capacity assumptions.",
        "Scheduled capacity is not observed ridership and does not include unprovided crowd-control constraints.",
    ]
    capacity, transit_status, service_notes = _capacity_for_peak(service, peak)
    assumptions.extend(service_notes)

    if transit_status == EvidenceStatus.UNAVAILABLE:
        assumptions.append(
            "Transit evidence is unavailable; zero capacity fields are sentinels and the residual is not a measured service gap."
        )
        return AccessGapResult(
            city=city,
            match_id=match_id,
            status=EvidenceStatus.UNAVAILABLE,
            peak_demand_per_hour=peak_demand,
            transit_capacity_low=0.0,
            transit_capacity_base=0.0,
            transit_capacity_high=0.0,
            residual_passengers=peak_demand,
            network_walk_distance_m=network_distance,
            service_span_after_match_min=span,
            route_heat_exposure_c=heat,
            assumptions=tuple(assumptions),
        )

    status = EvidenceStatus.SCENARIO
    walk_status = _status(walk.get("status"), default=EvidenceStatus.PARTIAL)
    if transit_status == EvidenceStatus.PARTIAL or walk_status in {
        EvidenceStatus.PARTIAL,
        EvidenceStatus.UNAVAILABLE,
    }:
        status = EvidenceStatus.PARTIAL
    if network_distance is None or span is None or heat is None:
        status = EvidenceStatus.PARTIAL
        assumptions.append("One or more walk, service-span, or route-heat inputs are unavailable.")

    residual = max(peak_demand - capacity["base"], 0.0)
    return AccessGapResult(
        city=city,
        match_id=match_id,
        status=status,
        peak_demand_per_hour=peak_demand,
        transit_capacity_low=capacity["low"],
        transit_capacity_base=capacity["base"],
        transit_capacity_high=capacity["high"],
        residual_passengers=residual,
        network_walk_distance_m=network_distance,
        service_span_after_match_min=span,
        route_heat_exposure_c=heat,
        assumptions=tuple(assumptions),
    )


def access_friction_index(
    result: AccessGapResult | Mapping[str, Any],
    weights: Mapping[str, float] | None = None,
    *,
    walk_reference_m: float = 1600.0,
    target_service_span_min: float = 180.0,
    heat_comfort_c: float = 26.0,
    heat_ceiling_c: float = 40.0,
) -> dict[str, Any]:
    """Return an optional 0-100 friction index with visible components/weights.

    Higher values mean more friction. Missing optional components are excluded and
    the remaining weights are explicitly renormalized. Unavailable transit yields
    no index because a missing feed must never be interpreted as zero service.
    """

    data = result.to_dict() if isinstance(result, AccessGapResult) else dict(result)
    status = _status(data.get("status"), default=EvidenceStatus.UNAVAILABLE)
    configured_weights = _validate_weights(
        DEFAULT_FRICTION_WEIGHTS if weights is None else weights
    )
    if status == EvidenceStatus.UNAVAILABLE:
        return {
            "friction_index": None,
            "status": EvidenceStatus.UNAVAILABLE.value,
            "components": {},
            "configured_weights": configured_weights,
            "effective_weights": {},
            "interpretation": "Unavailable because transit evidence is unavailable.",
        }
    if walk_reference_m <= 0 or target_service_span_min <= 0:
        raise ValueError("walk and service-span references must be greater than zero")
    if heat_ceiling_c <= heat_comfort_c:
        raise ValueError("heat_ceiling_c must be greater than heat_comfort_c")

    peak = _optional_nonnegative(data.get("peak_demand_per_hour"), "peak_demand_per_hour") or 0.0
    residual = _optional_nonnegative(data.get("residual_passengers"), "residual_passengers") or 0.0
    components: dict[str, float] = {
        "residual_gap": _clip(100.0 * residual / peak if peak else 0.0),
    }
    walk = _optional_nonnegative(data.get("network_walk_distance_m"), "network_walk_distance_m")
    if walk is not None:
        components["network_walk"] = _clip(100.0 * walk / walk_reference_m)
    span = _optional_nonnegative(
        data.get("service_span_after_match_min"), "service_span_after_match_min"
    )
    if span is not None:
        components["service_span"] = _clip(
            100.0 * max(target_service_span_min - span, 0.0) / target_service_span_min
        )
    heat = _optional_number(data.get("route_heat_exposure_c"), "route_heat_exposure_c")
    if heat is not None:
        components["route_heat"] = _clip(
            100.0 * max(heat - heat_comfort_c, 0.0) / (heat_ceiling_c - heat_comfort_c)
        )

    active_weight = sum(configured_weights[name] for name in components)
    if active_weight <= 0:
        raise ValueError("at least one available friction component must have positive weight")
    effective = {name: configured_weights[name] / active_weight for name in components}
    index = sum(components[name] * effective[name] for name in components)
    friction_status = status
    if set(components) != set(DEFAULT_FRICTION_WEIGHTS):
        friction_status = EvidenceStatus.PARTIAL
    return {
        "friction_index": round(index, 2),
        "status": friction_status.value,
        "components": {name: round(value, 2) for name, value in components.items()},
        "configured_weights": configured_weights,
        "effective_weights": {name: round(value, 6) for name, value in effective.items()},
        "parameters": {
            "walk_reference_m": walk_reference_m,
            "target_service_span_min": target_service_span_min,
            "heat_comfort_c": heat_comfort_c,
            "heat_ceiling_c": heat_ceiling_c,
        },
        "interpretation": "0 is lower modeled friction; 100 is higher modeled friction. This is a transparent planning index, not observed travel behavior.",
    }


def access_results_frame(
    results: AccessGapResult | Mapping[str, Any] | Sequence[AccessGapResult | Mapping[str, Any]],
    *,
    include_friction: bool = False,
) -> pd.DataFrame:
    """Convert access contracts to a table, optionally adding friction fields."""

    if isinstance(results, (AccessGapResult, Mapping)):
        items = [results]
    else:
        items = list(results)
    rows = []
    for item in items:
        data = item.to_dict() if isinstance(item, AccessGapResult) else dict(item)
        row = dict(data)
        if include_friction:
            friction = access_friction_index(data)
            row["friction_index"] = friction["friction_index"]
            row["friction_status"] = friction["status"]
        rows.append(row)
    return pd.DataFrame(rows)


def _peak_movement(hourly_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not hourly_rows:
        return {"timestamp": None, "direction": "both", "demand": 0.0}
    candidates = []
    for row in hourly_rows:
        arrivals = _optional_nonnegative(row.get("arrivals_base"), "arrivals_base") or 0.0
        departures = _optional_nonnegative(row.get("departures_base"), "departures_base") or 0.0
        timestamp = pd.to_datetime(row.get("timestamp_local"), errors="coerce")
        direction = "arrival" if arrivals > departures else "departure"
        if arrivals == departures:
            direction = "both"
        candidates.append(
            {
                "timestamp": None if pd.isna(timestamp) else timestamp,
                "direction": direction,
                "demand": arrivals + departures,
            }
        )
    return max(candidates, key=lambda row: row["demand"])


def _capacity_for_peak(
    service: pd.DataFrame, peak: Mapping[str, Any]
) -> tuple[dict[str, float], EvidenceStatus, list[str]]:
    empty = {"low": 0.0, "base": 0.0, "high": 0.0}
    if service.empty:
        return empty, EvidenceStatus.UNAVAILABLE, ["No event transit service rows were supplied."]
    required = {"departures_per_hour", *CAPACITY_COLUMNS}
    if not required.issubset(service.columns):
        return empty, EvidenceStatus.UNAVAILABLE, [
            f"Transit service is missing required columns: {sorted(required - set(service.columns))}."
        ]

    frame = service.copy()
    statuses = (
        frame["status"].map(lambda value: _status(value, default=EvidenceStatus.PARTIAL))
        if "status" in frame.columns
        else pd.Series(EvidenceStatus.PARTIAL, index=frame.index)
    )
    usable_mask = statuses != EvidenceStatus.UNAVAILABLE
    if not usable_mask.any():
        return empty, EvidenceStatus.UNAVAILABLE, ["All event transit service rows are unavailable."]
    frame = frame[usable_mask].copy()
    usable_statuses = statuses[usable_mask]
    quality_notes: list[str] = []
    quality_drops = 0

    if "direction" in frame.columns:
        directions = frame["direction"].astype(str).str.lower()
        valid_direction = directions.isin({"arrival", "departure", "both"})
        invalid_directions = int((~valid_direction).sum())
        if invalid_directions:
            quality_drops += invalid_directions
            quality_notes.append(
                f"Dropped {invalid_directions} transit rows with invalid direction values."
            )
        frame = frame[valid_direction]
        directions = directions[valid_direction]
        if peak["direction"] != "both":
            frame = frame[directions.isin({peak["direction"], "both"})]

    if "hour_start_local" in frame.columns and peak["timestamp"] is not None:
        service_hours = pd.to_datetime(frame["hour_start_local"], errors="coerce")
        valid_hours = service_hours.notna()
        invalid_hours = int((~valid_hours).sum())
        if invalid_hours == len(frame) and invalid_hours:
            return empty, EvidenceStatus.UNAVAILABLE, [
                "All applicable transit rows have invalid event-hour timestamps."
            ]
        if invalid_hours:
            quality_drops += invalid_hours
            quality_notes.append(
                f"Dropped {invalid_hours} transit rows with invalid event-hour timestamps."
            )
        peak_hour = peak["timestamp"].floor("h")
        frame = frame[valid_hours & (service_hours.dt.floor("h") == peak_hour)]

    numeric_columns = ["departures_per_hour", *CAPACITY_COLUMNS]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    invalid = frame[numeric_columns].isna().any(axis=1) | (frame[numeric_columns] < 0).any(axis=1)
    dropped = int(invalid.sum())
    frame = frame[~invalid]
    if frame.empty:
        notes = ["No valid transit rows apply to the modeled peak hour/direction."]
        if dropped:
            notes.append(f"Dropped {dropped} transit rows with invalid physical values.")
        notes.extend(quality_notes)
        # A valid feed with no applicable departures is an observed zero, not missing data.
        status = EvidenceStatus.PARTIAL if dropped or quality_drops else EvidenceStatus.SCENARIO
        return empty, status, notes

    capacity = {
        level: float((frame["departures_per_hour"] * frame[f"vehicle_capacity_{level}"]).sum())
        for level in ("low", "base", "high")
    }
    if not capacity["low"] <= capacity["base"] <= capacity["high"]:
        raise ValueError("transit capacity assumptions must be ordered low <= base <= high")
    status = EvidenceStatus.SCENARIO
    if (
        dropped
        or quality_drops
        or (usable_statuses == EvidenceStatus.PARTIAL).any()
        or (~usable_mask).any()
    ):
        status = EvidenceStatus.PARTIAL
    notes = list(quality_notes)
    if dropped:
        notes.append(f"Dropped {dropped} transit rows with invalid physical values.")
    return capacity, status, notes


def _validate_weights(weights: Mapping[str, float]) -> dict[str, float]:
    unknown = set(weights) - set(DEFAULT_FRICTION_WEIGHTS)
    missing = set(DEFAULT_FRICTION_WEIGHTS) - set(weights)
    if unknown or missing:
        raise ValueError(
            f"friction weights require exactly {sorted(DEFAULT_FRICTION_WEIGHTS)}; "
            f"missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    values = {name: _optional_nonnegative(value, f"{name} weight") or 0.0 for name, value in weights.items()}
    if sum(values.values()) <= 0:
        raise ValueError("friction weights must contain a positive value")
    return values


def _as_frame(
    value: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, Mapping):
        return pd.DataFrame([dict(value)])
    return pd.DataFrame(value)


def _as_mapping(value: Mapping[str, Any] | pd.Series | None) -> Mapping[str, Any]:
    if value is None:
        return {}
    return value.to_dict() if isinstance(value, pd.Series) else value


def _required_text(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"{key} is required")
    return str(value)


def _status(value: Any, default: EvidenceStatus) -> EvidenceStatus:
    if isinstance(value, EvidenceStatus):
        return value
    if value is None:
        return default
    try:
        return EvidenceStatus(str(value))
    except ValueError:
        return default


def _optional_number(value: Any, name: str) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if pd.isna(number) or not isfinite(number):
        if pd.isna(number):
            return None
        raise ValueError(f"{name} must be finite")
    return number


def _optional_nonnegative(value: Any, name: str) -> float | None:
    number = _optional_number(value, name)
    if number is not None and number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _clip(value: float) -> float:
    return min(max(float(value), 0.0), 100.0)
