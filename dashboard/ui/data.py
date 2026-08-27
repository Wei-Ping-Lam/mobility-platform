"""Dashboard artifact loading with explicit legacy-cache compatibility."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from dashboard.mobility_platform.artifacts import read_manifest, read_parquet
from dashboard.mobility_platform.config import ProjectPaths
from dashboard.mobility_platform.mappings import MARKET_TO_CITY, cities_for_market
from dashboard.viz.state_centroids import STATE_CENTROIDS


def _empty(name: str) -> pd.DataFrame:
    columns = {
        "visits": ["city", "date", "daily_visits"],
        "visits_category": ["city", "date", "category", "daily_visits"],
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
            copy["source_dataset"] = "store-visits-rice"
            copy["source_market"] = str(market)
            copy["evidence_status"] = "partial" if len(cities_for_market(str(market))) > 1 else "derived"
            rows.append(copy[["city", "date", "daily_visits", "source_dataset", "source_market", "evidence_status"]])
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
            rows.append(
                {
                    "city": city,
                    "avg_uhi": row.get("avg_uhi"),
                    "p90_uhi": row.get("p90_uhi"),
                    "max_uhi": row.get("max_uhi"),
                    "venue_avg_uhi": None,
                    "venue_p90_uhi": None,
                    "venue_points": 0,
                    "source_dataset": "urban-heat-index-rice",
                    "evidence_status": "partial",
                }
            )
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
    candidates = [
        paths.artifact_root / "gtfs_transit_scores.json",
        paths.repo_root / "data" / "gtfs_transit_scores.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cities = payload.get("cities", payload)
            if not isinstance(cities, dict):
                return {}
            normalized = {}
            for city, raw in cities.items():
                value = dict(raw) if isinstance(raw, dict) else {}
                if "score_status" not in value:
                    value["legacy_gtfs_transit_score"] = value.get("gtfs_transit_score")
                    value["gtfs_transit_score"] = None
                    value["score_status"] = "unavailable"
                    value["feed_status"] = "unavailable"
                    value["legacy_reason"] = (
                        "Legacy cache has no pinned fetch timestamp, hash, calendar validity, or evidence status."
                    )
                normalized[str(city)] = value
            return normalized
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, json.JSONDecodeError):
        return None


def _load_public_supplements(paths: ProjectPaths) -> dict[str, Any]:
    """Load explicit offline snapshots without scanning directories or fetching data."""

    roots = (paths.artifact_root, paths.repo_root / "data" / "snapshots")
    bundle: dict[str, Any] = {}
    for root in roots:
        payload = _load_json(root / "transportation_bundle.json")
        if isinstance(payload, dict):
            bundle.update(payload)
            break
    files = {
        "match_events": "fifa_schedule.json",
        "movement_scenarios": "movement_scenarios.json",
        "access_gaps": "access_gaps.json",
        "intervention_outcomes": "intervention_outcomes.json",
        "investment_recommendations": "investment_recommendations.json",
        "source_references": "source_references.json",
        "factor_registry": "factor_registry.json",
        "network_coverage": "network_coverage.json",
        "map_layers": "map_layers.json",
        "movement_validation": "movement_validation.json",
        "mrs_sensitivity": "mrs_sensitivity.json",
    }
    for key, filename in files.items():
        if key in bundle:
            continue
        for root in roots:
            payload = _load_json(root / filename)
            if payload is not None:
                bundle[key] = payload
                break
    snapshot_root = paths.repo_root / "data" / "snapshots"
    schedule = _load_json(snapshot_root / "fifa" / "fifa_2026_us_schedule.json")
    factors = _load_json(snapshot_root / "factors" / "planning_factors.json")
    walking = _load_json(snapshot_root / "osm" / "walking_networks.json")
    parking = _load_json(snapshot_root / "osm" / "parking_density.json")
    gtfs = _load_json(snapshot_root / "gtfs" / "gtfs_venue_access.json")
    operations = _load_json(snapshot_root / "operations" / "world_cup_2026_operations.json")
    traffic_management = _load_json(snapshot_root / "operations" / "world_cup_2026_traffic_management.json")
    strategy_benchmarks = _load_json(
        snapshot_root / "operations" / "world_cup_2026_strategy_benchmarks.json"
    )
    environment = _load_json(snapshot_root / "environment" / "venue_environment.json")
    if isinstance(schedule, dict):
        bundle.setdefault("match_events", schedule.get("events", []))
        bundle.setdefault("source_references", [schedule.get("source", {})])
    if isinstance(factors, dict):
        bundle["factor_snapshot"] = factors
        bundle.setdefault(
            "factor_registry",
            [{"factor": name, **value} for name, value in factors.get("factors", {}).items()],
        )
        bundle.setdefault("source_references", []).extend(factors.get("sources", {}).values())
    if isinstance(walking, dict):
        bundle["walking_networks"] = walking.get("cities", {})
        bundle.setdefault("network_coverage", list(walking.get("cities", {}).values()))
        bundle.setdefault("source_references", []).append(walking.get("source", {}))
    if isinstance(parking, dict):
        bundle["parking_density"] = parking.get("cities", {})
        bundle.setdefault("source_references", []).append(parking.get("source", {}))
    if isinstance(gtfs, dict):
        bundle["gtfs_snapshot"] = gtfs.get("cities", {})
        for city, city_gtfs in gtfs.get("cities", {}).items():
            if not isinstance(city_gtfs, dict):
                continue
            layers = bundle.setdefault("map_layers", {}).setdefault(city, {})
            layers["gtfs"] = city_gtfs.get("stop_points_2mi", [])
            layers["gtfs_routes"] = city_gtfs.get("route_shapes", [])
    if isinstance(operations, dict):
        bundle["operational_snapshot"] = operations
        bundle["operational_metrics"] = operations.get("metrics", [])
        bundle["operational_event_records"] = operations.get("event_records", [])
        bundle["operational_coverage"] = operations.get("city_coverage", {})
        bundle.setdefault("source_references", []).extend(
            {"source_id": source_id, **source}
            for source_id, source in operations.get("sources", {}).items()
            if isinstance(source, dict)
        )
    if isinstance(traffic_management, dict):
        bundle["traffic_management_snapshot"] = traffic_management
        bundle["published_traffic_plans"] = traffic_management.get("plans", {})
        bundle["traffic_management_coverage"] = traffic_management.get("city_coverage", {})
        bundle.setdefault("source_references", []).extend(
            {"source_id": source_id, **source}
            for source_id, source in traffic_management.get("sources", {}).items()
            if isinstance(source, dict)
        )
    if isinstance(strategy_benchmarks, dict):
        from dashboard.pipeline.public.strategy_benchmarks import validate_snapshot

        validate_snapshot(strategy_benchmarks)
        bundle["strategy_benchmark_snapshot"] = strategy_benchmarks
        bundle["strategy_benchmarks"] = strategy_benchmarks.get("benchmarks", {})
    if isinstance(environment, dict):
        bundle["environment_snapshot"] = environment
        bundle.setdefault("source_references", []).extend(
            {"source_id": source_id, **source}
            for source_id, source in environment.get("sources", {}).items()
            if isinstance(source, dict)
        )
    return bundle


def _apply_environment_supplements(
    weather: pd.DataFrame,
    uhi: pd.DataFrame,
    environment: object,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace only evidence rows named by a validated offline supplement."""

    if not isinstance(environment, dict):
        return weather, uhi
    policy = environment.get("replacement_policy", {})
    weather_rows = environment.get("weather_daily", [])
    weather_cities = set(policy.get("weather", []))
    if isinstance(weather_rows, list) and weather_rows and weather_cities:
        supplement = pd.DataFrame(weather_rows)
        supplement["date"] = pd.to_datetime(supplement["date"], errors="coerce")
        retained = weather[~weather["city"].isin(weather_cities)].copy() if "city" in weather else weather.copy()
        weather = pd.concat([retained, supplement], ignore_index=True, sort=False)
    uhi_rows = environment.get("uhi_city", [])
    uhi_cities = set(policy.get("uhi", []))
    if isinstance(uhi_rows, list) and uhi_rows and uhi_cities:
        supplement = pd.DataFrame(uhi_rows)
        retained = uhi[~uhi["city"].isin(uhi_cities)].copy() if "city" in uhi else uhi.copy()
        uhi = pd.concat([retained, supplement], ignore_index=True, sort=False)
    return weather, uhi


def _load_rice_spatial(paths: ProjectPaths) -> dict[str, Any]:
    names = {
        "uhi_points": "rice_spatial_uhi_grid.parquet",
        "poi_points": "rice_spatial_poi_points.parquet",
        "origin_flows": "rice_spatial_origin_flows.parquet",
        "movement_context": "rice_spatial_movement_context.parquet",
        "venue_corridors": "venue_corridor_summary.parquet",
    }
    frames = {key: read_parquet(paths, filename) for key, filename in names.items()}
    map_layers: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for city in sorted(set(frames["poi_points"].get("city", pd.Series(dtype=str)).dropna())):
        city_uhi = frames["uhi_points"][frames["uhi_points"]["city"] == city].copy()
        city_poi = frames["poi_points"][frames["poi_points"]["city"] == city].copy()
        city_origins = frames["origin_flows"][frames["origin_flows"]["city"] == city].copy()
        if not city_uhi.empty:
            city_uhi = city_uhi.rename(columns={"grid_lat": "lat", "grid_lon": "lon"})
            source_total = len(city_uhi)
            city_uhi["lat_bin"] = pd.to_numeric(city_uhi["lat"], errors="coerce").round(2)
            city_uhi["lon_bin"] = pd.to_numeric(city_uhi["lon"], errors="coerce").round(2)
            city_uhi = (
                city_uhi.groupby(["lat_bin", "lon_bin"], dropna=True)
                .agg(avg_uhi=("avg_uhi", "mean"), point_count=("point_count", "sum"))
                .reset_index()
                .rename(columns={"lat_bin": "lat", "lon_bin": "lon"})
                .sort_values(["point_count", "lat", "lon"], ascending=[False, True, True])
                .head(500)
            )
            city_uhi["name"] = city_uhi["avg_uhi"].map(lambda value: f"Rice UHI {value:.1f}")
            city_uhi["source_total_records"] = source_total
        if not city_poi.empty:
            city_poi = city_poi.rename(columns={"point_lat": "lat", "point_lon": "lon"})
            source_total = len(city_poi)
            city_poi["lat_bin"] = pd.to_numeric(city_poi["lat"], errors="coerce").round(2)
            city_poi["lon_bin"] = pd.to_numeric(city_poi["lon"], errors="coerce").round(2)
            grouped = (
                city_poi.groupby(["lat_bin", "lon_bin", "category"], dropna=True)
                .size()
                .rename("category_count")
                .reset_index()
            )
            city_poi = (
                grouped.sort_values(
                    ["lat_bin", "lon_bin", "category_count", "category"], ascending=[True, True, False, True]
                )
                .drop_duplicates(["lat_bin", "lon_bin"])
                .rename(columns={"lat_bin": "lat", "lon_bin": "lon", "category": "top_category"})
                .sort_values(["category_count", "lat", "lon"], ascending=[False, True, True])
                .head(500)
            )
            city_poi["name"] = city_poi.apply(
                lambda row: f"{row['top_category']} ({int(row['category_count'])})", axis=1
            )
            city_poi["source_total_records"] = source_total
        if not city_origins.empty:
            city_origins = city_origins.rename(columns={"home_state": "name"})
            source_total = len(city_origins)
            origin_rows = []
            for row in city_origins.sort_values(["state_rank", "name"], kind="stable").head(30).to_dict("records"):
                centroid = STATE_CENTROIDS.get(str(row.get("name")))
                if not centroid:
                    continue
                row["lat"], row["lon"] = centroid
                row["coordinates"] = [
                    [float(centroid[1]), float(centroid[0])],
                    [float(row["venue_lon"]), float(row["venue_lat"])],
                ]
                row["name"] = f"{row['name']} spend-panel customers"
                row["source_total_records"] = source_total
                origin_rows.append(row)
            city_origins = pd.DataFrame(origin_rows)
        map_layers[city] = {
            "uhi": city_uhi.to_dict("records"),
            "poi": city_poi.to_dict("records"),
            "origin": city_origins.to_dict("records"),
        }
    frames["map_layers"] = map_layers
    return frames


def load_artifacts(paths: ProjectPaths) -> dict[str, Any]:
    visits = read_parquet(paths, "visits_daily.parquet")
    if visits.empty:
        visits = _legacy_visits(paths)
    visits_category = read_parquet(paths, "visits_daily_category.parquet")
    weather = read_parquet(paths, "weather_city_daily.parquet")
    uhi = read_parquet(paths, "uhi_city_summary.parquet")
    if uhi.empty:
        uhi = _legacy_uhi(paths)
    poi = read_parquet(paths, "poi_venue_summary.parquet")
    origins = read_parquet(paths, "spend_origins.parquet")
    if origins.empty or not {"city", "home_state", "count", "raw_total_spend"}.issubset(origins.columns):
        origins = _legacy_origins(paths)
    brand_spend = read_parquet(paths, "brand_spend_city_daily.parquet")
    supplements = _load_public_supplements(paths)
    rice_weather = weather.copy()
    rice_uhi = uhi.copy()
    weather, uhi = _apply_environment_supplements(weather, uhi, supplements.get("environment_snapshot"))
    pinned_gtfs = supplements.get("gtfs_snapshot")
    artifacts = {
        "manifest": read_manifest(paths),
        "visits": visits,
        "visits_category": visits_category,
        "weather": weather,
        "uhi": uhi,
        "rice_weather": rice_weather,
        "rice_uhi": rice_uhi,
        "poi": poi,
        "origins": origins,
        "brand_spend": brand_spend,
        "gtfs": pinned_gtfs if isinstance(pinned_gtfs, dict) else load_gtfs(paths),
        "legacy_mode": not (paths.artifact_root / "manifest.json").exists(),
    }
    artifacts.update(supplements)
    spatial = _load_rice_spatial(paths)
    for city, city_layers in spatial.pop("map_layers", {}).items():
        artifacts.setdefault("map_layers", {}).setdefault(city, {}).update(city_layers)
    artifacts.update(spatial)
    for city, network in artifacts.get("walking_networks", {}).items():
        walk_rows = []
        route_geometry = network.get("route_geometry")
        if isinstance(route_geometry, dict):
            route_geometry = route_geometry.get("coordinates")
        if isinstance(route_geometry, list) and route_geometry:
            walk_rows.append(
                {
                    "coordinates": route_geometry,
                    "name": "Network path to event-relevant stop",
                    "status": network.get("status", "partial"),
                }
            )
        for isochrone in network.get("isochrones", []):
            geometry = isochrone.get("geometry", {})
            coordinates = geometry.get("coordinates", [])
            if coordinates:
                walk_rows.append({"coordinates": coordinates[0], "minutes": isochrone.get("minutes")})
        artifacts.setdefault("map_layers", {}).setdefault(city, {})["walk"] = walk_rows
    return artifacts
