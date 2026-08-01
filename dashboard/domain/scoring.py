"""Transparent readiness scoring and evidence-gated city metrics."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd

from dashboard.mobility_platform.contracts import EvidenceStatus, ScenarioConfig, ScenarioResult
from dashboard.mobility_platform.mappings import HOST_CITIES


DEFAULT_WEIGHTS = {
    "balanced": {"transit": 0.35, "heat": 0.20, "uhi": 0.15, "access": 0.30},
    "transit_access": {"transit": 0.50, "heat": 0.10, "uhi": 0.10, "access": 0.30},
    "heat_resilience": {"transit": 0.25, "heat": 0.35, "uhi": 0.25, "access": 0.15},
    "sustainability": {"transit": 0.30, "heat": 0.20, "uhi": 0.25, "access": 0.25},
}

DIMENSIONS = ("transit", "heat", "uhi", "access")
OBSERVED_STATUSES = {EvidenceStatus.OBSERVED.value, EvidenceStatus.DERIVED.value}


def clip_score(value: float | int | None) -> float | None:
    if value is None or not np.isfinite(float(value)):
        return None
    return float(np.clip(value, 0.0, 100.0))


def normalize_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    values = dict(weights or DEFAULT_WEIGHTS["balanced"])
    values = {dimension: max(0.0, float(values.get(dimension, 0.0))) for dimension in DIMENSIONS}
    total = sum(values.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS["balanced"])
    return {dimension: values[dimension] / total for dimension in DIMENSIONS}


def calculate_noaa_heat_index_c(temp_c: float, humidity: float) -> float:
    """Return the NOAA Rothfusz heat index where applicable, otherwise air temp."""

    if not np.isfinite(temp_c) or not np.isfinite(humidity):
        return float("nan")
    temp_f = temp_c * 9 / 5 + 32
    rh = float(np.clip(humidity, 0, 100))
    if temp_f < 80 or rh < 40:
        return float(temp_c)
    hi_f = (
        -42.379 + 2.04901523 * temp_f + 10.14333127 * rh
        - 0.22475541 * temp_f * rh - 6.83783e-3 * temp_f**2
        - 5.481717e-2 * rh**2 + 1.22874e-3 * temp_f**2 * rh
        + 8.5282e-4 * temp_f * rh**2 - 1.99e-6 * temp_f**2 * rh**2
    )
    if rh < 13 and 80 <= temp_f <= 112:
        adjustment = ((13 - rh) / 4) * np.sqrt((17 - abs(temp_f - 95)) / 17)
        hi_f -= adjustment
    elif rh > 85 and 80 <= temp_f <= 87:
        hi_f += ((rh - 85) / 10) * ((87 - temp_f) / 5)
    return float((hi_f - 32) * 5 / 9)


def heat_safety_score(heat_index_c: float | None) -> float | None:
    if heat_index_c is None or not np.isfinite(heat_index_c):
        return None
    return clip_score(100 - max(0.0, heat_index_c - 20) * 2.2)


def uhi_safety_score(uhi_c: float | None) -> float | None:
    if uhi_c is None or not np.isfinite(uhi_c):
        return None
    return clip_score(100 - uhi_c * 7)


def evidence_allowed(status: str, include_estimates: bool) -> bool:
    return status in OBSERVED_STATUSES or (include_estimates and status == EvidenceStatus.ESTIMATED.value)


def composite_score(row: dict[str, Any], weights: dict[str, float] | None = None, include_estimates: bool = False) -> tuple[float | None, str, float]:
    normalized = normalize_weights(weights)
    values: list[tuple[float, float]] = []
    statuses = []
    for dimension in DIMENSIONS:
        value = clip_score(row.get(f"{dimension}_score"))
        status = str(row.get(f"{dimension}_status", EvidenceStatus.UNAVAILABLE.value))
        statuses.append(status)
        if value is not None and evidence_allowed(status, include_estimates):
            values.append((normalized[dimension], value))
    coverage = sum(weight for weight, _ in values)
    if not values:
        return None, EvidenceStatus.UNAVAILABLE.value, 0.0
    result = sum(weight * value for weight, value in values) / coverage
    if all(status in OBSERVED_STATUSES for status in statuses):
        status = EvidenceStatus.DERIVED.value
    elif include_estimates:
        status = EvidenceStatus.ESTIMATED.value
    else:
        status = EvidenceStatus.PARTIAL.value
    return round(float(result), 1), status, round(float(coverage), 3)


def build_city_metrics(
    visits: pd.DataFrame,
    weather: pd.DataFrame,
    uhi: pd.DataFrame,
    poi: pd.DataFrame,
    gtfs: dict[str, dict[str, Any]],
    weights: dict[str, float] | None = None,
    include_estimates: bool = False,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for city, meta in HOST_CITIES.items():
        weather_city = weather[weather["city"] == city] if not weather.empty and "city" in weather else pd.DataFrame()
        event_weather = weather_city[
            (weather_city["date"].dt.month.isin([6, 7])) if not weather_city.empty and pd.api.types.is_datetime64_any_dtype(weather_city["date"]) else []
        ] if not weather_city.empty else pd.DataFrame()
        if event_weather.empty:
            event_weather = weather_city
        if not event_weather.empty:
            heat_values = [calculate_noaa_heat_index_c(float(temp), float(humidity)) for temp, humidity in zip(event_weather["avg_temp_c"], event_weather["humidity"])]
            heat_index = float(np.nanpercentile(heat_values, 90)) if heat_values else None
            avg_temp = float(event_weather["avg_temp_c"].mean())
            humidity = float(event_weather["humidity"].mean())
            heat_status = EvidenceStatus.DERIVED.value
        else:
            heat_index = avg_temp = humidity = None
            heat_status = EvidenceStatus.UNAVAILABLE.value

        uhi_city = uhi[uhi["city"] == city] if not uhi.empty and "city" in uhi else pd.DataFrame()
        uhi_value = None
        if not uhi_city.empty:
            uhi_value = uhi_city.iloc[0].get("venue_p90_uhi")
            if pd.isna(uhi_value):
                uhi_value = uhi_city.iloc[0].get("p90_uhi")
        uhi_status = EvidenceStatus.DERIVED.value if uhi_value is not None and not pd.isna(uhi_value) else EvidenceStatus.UNAVAILABLE.value

        gtfs_row = gtfs.get(city, {})
        transit_value = gtfs_row.get("gtfs_transit_score")
        transit_status = gtfs_row.get("score_status", EvidenceStatus.UNAVAILABLE.value)
        if transit_value is not None:
            transit_value = float(transit_value)

        poi_count = float(poi.loc[poi["city"] == city, "poi_count_1mi"].sum()) if not poi.empty and "city" in poi else 0.0
        access_values = []
        if not poi.empty and "city" in poi:
            all_counts = poi.groupby("city")["poi_count_1mi"].sum()
            reference = float(all_counts.quantile(0.95)) if not all_counts.empty else 0.0
            if reference > 0:
                access_values.append(min(100.0, poi_count / reference * 100.0))
        access_value = access_values[0] if access_values else None
        access_status = EvidenceStatus.DERIVED.value if access_value is not None else EvidenceStatus.UNAVAILABLE.value

        visits_city = visits[visits["city"] == city] if not visits.empty and "city" in visits else pd.DataFrame()
        average_visits = float(visits_city["daily_visits"].mean()) if not visits_city.empty else None
        peak_visits = float(visits_city["daily_visits"].max()) if not visits_city.empty else None
        peak_visitors = int(float(meta["capacity"]) * 0.95) if meta.get("capacity") else None

        row: dict[str, Any] = {
            "city": city,
            "venue": meta["venue"],
            "state": meta["state"],
            "lat": meta["lat"],
            "lon": meta["lon"],
            "capacity": meta["capacity"],
            "games": meta["games"],
            "transit_score": transit_value,
            "transit_status": transit_status,
            "heat_score": heat_safety_score(heat_index),
            "heat_status": heat_status,
            "uhi_score": uhi_safety_score(float(uhi_value)) if uhi_value is not None and not pd.isna(uhi_value) else None,
            "uhi_status": uhi_status,
            "access_score": access_value,
            "access_status": access_status,
            "heat_index_c_p90": heat_index,
            "avg_temp_c": avg_temp,
            "humidity": humidity,
            "avg_uhi_c": float(uhi_value) if uhi_value is not None and not pd.isna(uhi_value) else None,
            "avg_daily_visits": average_visits,
            "peak_daily_visits": peak_visits,
            "peak_visitors": peak_visitors,
            "transit_stops_0_5mi": gtfs_row.get("stops_0_5mi"),
            "nearest_stop_mi": gtfs_row.get("nearest_stop_mi"),
            "route_count": gtfs_row.get("route_count"),
            "feed_status": gtfs_row.get("feed_status", "unavailable"),
        }
        row["first_last_mile_gap"] = None if transit_value is None or heat_index is None else round(max(0.0, (100 - transit_value) * (1 + max(0.0, heat_index - 25) / 35)), 1)
        row["transit_status"] = transit_status
        row["heat_status"] = heat_status
        row["uhi_status"] = uhi_status
        row["access_status"] = access_status
        row["score"], row["score_status"], row["data_coverage"] = composite_score(row, weights, include_estimates)
        row["evidence_json"] = json.dumps({
            "transit": {"status": transit_status, "source": "pinned GTFS venue snapshot"},
            "heat": {"status": heat_status, "source": "daily-weather-rice event-window p90"},
            "uhi": {"status": uhi_status, "source": "urban-heat-index-rice venue buffer"},
            "access": {"status": access_status, "source": "core-poi-geometry-rice venue buffer"},
        })
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["score_status", "score"], ascending=[True, False], na_position="last").reset_index(drop=True)


def intervention_result(row: pd.Series | dict[str, Any], config: ScenarioConfig) -> ScenarioResult:
    row = row.to_dict() if isinstance(row, pd.Series) else row
    baseline_transit = float(row.get("transit_score") or 0.0)
    baseline_demand = int(row.get("peak_visitors") or row.get("capacity") or 0)
    added_shuttle_capacity = int(config.shuttle_buses_per_hour * config.shuttle_hours * config.bus_capacity * config.uptake_rate)
    added_park_ride_capacity = int(config.park_ride_spaces * config.uptake_rate)
    added_bike_capacity = int(config.bike_stations * 12 * config.uptake_rate)
    total_added = added_shuttle_capacity + added_park_ride_capacity + added_bike_capacity
    shifted = min(baseline_demand, max(0, total_added))
    residual = max(0, baseline_demand - shifted)
    vehicle_trips_avoided = shifted / max(config.average_vehicle_occupancy, 1.0)
    vehicle_km = vehicle_trips_avoided * config.average_trip_km_round_trip
    emissions = vehicle_km * config.vehicle_emissions_kg_per_km
    capital = config.bike_stations * 45_000 + config.park_ride_spaces * 2_800 + (config.pedestrian_upgrade_pct / 10) * 800_000
    operating = config.shuttle_buses_per_hour * config.shuttle_hours * 180
    return ScenarioResult(
        config=config,
        transit_capacity_added=total_added,
        potential_mode_shift=shifted,
        residual_vehicle_trips=residual,
        vehicle_km_avoided=round(vehicle_km, 1),
        emissions_avoided_kg=round(emissions, 1),
        capital_cost=round(capital, 2),
        operating_cost_per_match=round(operating, 2),
        assumptions=(
            "Potential mode shift is capped by modeled peak visitors.",
            "This is a traffic-pressure proxy, not measured roadway congestion.",
            "Vehicle occupancy, distance, bus capacity, uptake, and unit costs are editable assumptions.",
        ),
    )
