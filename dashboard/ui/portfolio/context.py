"""Prepare the single auditable frame consumed by every Portfolio objective."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd

from dashboard.domain.overview import PACKAGE_NAMES, build_portfolio_overview
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.models.resilience import stress_access_capacity

# Maps each named package to the column-name prefix used for its attached
# outcome fields (see _with_package_outcomes).
PACKAGE_KEYS = {
    "Baseline": "baseline",
    "Operational Package": "operational",
    "Capital Package": "capital",
}


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
    frame = _with_track1_metrics(frame, artifacts)
    frame = _with_gap_evidence(frame, metrics, artifacts.get("gtfs", {}))
    frame = _with_parking_evidence(frame, artifacts.get("parking_density", {}))
    frame = _with_package_outcomes(frame, artifacts.get("intervention_outcomes", []))
    return _with_geography(frame)


def _with_geography(frame: pd.DataFrame) -> pd.DataFrame:
    """Attach each host city's pinned venue latitude/longitude for mapping."""

    frame = frame.copy()
    frame["lat"] = frame["city"].map(lambda city: HOST_CITIES.get(city, {}).get("lat"))
    frame["lon"] = frame["city"].map(lambda city: HOST_CITIES.get(city, {}).get("lon"))
    return frame


def _outcome_row(
    city: str,
    match_id: str,
    package_name: str,
    outcome_rows: list[Mapping[str, Any]],
) -> Mapping[str, Any]:
    for row in outcome_rows:
        package = row.get("package", {})
        name = package.get("name") if isinstance(package, Mapping) else row.get("name")
        if (
            str(row.get("city")) == city
            and str(row.get("match_id")) == match_id
            and str(name) == package_name
        ):
            return row
    return {}


def _with_package_outcomes(
    frame: pd.DataFrame, outcome_rows: list[Mapping[str, Any]]
) -> pd.DataFrame:
    """Attach each named package's modeled outcome for the representative match.

    Lets the Investments tab offer a real package selector (Baseline / Operational
    / Capital) without evaluating the intervention model live from the UI layer -
    every package is already evaluated once in build_transportation_bundle.
    """

    records: list[dict[str, Any]] = []
    for row in frame.to_dict("records"):
        city = str(row.get("city"))
        match_id = str(row.get("representative_match_id") or "")
        entry: dict[str, Any] = {}
        for package_name in PACKAGE_NAMES:
            prefix = PACKAGE_KEYS[package_name]
            outcome = _outcome_row(city, match_id, package_name, outcome_rows)
            entry[f"{prefix}_cost_low"] = outcome.get("cost_low")
            entry[f"{prefix}_cost_base"] = outcome.get("cost_base")
            entry[f"{prefix}_cost_high"] = outcome.get("cost_high")
            entry[f"{prefix}_gap_resolved"] = outcome.get("gap_resolved_passengers")
            entry[f"{prefix}_net_co2e_base"] = outcome.get("net_co2e_kg_base")
            entry[f"{prefix}_vehicle_trips_base"] = outcome.get("venue_vehicle_trips_base")
            entry[f"{prefix}_arrival_shifted_pph"] = outcome.get("arrival_shifted_pph_base")
            entry[f"{prefix}_status"] = outcome.get("status", "unavailable")
        records.append(entry)
    additions = pd.DataFrame(records)
    # build_portfolio_overview already attaches baseline_vehicle_trips_{low,base,high}
    # (from the same Baseline package outcome) - keep those, don't duplicate them.
    additions = additions.drop(
        columns=[column for column in additions.columns if column in frame.columns]
    )
    return pd.concat([frame.reset_index(drop=True), additions], axis=1)


# Columns computed in dashboard/domain/scoring.py that build_city_comparison
# does not carry forward, but the gap-analysis and stop-density views need.
_GAP_EVIDENCE_METRICS_COLUMNS = (
    "city",
    "capacity",
    "transit_score",
    "transit_status",
    "parking_score",
    "gap_score",
    "gap_status",
    "balanced_score",
    "balanced_score_status",
    "first_last_mile_gap",
    "avg_temp_c",
    "transit_stops_0_5mi",
    "nearest_stop_mi",
    "route_count",
    "feed_status",
)


def _with_gap_evidence(
    frame: pd.DataFrame, metrics: pd.DataFrame, gtfs: Mapping[str, Any]
) -> pd.DataFrame:
    available = [c for c in _GAP_EVIDENCE_METRICS_COLUMNS if c in metrics.columns]
    merged = frame.merge(metrics[available], on="city", how="left")

    gtfs_rows = []
    for city in merged["city"]:
        entry = gtfs.get(str(city), {}) if isinstance(gtfs, Mapping) else {}
        agencies = entry.get("agencies") if isinstance(entry, Mapping) else None
        stop_points = entry.get("stop_points_2mi") if isinstance(entry, Mapping) else None
        nearest_stop_agency = None
        if stop_points:
            nearest_point = min(stop_points, key=lambda point: point.get("distance_mi", float("inf")))
            candidate = nearest_point.get("agency")
            nearest_stop_agency = candidate if candidate and candidate != "Agency unavailable" else None
        gtfs_rows.append(
            {
                "gtfs_stops_1mi": entry.get("stops_1mi") if isinstance(entry, Mapping) else None,
                "gtfs_stops_2mi": entry.get("stops_2mi") if isinstance(entry, Mapping) else None,
                "gtfs_agencies": ", ".join(agencies) if agencies else None,
                "nearest_stop_agency": nearest_stop_agency,
            }
        )
    return pd.concat([merged.reset_index(drop=True), pd.DataFrame(gtfs_rows)], axis=1)


def _with_parking_evidence(frame: pd.DataFrame, parking: Mapping[str, Any]) -> pd.DataFrame:
    """Attach each host city's real OSM parking-facility density, when the snapshot exists.

    dashboard/pipeline/public/parking.py produces this snapshot offline (it needs live
    OSM/Overpass network access); cities missing from the snapshot, or the whole
    artifact if it hasn't been generated yet, simply get null columns here.
    """

    rows = []
    for city in frame["city"]:
        entry = parking.get(str(city), {}) if isinstance(parking, Mapping) else {}
        entry = entry if isinstance(entry, Mapping) else {}
        rows.append(
            {
                "parking_count_0_5mi": entry.get("facility_count_0_5mi"),
                "parking_count_1mi": entry.get("facility_count_1mi"),
                "parking_count_2mi": entry.get("facility_count_2mi"),
                "parking_tagged_capacity_0_5mi": entry.get("tagged_capacity_0_5mi"),
                "parking_tagged_capacity_1mi": entry.get("tagged_capacity_1mi"),
                "parking_tagged_capacity_2mi": entry.get("tagged_capacity_2mi"),
                "parking_facilities_with_capacity_tag": entry.get("facilities_with_capacity_tag"),
                "parking_total_facilities": entry.get("total_facilities"),
                "parking_status": entry.get("status", "unavailable"),
            }
        )
    return pd.concat([frame.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def _with_access_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    demand = pd.to_numeric(result.get("peak_demand_pph"), errors="coerce")
    gap = pd.to_numeric(result.get("capacity_qualified_gap_pph"), errors="coerce").clip(lower=0)
    result["scheduled_transit_capacity_pph"] = (demand - gap).clip(lower=0)
    result["scheduled_coverage_pct"] = np.where(
        demand > 0,
        result["scheduled_transit_capacity_pph"] / demand * 100,
        np.nan,
    )
    return result


def _direction_peak(rows: list[Mapping[str, Any]], direction: str, case: str) -> tuple[float | None, float | None]:
    field = f"{direction}_{case}"
    candidates = [row for row in rows if pd.notna(pd.to_numeric(row.get(field), errors="coerce"))]
    if not candidates:
        return None, None
    peak = max(candidates, key=lambda row: float(row.get(field) or 0))
    return float(peak.get(field) or 0), float(peak.get("hours_from_kickoff") or 0)


def _with_track1_metrics(frame: pd.DataFrame, artifacts: Mapping[str, Any]) -> pd.DataFrame:
    result = _with_access_metrics(frame)
    movements = {
        (str(row.get("city")), str(row.get("match_id"))): row for row in artifacts.get("movement_scenarios", [])
    }
    forecasts_by_city: dict[str, list[Mapping[str, Any]]] = {}
    for forecast_row in artifacts.get("visitor_flow_forecasts", []):
        forecasts_by_city.setdefault(str(forecast_row.get("city")), []).append(forecast_row)
    access_rows = list(artifacts.get("access_gaps", []))
    access = {(str(row.get("city")), str(row.get("match_id"))): row for row in access_rows}
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
            "movement_uncertainty": str(movement.get("uncertainty_type") or "not available"),
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

        city_access = [item for item in access_rows if str(item.get("city")) == city]
        zero_capacity_matches = sum(
            float(item.get("transit_capacity_base") or 0) <= 0 and bool(item.get("capacity_qualified", False))
            for item in city_access
        )
        walk = walking.get(city, {}) if isinstance(walking, Mapping) else {}
        target = walk.get("target_stop") or {}
        demand_value = pd.to_numeric(row.get("peak_demand_pph"), errors="coerce")
        capacity_value = pd.to_numeric(row.get("scheduled_transit_capacity_pph"), errors="coerce")
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
                "network_walk_distance_m": access_row.get("network_walk_distance_m"),
                "walking_status": str(access_row.get("walking_status") or "unavailable"),
                "service_span_after_match_min": access_row.get("service_span_after_match_min"),
                "route_heat_exposure_c": access_row.get("route_heat_exposure_c"),
                "target_stop_name": target.get("name") or "No event stop path",
                "target_route": target.get("route") or "Not established",
                "walk_detour_ratio": walk.get("detour_ratio"),
                "accessibility_status": str(walk.get("accessibility_status") or "not measured"),
                "stress_coverage_pct": resilience["stressed_coverage_pct"],
                "stress_gap_pph": resilience["stressed_gap_pph"],
                "stress_demand_pph": resilience["stressed_demand_pph"],
                "stress_capacity_pph": resilience["stressed_capacity_pph"],
            }
        )
    return pd.concat([result.reset_index(drop=True), pd.DataFrame(additions)], axis=1)


# Ranks each real FIFA schedule stage by tournament depth so "furthest round
# played" can be computed per city; bronze_final ties semi_final since both
# require having reached the semifinal.
_STAGE_RANK_BY_KEY = {
    "group": 0,
    "round of 32": 1,
    "round of 16": 2,
    "quarter-final": 3,
    "semi-final": 4,
    "bronze final": 4,
    "final": 5,
}
_STAGE_DISPLAY_BY_KEY = {
    "group": "Group",
    "round of 32": "Round of 32",
    "round of 16": "Round of 16",
    "quarter-final": "Quarterfinal",
    "semi-final": "Semifinal",
    "bronze final": "3rd place",
    "final": "Final",
}


def _stage_key(stage: Any) -> str:
    normalized = str(stage or "").strip().lower()
    return "group" if normalized.startswith("group") else normalized


def _furthest_stage_label(forecasts: Sequence[Mapping[str, Any]]) -> str:
    if not forecasts:
        return "Not available"
    furthest = max(forecasts, key=lambda row: _STAGE_RANK_BY_KEY.get(_stage_key(row.get("stage")), 0))
    key = _stage_key(furthest.get("stage"))
    return _STAGE_DISPLAY_BY_KEY.get(key, str(furthest.get("stage") or "Group"))


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
    summary["furthest_stage"] = _furthest_stage_label(forecasts)
    for field in (
        "attendance_low",
        "attendance_base",
        "attendance_high",
        "non_host_market_attendees_base",
    ):
        summary[field] = sum(float(row.get(field) or 0) for row in forecasts)
    base_total = float(summary["attendance_base"] or 0)
    summary["non_host_market_share_base"] = (
        float(summary["non_host_market_attendees_base"]) / base_total if base_total else 0.0
    )
    for collection, key in (("origin_rows", "origin_type"), ("mode_rows", "mode")):
        names = {str(item.get(key)) for forecast in forecasts for item in forecast.get(collection, [])}
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
        "forecast_furthest_stage": forecast.get("furthest_stage"),
        "forecast_anchor_match_id": forecast.get("match_id"),
        "forecast_match_count": forecast.get("forecast_match_count"),
        "forecast_status": str(forecast.get("status") or "unavailable"),
        "forecast_validation_status": str(forecast.get("validation_status") or "not available"),
        "forecast_attendance_base": forecast.get("attendance_base"),
        "forecast_non_host_attendees_base": forecast.get("non_host_market_attendees_base"),
        "forecast_non_host_share_pct": (
            float(forecast.get("non_host_market_share_base")) * 100
            if pd.notna(pd.to_numeric(forecast.get("non_host_market_share_base"), errors="coerce"))
            else None
        ),
        "forecast_origin_prior_status": str(forecast.get("origin_prior_status") or "unavailable"),
        "forecast_origin_prior_coverage_pct": forecast.get("origin_prior_coverage_pct"),
        "forecast_arrival_peak_low": forecast.get("arrival_peak_low"),
        "forecast_arrival_peak_base": forecast.get("arrival_peak_base"),
        "forecast_arrival_peak_high": forecast.get("arrival_peak_high"),
        "forecast_arrival_peak_offset_hours": forecast.get("arrival_peak_offset_hours"),
        "forecast_departure_peak_low": forecast.get("departure_peak_low"),
        "forecast_departure_peak_base": forecast.get("departure_peak_base"),
        "forecast_departure_peak_high": forecast.get("departure_peak_high"),
        "forecast_departure_peak_offset_hours": forecast.get("departure_peak_offset_hours"),
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


def build_city_hourly_movement(artifacts: Mapping[str, Any]) -> pd.DataFrame:
    """Average each host city's modeled hourly arrival/departure movement across all its matches.

    One row per (city, hours_from_kickoff), so the Visitor movement tab can plot a
    single host city's average passenger curve without re-deriving it from raw
    movement_scenarios each render.
    """

    totals: dict[tuple[str, float], dict[str, float]] = {}
    match_ids: dict[str, set[str]] = {}
    for scenario in artifacts.get("movement_scenarios", []):
        city = str(scenario.get("city"))
        match_ids.setdefault(city, set()).add(str(scenario.get("match_id")))
        for hour_row in scenario.get("hourly_rows", []):
            offset = pd.to_numeric(hour_row.get("hours_from_kickoff"), errors="coerce")
            if pd.isna(offset):
                continue
            key = (city, round(float(offset), 2))
            bucket = totals.setdefault(key, {"arrivals": 0.0, "departures": 0.0, "n": 0})
            bucket["arrivals"] += float(hour_row.get("arrivals_base") or 0)
            bucket["departures"] += float(hour_row.get("departures_base") or 0)
            bucket["n"] += 1

    columns = ["city", "hours_from_kickoff", "avg_arrivals_base", "avg_departures_base", "match_count"]
    if not totals:
        return pd.DataFrame(columns=columns)
    rows = [
        {
            "city": city,
            "hours_from_kickoff": offset,
            "avg_arrivals_base": bucket["arrivals"] / bucket["n"],
            "avg_departures_base": bucket["departures"] / bucket["n"],
            "match_count": len(match_ids.get(city, ())),
        }
        for (city, offset), bucket in totals.items()
    ]
    return pd.DataFrame(rows)[columns].sort_values(["city", "hours_from_kickoff"]).reset_index(drop=True)
