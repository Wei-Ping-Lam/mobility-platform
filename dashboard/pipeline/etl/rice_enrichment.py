"""Build deterministic, compact Rice spatial and movement enrichments offline.

This command is the only path that scans raw Rice spatial/origin files. The
dashboard and downstream models consume the generated cache artifacts only.
Commercial visits describe general city activity and customer origins describe
the supplied spend panel; neither is event-demand evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from dashboard.mobility_platform.config import ProjectPaths, project_paths, require_data_root
from dashboard.mobility_platform.mappings import HOST_CITIES, cities_for_market
from dashboard.pipeline.etl.build import _customer_origin_items, _files, _haversine_miles, _read_chunks, _sha256
from dashboard.pipeline.schemas.rice_enrichment import (
    ARTIFACT_SCHEMAS,
    SOURCE_COLLECTION,
    SPATIAL_LIMITATION,
    validate_artifact,
)

SCHEMA_VERSION = "0.3.0"
DISTANCE_BANDS = (("0-1 mi", 0.0, 1.0), ("1-2 mi", 1.0, 2.0), ("2-5 mi", 2.0, 5.0))
WEEKDAY_NAMES = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}


def _dataset_sha256(files: Iterable[Path]) -> str:
    """Hash ordered file names and contents into one portable dataset digest."""

    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _allocation_records(frame: pd.DataFrame) -> pd.DataFrame:
    records: list[pd.DataFrame] = []
    for market, group in frame.groupby("MARKET", dropna=False, sort=True):
        cities = cities_for_market(str(market))
        for city in cities:
            allocated = group.copy()
            allocated["city"] = city
            allocated["source_market"] = str(market)
            allocated["allocation_factor"] = 1.0 / len(cities)
            allocated["allocation_method"] = "equal_split_combined_market" if len(cities) > 1 else "none"
            allocated["evidence_status"] = "partial" if len(cities) > 1 else "derived"
            records.append(allocated)
    return pd.concat(records, ignore_index=True) if records else pd.DataFrame()


def _distance_band(distance: pd.Series) -> pd.Series:
    values = pd.to_numeric(distance, errors="coerce")
    return pd.Series(
        np.select(
            [values <= 1.0, (values > 1.0) & (values <= 2.0), (values > 2.0) & (values <= 5.0)],
            ["0-1 mi", "1-2 mi", "2-5 mi"],
            default=None,
        ),
        index=distance.index,
        dtype="object",
    )


def _attach_provenance(
    frame: pd.DataFrame,
    *,
    dataset: str,
    source_sha256: str,
    spatial: bool = False,
    claim_scope: str | None = None,
) -> pd.DataFrame:
    frame = frame.copy()
    frame["source_collection"] = SOURCE_COLLECTION
    frame["source_dataset"] = dataset
    frame["source_sha256"] = source_sha256
    if spatial:
        frame["spatial_limitations"] = SPATIAL_LIMITATION
    if claim_scope:
        frame["claim_scope"] = claim_scope
    return frame


def build_uhi_grid(frame: pd.DataFrame, source_sha256: str) -> pd.DataFrame:
    """Aggregate supplied UHI observations to an approximately 250 m grid."""

    raw = frame.rename(columns={"LATITUDE": "latitude", "LONGITUDE": "longitude", "UHI": "uhi"}).copy()
    for column in ("latitude", "longitude", "uhi"):
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    raw = raw.dropna(subset=["MARKET", "latitude", "longitude", "uhi"])
    expanded = _allocation_records(raw)
    rows: list[pd.DataFrame] = []
    for city, metadata in HOST_CITIES.items():
        points = expanded[expanded["city"] == city].copy()
        if points.empty:
            continue
        points["distance_mi"] = _haversine_miles(
            float(metadata["lat"]),
            float(metadata["lon"]),
            points["latitude"].to_numpy(),
            points["longitude"].to_numpy(),
        )
        points = points[points["distance_mi"] <= 5.0].copy()
        if points.empty:
            continue
        points["grid_lat"] = (points["latitude"] / 0.0025).round() * 0.0025
        points["grid_lon"] = (points["longitude"] / 0.0025).round() * 0.0025
        grouped = points.groupby(
            [
                "city",
                "source_market",
                "evidence_status",
                "allocation_method",
                "allocation_factor",
                "grid_lat",
                "grid_lon",
            ],
            as_index=False,
            sort=True,
        ).agg(
            avg_uhi=("uhi", "mean"),
            p90_uhi=("uhi", lambda values: float(np.percentile(values, 90))),
            max_uhi=("uhi", "max"),
            point_count=("allocation_factor", "sum"),
        )
        grouped["venue"] = str(metadata["venue"])
        grouped["venue_lat"] = float(metadata["lat"])
        grouped["venue_lon"] = float(metadata["lon"])
        grouped["distance_mi"] = _haversine_miles(
            float(metadata["lat"]),
            float(metadata["lon"]),
            grouped["grid_lat"].to_numpy(),
            grouped["grid_lon"].to_numpy(),
        )
        grouped["distance_band"] = _distance_band(grouped["distance_mi"])
        rows.append(grouped)
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    covered_cities = set(result["city"]) if not result.empty else set()
    missing_rows = []
    for city in sorted(set(HOST_CITIES).difference(covered_cities)):
        metadata = HOST_CITIES[city]
        missing_rows.append(
            {
                "city": city,
                "source_market": str(metadata["market"]),
                "evidence_status": "unavailable",
                "allocation_method": "none",
                "allocation_factor": 1.0,
                "grid_lat": float(metadata["lat"]),
                "grid_lon": float(metadata["lon"]),
                "avg_uhi": None,
                "p90_uhi": None,
                "max_uhi": None,
                "point_count": 0.0,
                "venue": str(metadata["venue"]),
                "venue_lat": float(metadata["lat"]),
                "venue_lon": float(metadata["lon"]),
                "distance_mi": 0.0,
                "distance_band": "0-1 mi",
            }
        )
    if missing_rows:
        result = pd.concat([result, pd.DataFrame(missing_rows)], ignore_index=True)
    result = _attach_provenance(
        result,
        dataset="urban-heat-index-rice",
        source_sha256=source_sha256,
        spatial=True,
    )
    return result


def build_poi_points(frame: pd.DataFrame, source_sha256: str) -> pd.DataFrame:
    """Select and deduplicate supplied POI centroids within five venue miles."""

    raw = frame.rename(
        columns={"LATITUDE": "point_lat", "LONGITUDE": "point_lon", "TOP_CATEGORY": "category", "PLACEKEY": "placekey"}
    ).copy()
    raw["point_lat"] = pd.to_numeric(raw["point_lat"], errors="coerce")
    raw["point_lon"] = pd.to_numeric(raw["point_lon"], errors="coerce")
    raw["category"] = raw["category"].fillna("Other").astype(str)
    raw = raw.dropna(subset=["MARKET", "point_lat", "point_lon", "placekey"])
    expanded = _allocation_records(raw)
    rows: list[pd.DataFrame] = []
    for city, metadata in HOST_CITIES.items():
        points = expanded[expanded["city"] == city].copy()
        if points.empty:
            continue
        points["distance_mi"] = _haversine_miles(
            float(metadata["lat"]),
            float(metadata["lon"]),
            points["point_lat"].to_numpy(),
            points["point_lon"].to_numpy(),
        )
        points = points[points["distance_mi"] <= 5.0].copy()
        points["distance_band"] = _distance_band(points["distance_mi"])
        points["venue"] = str(metadata["venue"])
        points["venue_lat"] = float(metadata["lat"])
        points["venue_lon"] = float(metadata["lon"])
        rows.append(points)
    result = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not result.empty:
        result = result.sort_values(["city", "placekey", "source_market", "category"]).drop_duplicates(
            ["city", "placekey", "source_market"], keep="first"
        )
    result = _attach_provenance(
        result,
        dataset="core-poi-geometry-rice",
        source_sha256=source_sha256,
        spatial=True,
    )
    return result


def build_origin_flows(frame: pd.DataFrame, source_sha256: str) -> pd.DataFrame:
    """Aggregate supplied spend-panel customer-home cities to state flows."""

    expanded = _allocation_records(frame.dropna(subset=["MARKET", "CUSTOMER_HOME_CITY"]))
    rows: list[dict[str, object]] = []
    for record in expanded.itertuples(index=False):
        for location, raw_count in _customer_origin_items(record.CUSTOMER_HOME_CITY):
            try:
                count = float(raw_count) * float(record.allocation_factor)
            except (TypeError, ValueError):
                continue
            state = location.rsplit(", ", 1)[-1].strip() if ", " in location else "Unknown"
            rows.append(
                {
                    "city": record.city,
                    "home_state": state or "Unknown",
                    "customer_count": count,
                    "source_market": record.source_market,
                    "evidence_status": record.evidence_status,
                    "allocation_method": record.allocation_method,
                }
            )
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.groupby(
            ["city", "home_state", "source_market", "evidence_status", "allocation_method"], as_index=False, sort=True
        )["customer_count"].sum()
        result["allocation_factor"] = np.where(result["evidence_status"] == "partial", 0.5, 1.0)
        city_totals = result.groupby("city")["customer_count"].transform("sum")
        result["city_customer_share"] = np.where(city_totals > 0, result["customer_count"] / city_totals, 0.0)
        state_totals = result.groupby(["city", "home_state"], as_index=False)["customer_count"].sum()
        state_totals["state_rank"] = state_totals.groupby("city")["customer_count"].rank(
            method="dense", ascending=False
        ).astype(int)
        result = result.merge(state_totals[["city", "home_state", "state_rank"]], on=["city", "home_state"], how="left")
        result["venue_lat"] = result["city"].map(lambda city: float(HOST_CITIES[city]["lat"]))
        result["venue_lon"] = result["city"].map(lambda city: float(HOST_CITIES[city]["lon"]))
    result = _attach_provenance(
        result,
        dataset="spend-patterns-rice",
        source_sha256=source_sha256,
        claim_scope="spend_panel_customer_origin_context",
    )
    return result


def build_movement_context(frame: pd.DataFrame, source_sha256: str) -> pd.DataFrame:
    """Create month/weekday/category context from cached commercial visits."""

    visits = frame.copy()
    visits["date"] = pd.to_datetime(visits["date"], errors="coerce")
    visits["daily_visits"] = pd.to_numeric(visits["daily_visits"], errors="coerce")
    visits = visits.dropna(subset=["city", "date", "category", "daily_visits"])
    visits["month"] = visits["date"].dt.month.astype(int)
    visits["weekday"] = visits["date"].dt.weekday.astype(int)
    group_columns = ["city", "month", "weekday", "category", "source_market", "evidence_status"]
    result = visits.groupby(group_columns, as_index=False, sort=True).agg(
        mean_daily_visits=("daily_visits", "mean"),
        p10_daily_visits=("daily_visits", lambda values: float(np.percentile(values, 10))),
        p90_daily_visits=("daily_visits", lambda values: float(np.percentile(values, 90))),
        observation_days=("date", "nunique"),
    )
    result["weekday_name"] = result["weekday"].map(WEEKDAY_NAMES)
    result["allocation_method"] = np.where(
        result["evidence_status"] == "partial", "equal_split_combined_market", "none"
    )
    result["allocation_factor"] = np.where(result["evidence_status"] == "partial", 0.5, 1.0)
    result["venue_lat"] = result["city"].map(lambda city: float(HOST_CITIES[city]["lat"]))
    result["venue_lon"] = result["city"].map(lambda city: float(HOST_CITIES[city]["lon"]))
    result = _attach_provenance(
        result,
        dataset="store-visits-rice",
        source_sha256=source_sha256,
        claim_scope="commercial_activity_context",
    )
    return result


def _worst_status(values: Iterable[object]) -> str:
    statuses = {str(value) for value in values}
    if "unavailable" in statuses:
        return "unavailable"
    if "partial" in statuses:
        return "partial"
    return "derived"


def _weighted_quantile(values: pd.Series, weights: pd.Series, quantile: float) -> float | None:
    valid = pd.DataFrame({"value": pd.to_numeric(values, errors="coerce"), "weight": pd.to_numeric(weights, errors="coerce")})
    valid = valid.dropna().query("weight > 0").sort_values("value")
    if valid.empty:
        return None
    cutoff = float(valid["weight"].sum()) * quantile
    return float(valid.loc[valid["weight"].cumsum() >= cutoff, "value"].iloc[0])


def build_corridor_summary(
    uhi_grid: pd.DataFrame,
    poi_points: pd.DataFrame,
    origin_flows: pd.DataFrame,
    movement_context: pd.DataFrame,
) -> pd.DataFrame:
    """Build one integration-ready record per city and venue-distance band."""

    rows: list[dict[str, object]] = []
    for city, metadata in sorted(HOST_CITIES.items()):
        city_origins = origin_flows[origin_flows["city"] == city]
        origin_totals = city_origins.groupby("home_state")["customer_count"].sum().sort_values(ascending=False)
        top_states = " | ".join(str(value) for value in origin_totals.head(5).index)
        city_movement = movement_context[movement_context["city"] == city]
        month_totals = city_movement.groupby("month")["mean_daily_visits"].sum()
        weekday_totals = city_movement.groupby("weekday_name")["mean_daily_visits"].sum()
        source_markets = sorted(
            set(uhi_grid.loc[uhi_grid["city"] == city, "source_market"])
            | set(poi_points.loc[poi_points["city"] == city, "source_market"])
            | set(city_origins.get("source_market", pd.Series(dtype=str)))
            | set(city_movement.get("source_market", pd.Series(dtype=str)))
        )
        statuses = list(city_origins.get("evidence_status", [])) + list(city_movement.get("evidence_status", []))
        allocation = "equal_split_combined_market" if "partial" in statuses else "none"
        allocation_factor = 0.5 if allocation == "equal_split_combined_market" else 1.0
        source_hashes = [
            ("urban-heat-index-rice", uhi_grid.loc[uhi_grid["city"] == city, "source_sha256"]),
            ("core-poi-geometry-rice", poi_points.loc[poi_points["city"] == city, "source_sha256"]),
            ("spend-patterns-rice", city_origins.get("source_sha256", pd.Series(dtype=str))),
            ("store-visits-rice", city_movement.get("source_sha256", pd.Series(dtype=str))),
        ]
        labeled_hashes = [
            f"{dataset}={sorted(set(values.dropna().astype(str)))[0]}"
            for dataset, values in source_hashes
            if not values.empty
        ]
        for band, minimum, maximum in DISTANCE_BANDS:
            heat = uhi_grid[(uhi_grid["city"] == city) & (uhi_grid["distance_band"] == band)]
            pois = poi_points[(poi_points["city"] == city) & (poi_points["distance_band"] == band)]
            available_heat = heat[heat["evidence_status"] != "unavailable"]
            weighted_count = float(available_heat["point_count"].sum()) if not available_heat.empty else 0.0
            avg_uhi = (
                float(np.average(available_heat["avg_uhi"], weights=available_heat["point_count"]))
                if weighted_count
                else None
            )
            p90_uhi = _weighted_quantile(available_heat["avg_uhi"], available_heat["point_count"], 0.9)
            category_counts = pois.groupby("category").size().sort_values(ascending=False)
            heat_statuses = list(available_heat.get("evidence_status", [])) if not available_heat.empty else ["unavailable"]
            band_statuses = statuses + heat_statuses + list(pois.get("evidence_status", []))
            rows.append(
                {
                    "city": city,
                    "venue": str(metadata["venue"]),
                    "venue_lat": float(metadata["lat"]),
                    "venue_lon": float(metadata["lon"]),
                    "distance_band": band,
                    "band_min_mi": minimum,
                    "band_max_mi": maximum,
                    "uhi_point_count": weighted_count,
                    "avg_uhi": avg_uhi,
                    "p90_uhi": p90_uhi,
                    "poi_count": float(pois["allocation_factor"].sum()),
                    "poi_category_count": int(pois["category"].nunique()),
                    "top_poi_categories": " | ".join(str(value) for value in category_counts.head(5).index),
                    "top_home_states": top_states,
                    "peak_commercial_month": int(month_totals.idxmax()) if not month_totals.empty else None,
                    "peak_commercial_weekday": str(weekday_totals.idxmax()) if not weekday_totals.empty else None,
                    "source_collection": SOURCE_COLLECTION,
                    "source_datasets": (
                        "core-poi-geometry-rice | spend-patterns-rice | store-visits-rice | urban-heat-index-rice"
                    ),
                    "source_markets": " | ".join(str(value) for value in source_markets),
                    "source_sha256": " | ".join(labeled_hashes),
                    "evidence_status": _worst_status(band_statuses) if band_statuses else "unavailable",
                    "allocation_method": allocation,
                    "allocation_factor": allocation_factor,
                    "spatial_limitations": SPATIAL_LIMITATION,
                    "claim_scope": "venue_area_commercial_and_environmental_context",
                }
            )
    return pd.DataFrame(rows)


def _read_raw(paths: ProjectPaths, dataset: str, columns: list[str], chunksize: int = 150_000) -> pd.DataFrame:
    chunks = [chunk for path in _files(paths, dataset) for chunk in _read_chunks(path, columns, chunksize=chunksize)]
    return pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame(columns=columns)


def _write_artifact(name: str, frame: pd.DataFrame, output_root: Path) -> tuple[Path, str]:
    schema = ARTIFACT_SCHEMAS[name]
    validate_artifact(name, frame, require_all_cities=set(HOST_CITIES))
    ordered = frame.loc[:, schema.required_columns].sort_values(list(schema.sort_columns), kind="mergesort").reset_index(drop=True)
    output_root.mkdir(parents=True, exist_ok=True)
    path = output_root / schema.filename
    ordered.to_parquet(path, index=False, compression="zstd")
    return path, _sha256(path)


def build_rice_enrichments(paths: ProjectPaths) -> dict[str, object]:
    """Run the explicit offline enrichment build and return its deterministic manifest."""

    require_data_root(paths)
    movement_path = paths.artifact_root / "visits_daily_category.parquet"
    if not movement_path.exists():
        raise FileNotFoundError("visits_daily_category.parquet is required; run the base Rice ETL first.")

    raw_files = {
        "urban-heat-index-rice": _files(paths, "urban-heat-index-rice"),
        "core-poi-geometry-rice": _files(paths, "core-poi-geometry-rice"),
        "spend-patterns-rice": _files(paths, "spend-patterns-rice"),
    }
    source_hashes = {dataset: _dataset_sha256(files) for dataset, files in raw_files.items()}
    source_hashes["store-visits-rice"] = _sha256(movement_path)

    uhi = build_uhi_grid(
        _read_raw(paths, "urban-heat-index-rice", ["MARKET", "LATITUDE", "LONGITUDE", "UHI"], 300_000),
        source_hashes["urban-heat-index-rice"],
    )
    poi = build_poi_points(
        _read_raw(paths, "core-poi-geometry-rice", ["MARKET", "LATITUDE", "LONGITUDE", "TOP_CATEGORY", "PLACEKEY"]),
        source_hashes["core-poi-geometry-rice"],
    )
    origins = build_origin_flows(
        _read_raw(paths, "spend-patterns-rice", ["MARKET", "CUSTOMER_HOME_CITY"], 100_000),
        source_hashes["spend-patterns-rice"],
    )
    movement = build_movement_context(pd.read_parquet(movement_path), source_hashes["store-visits-rice"])
    corridors = build_corridor_summary(uhi, poi, origins, movement)

    frames = {
        "uhi_grid": uhi,
        "poi_points": poi,
        "origin_flows": origins,
        "movement_context": movement,
        "corridors": corridors,
    }
    artifacts: dict[str, dict[str, object]] = {}
    for name, frame in frames.items():
        path, digest = _write_artifact(name, frame, paths.artifact_root)
        artifacts[name] = {"path": path.name, "rows": len(frame), "sha256": digest}

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source_collection": SOURCE_COLLECTION,
        "build_fingerprint": hashlib.sha256(
            json.dumps(source_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "source_hashes": dict(sorted(source_hashes.items())),
        "artifacts": artifacts,
        "limitations": [SPATIAL_LIMITATION],
    }
    manifest_path = paths.artifact_root / "rice_spatial_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, help="Path to the read-only Rice WC Hack collection.")
    parser.add_argument("--output", default=None, help="Cache output directory; defaults to dashboard/cache.")
    args = parser.parse_args()
    paths = project_paths(explicit_data_root=args.data_root)
    if args.output:
        paths = ProjectPaths(paths.repo_root, paths.data_root, Path(args.output).resolve())
    print(json.dumps(build_rice_enrichments(paths), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
