"""Dashboard artifact loading with explicit legacy-cache compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.mobility_platform.artifacts import read_json, read_manifest, read_parquet
from dashboard.mobility_platform.config import ProjectPaths
from dashboard.mobility_platform.mappings import MARKET_TO_CITY, cities_for_market


def _empty(name: str) -> pd.DataFrame:
    columns = {
        "visits": ["city", "date", "daily_visits"],
        "weather": ["city", "date", "avg_temp_c", "max_temp_c", "min_temp_c", "humidity"],
        "uhi": ["city", "avg_uhi", "p90_uhi", "max_uhi", "venue_avg_uhi", "venue_p90_uhi", "venue_points"],
        "poi": ["city", "category", "poi_count_1mi"],
        "origins": ["city", "home_state", "count", "raw_total_spend"],
        "brand_spend": ["city", "date", "spend", "transactions"],
    }
    return pd.DataFrame(columns=columns[name])


def _legacy_visits(paths: ProjectPaths) -> pd.DataFrame:
    path = paths.artifact_root / "store_visits_agg.parquet"
    if not path.exists():
        return _empty("visits")
    frame = pd.read_parquet(path)
    if frame.empty:
        return _empty("visits")
    rows = []
    for market, group in frame.groupby("market"):
        for city in cities_for_market(str(market)):
            copy = group.copy()
            copy["city"] = city
            copy["daily_visits"] = copy["daily_visits"] / max(1, len(cities_for_market(str(market))))
            rows.append(copy[["city", "date", "daily_visits"]])
    return pd.concat(rows, ignore_index=True) if rows else _empty("visits")


def _legacy_uhi(paths: ProjectPaths) -> pd.DataFrame:
    path = paths.artifact_root / "uhi_summary.parquet"
    if not path.exists():
        return _empty("uhi")
    frame = pd.read_parquet(path).rename(columns={"MARKET": "market"})
    rows = []
    for market, group in frame.groupby("market"):
        city = MARKET_TO_CITY.get(str(market))
        if city:
            row = group.iloc[0]
            rows.append({"city": city, "avg_uhi": row.get("avg_uhi"), "p90_uhi": row.get("p90_uhi"), "max_uhi": row.get("max_uhi"), "venue_avg_uhi": None, "venue_p90_uhi": None, "venue_points": 0})
    return pd.DataFrame(rows) if rows else _empty("uhi")


def _legacy_origins(paths: ProjectPaths) -> pd.DataFrame:
    path = paths.artifact_root / "spend_origins.parquet"
    if not path.exists():
        return _empty("origins")
    frame = pd.read_parquet(path)
    if "market" not in frame or "home_state" not in frame:
        return _empty("origins")
    frame["city"] = frame["market"].map(MARKET_TO_CITY)
    return frame.dropna(subset=["city"])[["city", "home_state", "count"]].assign(raw_total_spend=None)


def load_gtfs(paths: ProjectPaths) -> dict[str, dict[str, Any]]:
    candidates = [paths.artifact_root / "gtfs_transit_scores.json", paths.repo_root / "data" / "gtfs_transit_scores.json"]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cities = payload.get("cities", payload)
            return cities if isinstance(cities, dict) else {}
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def load_artifacts(paths: ProjectPaths) -> dict[str, Any]:
    visits = read_parquet(paths, "visits_daily.parquet")
    if visits.empty:
        visits = _legacy_visits(paths)
    weather = read_parquet(paths, "weather_city_daily.parquet")
    uhi = read_parquet(paths, "uhi_city_summary.parquet")
    if uhi.empty:
        uhi = _legacy_uhi(paths)
    poi = read_parquet(paths, "poi_venue_summary.parquet")
    origins = read_parquet(paths, "spend_origins.parquet")
    if origins.empty:
        origins = _legacy_origins(paths)
    brand_spend = read_parquet(paths, "brand_spend_city_daily.parquet")
    return {
        "manifest": read_manifest(paths),
        "visits": visits,
        "weather": weather,
        "uhi": uhi,
        "poi": poi,
        "origins": origins,
        "brand_spend": brand_spend,
        "gtfs": load_gtfs(paths),
        "legacy_mode": not (paths.artifact_root / "manifest.json").exists(),
    }
