"""Prepare the single auditable frame consumed by every Portfolio objective."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from dashboard.domain.overview import build_portfolio_overview
from dashboard.models.resilience import stress_access_capacity


def build_portfolio_frame(
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    weights: Mapping[str, float],
) -> pd.DataFrame:
    frame = build_portfolio_overview(
        metrics,
        artifacts.get("access_gaps", []),
        artifacts.get("investment_recommendations", []),
        artifacts.get("intervention_outcomes", []),
        weights=weights,
    )
    return _with_track1_metrics(frame, artifacts)


def _with_access_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    demand = pd.to_numeric(result.get("peak_demand_pph"), errors="coerce")
    gap = pd.to_numeric(
        result.get("capacity_qualified_gap_pph"), errors="coerce"
    ).clip(lower=0)
    result["scheduled_transit_capacity_pph"] = (demand - gap).clip(lower=0)
    result["scheduled_coverage_pct"] = np.where(
        demand > 0,
        result["scheduled_transit_capacity_pph"] / demand * 100,
        np.nan,
    )
    return result


def _direction_peak(
    rows: list[Mapping[str, Any]], direction: str, case: str
) -> tuple[float | None, float | None]:
    field = f"{direction}_{case}"
    candidates = [
        row
        for row in rows
        if pd.notna(pd.to_numeric(row.get(field), errors="coerce"))
    ]
    if not candidates:
        return None, None
    peak = max(candidates, key=lambda row: float(row.get(field) or 0))
    return float(peak.get(field) or 0), float(
        peak.get("hours_from_kickoff") or 0
    )


def _with_track1_metrics(
    frame: pd.DataFrame, artifacts: Mapping[str, Any]
) -> pd.DataFrame:
    result = _with_access_metrics(frame)
    movements = {
        (str(row.get("city")), str(row.get("match_id"))): row
        for row in artifacts.get("movement_scenarios", [])
    }
    forecasts_by_city: dict[str, list[Mapping[str, Any]]] = {}
    for forecast_row in artifacts.get("visitor_flow_forecasts", []):
        forecasts_by_city.setdefault(
            str(forecast_row.get("city")), []
        ).append(forecast_row)
    access_rows = list(artifacts.get("access_gaps", []))
    access = {
        (str(row.get("city")), str(row.get("match_id"))): row
        for row in access_rows
    }
    walking = artifacts.get("walking_networks", {})

    additions: list[dict[str, Any]] = []
    for row in result.to_dict("records"):
        city = str(row.get("city"))
        match_id = str(row.get("representative_match_id") or "")
        movement = movements.get((city, match_id), {})
        forecast = _city_forecast_summary(forecasts_by_city.get(city, []))
        hourly = list(movement.get("hourly_rows", []))
        movement_fields: dict[str, Any] = {
            "movement_status": str(movement.get("status") or "unavailable"),
            "movement_uncertainty": str(
                movement.get("uncertainty_type") or "not available"
            ),
        }
        for direction in ("arrivals", "departures"):
            prefix = "arrival" if direction == "arrivals" else "departure"
            for case in ("low", "base", "high"):
                value, offset = _direction_peak(hourly, direction, case)
                movement_fields[f"{prefix}_peak_{case}"] = value
                if case == "base":
                    movement_fields[f"{prefix}_peak_offset_hours"] = offset

        access_row = access.get((city, match_id), {})
        peak_row = max(
            hourly,
            key=lambda item: float(item.get("total_movement_base") or 0),
            default={},
        )
        arrivals = float(peak_row.get("arrivals_base") or 0)
        departures = float(peak_row.get("departures_base") or 0)
        peak_direction = "arrival" if arrivals > departures else "departure"
        if arrivals == departures:
            peak_direction = "both"

        city_access = [
            item for item in access_rows if str(item.get("city")) == city
        ]
        zero_capacity_matches = sum(
            float(item.get("transit_capacity_base") or 0) <= 0
            and bool(item.get("capacity_qualified", False))
            for item in city_access
        )
        walk = walking.get(city, {}) if isinstance(walking, Mapping) else {}
        target = walk.get("target_stop") or {}
        demand_value = pd.to_numeric(row.get("peak_demand_pph"), errors="coerce")
        capacity_value = pd.to_numeric(
            row.get("scheduled_transit_capacity_pph"), errors="coerce"
        )
        resilience = (
            stress_access_capacity(demand_value, capacity_value)
            if pd.notna(demand_value) and pd.notna(capacity_value)
            else {
                "stressed_coverage_pct": None,
                "stressed_gap_pph": None,
                "stressed_demand_pph": None,
                "stressed_capacity_pph": None,
            }
        )
        additions.append(
            {
                **movement_fields,
                **_forecast_fields(forecast),
                "peak_direction": peak_direction,
                "peak_offset_hours": peak_row.get("hours_from_kickoff"),
                "zero_capacity_matches": zero_capacity_matches,
                "city_match_count": len(city_access),
                "network_walk_distance_m": access_row.get(
                    "network_walk_distance_m"
                ),
                "walking_status": str(
                    access_row.get("walking_status") or "unavailable"
                ),
                "service_span_after_match_min": access_row.get(
                    "service_span_after_match_min"
                ),
                "route_heat_exposure_c": access_row.get(
                    "route_heat_exposure_c"
                ),
                "target_stop_name": target.get("name")
                or "No event stop path",
                "target_route": target.get("route") or "Not established",
                "walk_detour_ratio": walk.get("detour_ratio"),
                "accessibility_status": str(
                    walk.get("accessibility_status") or "not measured"
                ),
                "stress_coverage_pct": resilience["stressed_coverage_pct"],
                "stress_gap_pph": resilience["stressed_gap_pph"],
                "stress_demand_pph": resilience["stressed_demand_pph"],
                "stress_capacity_pph": resilience["stressed_capacity_pph"],
            }
        )
    return pd.concat(
        [result.reset_index(drop=True), pd.DataFrame(additions)], axis=1
    )


def _city_forecast_summary(
    forecasts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    if not forecasts:
        return {}
    anchor = max(
        forecasts,
        key=lambda row: float(row.get("non_host_market_attendees_base") or 0),
    )
    summary: dict[str, Any] = dict(anchor)
    summary["forecast_match_count"] = len(forecasts)
    for field in (
        "attendance_low",
        "attendance_base",
        "attendance_high",
        "non_host_market_attendees_base",
    ):
        summary[field] = sum(float(row.get(field) or 0) for row in forecasts)
    base_total = float(summary["attendance_base"] or 0)
    summary["non_host_market_share_base"] = (
        float(summary["non_host_market_attendees_base"]) / base_total
        if base_total
        else 0.0
    )
    for collection, key in (("origin_rows", "origin_type"), ("mode_rows", "mode")):
        names = {
            str(item.get(key))
            for forecast in forecasts
            for item in forecast.get(collection, [])
        }
        rows: list[dict[str, Any]] = []
        for name in sorted(names):
            combined: dict[str, Any] = {key: name}
            for case in ("low", "base", "high"):
                count = sum(
                    float(item.get(f"attendees_{case}") or 0)
                    for forecast in forecasts
                    for item in forecast.get(collection, [])
                    if str(item.get(key)) == name
                )
                total = float(summary[f"attendance_{case}"] or 0)
                combined[f"attendees_{case}"] = count
                combined[f"share_{case}"] = count / total if total else 0.0
            rows.append(combined)
        summary[collection] = rows
    return summary


def _forecast_fields(forecast: Mapping[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "forecast_stage": forecast.get("stage"),
        "forecast_anchor_match_id": forecast.get("match_id"),
        "forecast_match_count": forecast.get("forecast_match_count"),
        "forecast_status": str(forecast.get("status") or "unavailable"),
        "forecast_validation_status": str(
            forecast.get("validation_status") or "not available"
        ),
        "forecast_attendance_base": forecast.get("attendance_base"),
        "forecast_non_host_attendees_base": forecast.get(
            "non_host_market_attendees_base"
        ),
        "forecast_non_host_share_pct": (
            float(forecast.get("non_host_market_share_base")) * 100
            if pd.notna(
                pd.to_numeric(
                    forecast.get("non_host_market_share_base"), errors="coerce"
                )
            )
            else None
        ),
        "forecast_origin_prior_status": str(
            forecast.get("origin_prior_status") or "unavailable"
        ),
        "forecast_origin_prior_coverage_pct": forecast.get(
            "origin_prior_coverage_pct"
        ),
        "forecast_arrival_peak_low": forecast.get("arrival_peak_low"),
        "forecast_arrival_peak_base": forecast.get("arrival_peak_base"),
        "forecast_arrival_peak_high": forecast.get("arrival_peak_high"),
        "forecast_arrival_peak_offset_hours": forecast.get(
            "arrival_peak_offset_hours"
        ),
        "forecast_departure_peak_low": forecast.get("departure_peak_low"),
        "forecast_departure_peak_base": forecast.get("departure_peak_base"),
        "forecast_departure_peak_high": forecast.get("departure_peak_high"),
        "forecast_departure_peak_offset_hours": forecast.get(
            "departure_peak_offset_hours"
        ),
    }
    origin_columns = {
        "Host market": "origin_host_market",
        "Nearby U.S.": "origin_nearby_us",
        "Long-distance U.S.": "origin_long_distance_us",
        "International / unobserved": "origin_international",
    }
    for row in forecast.get("origin_rows", []):
        prefix = origin_columns.get(str(row.get("origin_type")))
        if prefix:
            fields[f"{prefix}_attendees_base"] = row.get("attendees_base")
            fields[f"{prefix}_share_pct"] = (
                float(row.get("share_base")) * 100
                if pd.notna(pd.to_numeric(row.get("share_base"), errors="coerce"))
                else None
            )
    mode_columns = {
        "Scheduled transit": "mode_scheduled_transit",
        "Event shuttle / coach": "mode_shuttle_coach",
        "Private vehicle / taxi": "mode_private_taxi",
        "Walk / bike to venue": "mode_walk_bike",
    }
    for row in forecast.get("mode_rows", []):
        prefix = mode_columns.get(str(row.get("mode")))
        if prefix:
            fields[f"{prefix}_attendees_base"] = row.get("attendees_base")
            fields[f"{prefix}_share_pct"] = (
                float(row.get("share_base")) * 100
                if pd.notna(pd.to_numeric(row.get("share_base"), errors="coerce"))
                else None
            )
    return fields
