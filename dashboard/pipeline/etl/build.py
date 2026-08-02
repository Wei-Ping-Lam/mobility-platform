"""Build compact, deterministic artifacts from the supplied raw datasets.

The Streamlit application must consume these artifacts rather than scanning the
raw store-visits collection. The implementation deliberately records partial
coverage for combined source markets instead of pretending that rows can be
assigned to a specific city.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from dashboard.mobility_platform.config import ProjectPaths, project_paths, require_data_root
from dashboard.mobility_platform.contracts import CONTRACT_VERSION, DataManifest, DataQualityReport, EvidenceStatus
from dashboard.mobility_platform.mappings import (
    HOST_CITIES,
    MARKET_TO_CITY,
    PRIMARY_WEATHER_STATIONS,
    WEATHER_STATION_METADATA,
    WEATHER_STATIONS,
    cities_for_market,
)
from dashboard.mobility_platform.sources import RICE_COLLECTION
from dashboard.pipeline.schemas.validation import QualityTracker

EXPECTED_PARTITIONS = {
    "store-visits-rice": 32,
    "urban-heat-index-rice": 32,
    "daily-weather-rice": 32,
    "core-poi-geometry-rice": 32,
    "spend-patterns-rice": 32,
    "daily-spend-brand-and-state-rice": 32,
}
PARTITION_GRID = {
    f"{dataset}_{row}_{column}_0.csv.gz"
    for dataset in EXPECTED_PARTITIONS
    for row in range(4)
    for column in range(8)
}

COLS = {
    "store": ["MARKET", "LOCAL_DATE", "DAILY_VISITS", "CATEGORY", "STORE_ID"],
    "weather": [
        "CITY_LOCATION_IDENTIFIER__UP_TO_9_ALPHANUMERIC_CHARACTERS_",
        "VALID_DATE_AS_YYYYMMDD",
        "AVERAGE_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE",
        "MAXIMUM_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE",
        "MINIMUM_TEMPERATURE_C___FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE",
        "AVERAGE_RELATIVE_HUMIDITY_____FLOAT_VALUE_TO_NEAREST_HUNDREDTHS_PLACE",
    ],
}


def _files(paths: ProjectPaths, dataset: str) -> list[Path]:
    return sorted(paths.raw_dataset(dataset).glob("*.gz")) if paths.raw_dataset(dataset).is_dir() else []


def _read_chunks(path: Path, usecols: list[str], chunksize: int = 250_000) -> Iterable[pd.DataFrame]:
    try:
        reader = pd.read_csv(path, compression="gzip", usecols=lambda col: col in usecols, chunksize=chunksize)
        yield from reader
    except (OSError, ValueError, pd.errors.ParserError):
        return


def _expand_city_allocations(frame: pd.DataFrame, market_col: str = "MARKET") -> pd.DataFrame:
    """Expand source markets to canonical cities with explicit allocation weights."""

    rows: list[pd.DataFrame] = []
    for market, group in frame.groupby(market_col, dropna=False):
        cities = cities_for_market(str(market))
        if not cities:
            continue
        allocation = 1.0 / len(cities)
        for city in cities:
            copy = group.copy()
            copy["city"] = city
            copy["allocation"] = allocation
            copy["source_market"] = market
            copy["evidence_status"] = (
                EvidenceStatus.PARTIAL.value if len(cities) > 1 else EvidenceStatus.DERIVED.value
            )
            rows.append(copy)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _partition_warnings(paths: ProjectPaths, dataset: str) -> list[str]:
    observed = {path.name for path in _files(paths, dataset)}
    expected = {name for name in PARTITION_GRID if name.startswith(f"{dataset}_")}
    missing = sorted(expected.difference(observed))
    return [f"{dataset}: missing partitions: {', '.join(missing)}"] if missing else []


def _write(df: pd.DataFrame, paths: ProjectPaths, name: str) -> Path:
    paths.artifact_root.mkdir(parents=True, exist_ok=True)
    target = paths.artifact_root / name
    df.to_parquet(target, index=False)
    return target


def _portable_path(paths: ProjectPaths, path: Path) -> str:
    try:
        return path.resolve().relative_to(paths.repo_root.resolve()).as_posix()
    except ValueError:
        return path.name


def _market_manifest(
    paths: ProjectPaths,
    dataset: str,
    rows_read: int,
    rows_written: int,
    artifact: Path,
    warnings: list[str] | None = None,
    quality=None,
    force_partial: bool = False,
) -> DataManifest:
    files = _files(paths, dataset)
    partition_warnings = _partition_warnings(paths, dataset)
    return DataManifest(
        dataset=dataset,
        source_root=f"{RICE_COLLECTION}/{dataset}",
        expected_partitions=EXPECTED_PARTITIONS[dataset],
        discovered_partitions=len(files),
        rows_read=quality.rows_read if quality is not None else rows_read,
        rows_written=rows_written,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        source_version=CONTRACT_VERSION,
        coverage_start=quality.coverage_start if quality is not None else None,
        coverage_end=quality.coverage_end if quality is not None else None,
        artifact_path=_portable_path(paths, artifact),
        artifact_sha256=_sha256(artifact),
        status=(
            EvidenceStatus.PARTIAL
            if force_partial
            or partition_warnings
            or len(files) < EXPECTED_PARTITIONS[dataset]
            or (quality is not None and not quality.passed)
            else EvidenceStatus.OBSERVED
        ),
        warnings=tuple((warnings or []) + partition_warnings),
        quality=quality,
    )


def _haversine_miles(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    radius = 3958.8
    phi1 = math.radians(lat)
    phi2 = np.radians(lats)
    dphi = phi2 - phi1
    dlam = np.radians(lons - lon)
    a = np.sin(dphi / 2) ** 2 + math.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def build_store_visits(paths: ProjectPaths) -> tuple[Path, Path, DataManifest]:
    totals: defaultdict[tuple[str, str], float] = defaultdict(float)
    categories: defaultdict[tuple[str, str, str], float] = defaultdict(float)
    rows_read = 0
    warnings: list[str] = []
    partial_cities: set[str] = set()
    source_markets: defaultdict[str, set[str]] = defaultdict(set)
    quality = QualityTracker("store-visits-rice")
    for file in _files(paths, "store-visits-rice"):
        for chunk in _read_chunks(file, COLS["store"]):
            if not quality.observe(
                chunk,
                required=COLS["store"],
                key_columns=("STORE_ID", "LOCAL_DATE"),
                date_columns=("LOCAL_DATE",),
                numeric_ranges={"DAILY_VISITS": (0, float("inf"))},
            ):
                continue
            quality.check_allowed_values(chunk, "MARKET", set(MARKET_TO_CITY))
            rows_read += len(chunk)
            chunk = chunk.dropna(subset=["MARKET", "LOCAL_DATE", "DAILY_VISITS"])
            chunk["date"] = pd.to_datetime(chunk["LOCAL_DATE"], errors="coerce").dt.date
            chunk["visits"] = pd.to_numeric(chunk["DAILY_VISITS"], errors="coerce")
            chunk["category"] = chunk["CATEGORY"].fillna("Other").astype(str)
            chunk = chunk.dropna(subset=["date", "visits"])
            expanded = _expand_city_allocations(chunk)
            if expanded.empty:
                continue
            partial_cities.update(expanded.loc[expanded["evidence_status"] == "partial", "city"].unique())
            for city, markets in expanded.groupby("city")["source_market"]:
                source_markets[str(city)].update(str(market) for market in markets.dropna().unique())
            expanded["weighted_visits"] = expanded["visits"] * expanded["allocation"]
            for (city, day), value in expanded.groupby(["city", "date"])["weighted_visits"].sum().items():
                totals[(city, str(day))] += float(value)
            for (city, day, category), value in expanded.groupby(["city", "date", "category"])["weighted_visits"].sum().items():
                categories[(city, str(day), category)] += float(value)
    total_df = pd.DataFrame([{"city": c, "date": d, "daily_visits": v} for (c, d), v in totals.items()], columns=["city", "date", "daily_visits"])
    category_df = pd.DataFrame([{"city": c, "date": d, "category": k, "daily_visits": v} for (c, d, k), v in categories.items()], columns=["city", "date", "category", "daily_visits"])
    for frame in (total_df, category_df):
        frame["source_dataset"] = "store-visits-rice"
        frame["source_market"] = frame["city"].map(lambda city: " / ".join(sorted(source_markets.get(str(city), set()))))
        frame["evidence_status"] = np.where(frame["city"].isin(partial_cities), "partial", "derived")
    total_path = _write(total_df.sort_values(["city", "date"]), paths, "visits_daily.parquet")
    category_path = _write(category_df.sort_values(["city", "date", "category"]), paths, "visits_daily_category.parquet")
    if len(_files(paths, "store-visits-rice")) < EXPECTED_PARTITIONS["store-visits-rice"]:
        warnings.append("Store-visits partition coverage is incomplete.")
    if partial_cities:
        warnings.append(
            "Combined source markets were equally allocated to Dallas/Houston and Los Angeles/San Francisco; those city series are partial."
        )
    return total_path, category_path, _market_manifest(
        paths,
        "store-visits-rice",
        rows_read,
        len(total_df),
        total_path,
        warnings + quality.warnings,
        quality.report(),
        force_partial=bool(partial_cities),
    )


def _weather_columns(columns: list[str]) -> dict[str, str] | None:
    def find(prefix: str) -> str | None:
        return next((column for column in columns if column.startswith(prefix)), None)

    station = find("CITY_LOCATION_IDENTIFIER")
    date_col = find("VALID_DATE")
    avg_temp = find("AVERAGE_TEMPERATURE_C")
    max_temp = find("MAXIMUM_TEMPERATURE_C")
    min_temp = find("MINIMUM_TEMPERATURE_C")
    humidity = find("AVERAGE_RELATIVE_HUMIDITY")
    if not all((station, date_col, avg_temp, max_temp, min_temp, humidity)):
        return None
    mapping = {"station": station, "date": date_col, "avg_temp_c": avg_temp, "max_temp_c": max_temp, "min_temp_c": min_temp, "humidity": humidity}
    optional = {
        "dew_point_f": find("AVERAGE_DEW_POINT"),
        "pressure_mb": find("AVERAGE_SEA_LEVEL_PRESSURE"),
        "precip_hundredths_mm": find("PRECIPITATION_INTEGER"),
    }
    mapping.update({key: value for key, value in optional.items() if value is not None})
    return mapping


def build_weather(paths: ProjectPaths) -> tuple[Path, DataManifest]:
    rows: list[pd.DataFrame] = []
    rows_read = 0
    warnings: list[str] = []
    quality = QualityTracker("daily-weather-rice")
    stations = set(WEATHER_STATIONS.values())
    for file in _files(paths, "daily-weather-rice"):
        try:
            header = pd.read_csv(file, compression="gzip", nrows=0).columns.tolist()
        except (OSError, pd.errors.ParserError):
            continue
        columns = _weather_columns(header)
        if columns is None:
            warnings.append(f"Could not identify weather columns in {file.name}.")
            continue
        for chunk in _read_chunks(file, list(columns.values()), chunksize=100_000):
            chunk = chunk.rename(columns={value: key for key, value in columns.items()})
            if not quality.observe(
                chunk,
                required=("station", "date", "avg_temp_c", "max_temp_c", "min_temp_c", "humidity"),
                key_columns=("station", "date"),
                date_columns=("date",),
                numeric_ranges={
                    "avg_temp_c": (-90, 70),
                    "max_temp_c": (-90, 75),
                    "min_temp_c": (-90, 70),
                    "humidity": (0, 100),
                },
                sentinels={
                    column: {-999998.5, -999999}
                    for column in ("dew_point_f", "pressure_mb")
                    if column in chunk
                },
            ):
                continue
            rows_read += len(chunk)
            chunk = chunk[chunk["station"].isin(stations)].copy()
            chunk["city"] = chunk["station"].map({station: city for city, station in WEATHER_STATIONS.items()})
            chunk["station_name"] = chunk["city"].map(
                {city: metadata["name"] for city, metadata in WEATHER_STATION_METADATA.items()}
            )
            chunk["station_distance_mi"] = chunk["city"].map(
                {city: metadata["distance_mi"] for city, metadata in WEATHER_STATION_METADATA.items()}
            )
            chunk["evidence_status"] = np.where(
                pd.to_numeric(chunk["station_distance_mi"], errors="coerce") <= 30,
                EvidenceStatus.DERIVED.value,
                EvidenceStatus.PARTIAL.value,
            )
            chunk["date"] = pd.to_datetime(chunk["date"], errors="coerce")
            for column in ("avg_temp_c", "max_temp_c", "min_temp_c", "humidity"):
                chunk[column] = pd.to_numeric(chunk[column], errors="coerce")
            rows.append(
                chunk.dropna(subset=["city", "date", "avg_temp_c", "humidity"])[
                    [
                        "city",
                        "date",
                        "avg_temp_c",
                        "max_temp_c",
                        "min_temp_c",
                        "humidity",
                        "station",
                        "station_name",
                        "station_distance_mi",
                        "evidence_status",
                    ]
                ]
            )
    if rows:
        frame = pd.concat(rows, ignore_index=True).groupby(["city", "date"], as_index=False).agg(
            avg_temp_c=("avg_temp_c", "mean"), max_temp_c=("max_temp_c", "mean"),
            min_temp_c=("min_temp_c", "mean"), humidity=("humidity", "mean"),
            station=("station", "first"), station_name=("station_name", "first"),
            station_distance_mi=("station_distance_mi", "first"), evidence_status=("evidence_status", "first"),
        )
    else:
        frame = pd.DataFrame(
            columns=[
                "city", "date", "avg_temp_c", "max_temp_c", "min_temp_c", "humidity",
                "station", "station_name", "station_distance_mi", "evidence_status",
            ]
        )
    frame["source_dataset"] = "daily-weather-rice"
    fallback_stations = [
        f"{city}: {metadata['station']} ({metadata['distance_mi']} mi)"
        for city, metadata in WEATHER_STATION_METADATA.items()
        if str(metadata["station"]) != PRIMARY_WEATHER_STATIONS[city]
    ]
    if fallback_stations:
        warnings.append(
            "Primary host stations are absent with missing partition 2_0_0; nearest supplied stations were used: "
            + "; ".join(fallback_stations)
        )
    path = _write(frame.sort_values(["city", "date"]), paths, "weather_city_daily.parquet")
    return path, _market_manifest(paths, "daily-weather-rice", rows_read, len(frame), path, warnings + quality.warnings, quality.report())


def build_uhi(paths: ProjectPaths) -> tuple[Path, DataManifest]:
    market_rows: list[pd.DataFrame] = []
    rows_read = 0
    quality = QualityTracker("urban-heat-index-rice")
    for file in _files(paths, "urban-heat-index-rice"):
        for chunk in _read_chunks(file, ["LATITUDE", "LONGITUDE", "MARKET", "UHI"], chunksize=300_000):
            if not quality.observe(
                chunk,
                required=("LATITUDE", "LONGITUDE", "MARKET", "UHI"),
                key_columns=("LATITUDE", "LONGITUDE"),
                numeric_ranges={"UHI": (0, 100)},
                coordinate_columns=("LATITUDE", "LONGITUDE"),
            ):
                continue
            quality.check_allowed_values(chunk, "MARKET", set(MARKET_TO_CITY))
            rows_read += len(chunk)
            chunk["city"] = chunk["MARKET"].map(MARKET_TO_CITY)
            chunk["LATITUDE"] = pd.to_numeric(chunk["LATITUDE"], errors="coerce")
            chunk["LONGITUDE"] = pd.to_numeric(chunk["LONGITUDE"], errors="coerce")
            chunk["UHI"] = pd.to_numeric(chunk["UHI"], errors="coerce")
            chunk = chunk.dropna(subset=["city", "LATITUDE", "LONGITUDE", "UHI"])
            market_rows.append(chunk[["city", "LATITUDE", "LONGITUDE", "UHI"]])
    if market_rows:
        frame = pd.concat(market_rows, ignore_index=True)
        summary = frame.groupby("city", as_index=False).agg(
            avg_uhi=("UHI", "mean"), p90_uhi=("UHI", lambda values: float(np.percentile(values, 90))), max_uhi=("UHI", "max"),
        )
        venue_rows = []
        for city, meta in HOST_CITIES.items():
            city_points = frame[frame["city"] == city]
            if city_points.empty:
                continue
            distance = _haversine_miles(float(meta["lat"]), float(meta["lon"]), city_points["LATITUDE"].to_numpy(), city_points["LONGITUDE"].to_numpy())
            nearby = city_points.loc[distance <= 2.0, "UHI"]
            venue_rows.append({"city": city, "venue_avg_uhi": float(nearby.mean()) if not nearby.empty else None, "venue_p90_uhi": float(np.percentile(nearby, 90)) if not nearby.empty else None, "venue_points": int(len(nearby))})
        venue_frame = pd.DataFrame(venue_rows, columns=["city", "venue_avg_uhi", "venue_p90_uhi", "venue_points"])
        summary = summary.merge(venue_frame, on="city", how="left")
    else:
        summary = pd.DataFrame(columns=["city", "avg_uhi", "p90_uhi", "max_uhi", "venue_avg_uhi", "venue_p90_uhi", "venue_points"])
    summary["source_dataset"] = "urban-heat-index-rice"
    summary["evidence_status"] = np.where(
        pd.to_numeric(summary.get("venue_points", 0), errors="coerce").fillna(0) > 0,
        EvidenceStatus.DERIVED.value,
        EvidenceStatus.PARTIAL.value,
    )
    path = _write(summary.sort_values("city"), paths, "uhi_city_summary.parquet")
    return path, _market_manifest(paths, "urban-heat-index-rice", rows_read, len(summary), path, quality.warnings, quality.report())


def _customer_origin_items(raw: object) -> Iterable[tuple[str, object]]:
    """Yield origin/count pairs from both schemas present in the Rice files."""

    try:
        values = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError, json.JSONDecodeError):
        return
    if not isinstance(values, dict):
        return
    keyed_values = values.get("key_value")
    if isinstance(keyed_values, list):
        for item in keyed_values:
            if isinstance(item, dict) and isinstance(item.get("key"), str) and "value" in item:
                yield item["key"], item["value"]
        return
    for location, count in values.items():
        if isinstance(location, str):
            yield location, count


def build_spend_origins(paths: ProjectPaths) -> tuple[Path, DataManifest]:
    origins: defaultdict[tuple[str, str], float] = defaultdict(float)
    spend: defaultdict[str, float] = defaultdict(float)
    rows_read = 0
    quality = QualityTracker("spend-patterns-rice")
    partial_cities: set[str] = set()
    for file in _files(paths, "spend-patterns-rice"):
        usecols = ["MARKET", "CUSTOMER_HOME_CITY", "RAW_TOTAL_SPEND", "RAW_NUM_CUSTOMERS", "PLACEKEY", "SPEND_DATE_RANGE_START"]
        for chunk in _read_chunks(file, usecols, chunksize=100_000):
            if not quality.observe(
                chunk,
                required=usecols,
                key_columns=("PLACEKEY", "SPEND_DATE_RANGE_START"),
                date_columns=("SPEND_DATE_RANGE_START",),
                numeric_ranges={"RAW_TOTAL_SPEND": (0, float("inf")), "RAW_NUM_CUSTOMERS": (0, float("inf"))},
            ):
                continue
            quality.check_allowed_values(chunk, "MARKET", set(MARKET_TO_CITY))
            rows_read += len(chunk)
            chunk["spend"] = pd.to_numeric(chunk["RAW_TOTAL_SPEND"], errors="coerce")
            chunk["customers"] = pd.to_numeric(chunk["RAW_NUM_CUSTOMERS"], errors="coerce")
            chunk = chunk.dropna(subset=["spend", "customers"])
            for market, group in chunk.groupby("MARKET", dropna=False):
                cities = cities_for_market(str(market))
                if not cities:
                    continue
                allocation = 1.0 / len(cities)
                for city in cities:
                    if len(cities) > 1:
                        partial_cities.add(city)
                    spend[city] += float(group["spend"].sum()) * allocation
                    for raw in group["CUSTOMER_HOME_CITY"].dropna():
                        for location, count in _customer_origin_items(raw):
                            state = location.rsplit(", ", 1)[-1] if ", " in location else "Unknown"
                            try:
                                origins[(city, state)] += float(count) * allocation
                            except (TypeError, ValueError):
                                quality._count("invalid_origin_counts", count=1)
                                quality._message_once(quality.warnings, "spend-patterns-rice: invalid customer-origin counts were skipped.")
    origin_df = pd.DataFrame(
        [{"city": city, "home_state": state, "count": count} for (city, state), count in origins.items()],
        columns=["city", "home_state", "count"],
    )
    spend_df = pd.DataFrame(
        [{"city": city, "raw_total_spend": value} for city, value in spend.items()],
        columns=["city", "raw_total_spend"],
    )
    output = origin_df.merge(spend_df, on="city", how="outer")
    output["source_dataset"] = "spend-patterns-rice"
    output["evidence_status"] = np.where(output["city"].isin(partial_cities), "partial", "derived")
    path = _write(output.sort_values(["city", "count"], ascending=[True, False]), paths, "spend_origins.parquet")
    warnings = list(quality.warnings)
    if partial_cities:
        warnings.append("Combined source markets were equally allocated; affected city origin and spend summaries are partial.")
    return path, _market_manifest(
        paths,
        "spend-patterns-rice",
        rows_read,
        len(output),
        path,
        warnings,
        quality.report(),
        force_partial=bool(partial_cities),
    )


def build_poi(paths: ProjectPaths) -> tuple[Path, DataManifest]:
    rows: list[dict[str, object]] = []
    rows_read = 0
    source_cities: set[str] = set()
    quality = QualityTracker("core-poi-geometry-rice")
    columns = ["MARKET", "LATITUDE", "LONGITUDE", "TOP_CATEGORY", "PLACEKEY"]
    for file in _files(paths, "core-poi-geometry-rice"):
        for chunk in _read_chunks(file, columns, chunksize=150_000):
            if not quality.observe(
                chunk,
                required=columns,
                key_columns=("PLACEKEY",),
                numeric_ranges={"LATITUDE": (-90, 90), "LONGITUDE": (-180, 180)},
                coordinate_columns=("LATITUDE", "LONGITUDE"),
            ):
                continue
            quality.check_allowed_values(chunk, "MARKET", set(MARKET_TO_CITY))
            rows_read += len(chunk)
            chunk["city"] = chunk["MARKET"].map(MARKET_TO_CITY)
            chunk["LATITUDE"] = pd.to_numeric(chunk["LATITUDE"], errors="coerce")
            chunk["LONGITUDE"] = pd.to_numeric(chunk["LONGITUDE"], errors="coerce")
            chunk = chunk.dropna(subset=["city", "LATITUDE", "LONGITUDE"])
            source_cities.update(str(city) for city in chunk["city"].unique())
            for city, meta in HOST_CITIES.items():
                points = chunk[chunk["city"] == city]
                if points.empty:
                    continue
                distance = _haversine_miles(float(meta["lat"]), float(meta["lon"]), points["LATITUDE"].to_numpy(), points["LONGITUDE"].to_numpy())
                nearby = points.loc[distance <= 1.0]
                if not nearby.empty:
                    counts = nearby.assign(category=nearby["TOP_CATEGORY"].fillna("Other")).groupby("category").size()
                    rows.extend({"city": city, "category": str(category), "poi_count_1mi": int(count)} for category, count in counts.items())
    result = pd.DataFrame(rows, columns=["city", "category", "poi_count_1mi"])
    if not result.empty:
        result = result.groupby(["city", "category"], as_index=False)["poi_count_1mi"].sum()
    cities_with_poi = set(result["city"]) if not result.empty else set()
    zero_rows = pd.DataFrame(
        [
            {"city": city, "category": "No qualifying POIs within one mile", "poi_count_1mi": 0}
            for city in sorted(source_cities.difference(cities_with_poi))
        ]
    )
    if not zero_rows.empty:
        result = pd.concat([result, zero_rows], ignore_index=True)
    result["source_dataset"] = "core-poi-geometry-rice"
    result["evidence_status"] = EvidenceStatus.DERIVED.value
    path = _write(result.sort_values(["city", "poi_count_1mi"], ascending=[True, False]), paths, "poi_venue_summary.parquet")
    return path, _market_manifest(paths, "core-poi-geometry-rice", rows_read, len(result), path, quality.warnings, quality.report())


def build_brand_spend(paths: ProjectPaths) -> tuple[Path, DataManifest]:
    rows: list[pd.DataFrame] = []
    rows_read = 0
    quality = QualityTracker("daily-spend-brand-and-state-rice")
    partial_cities: set[str] = set()
    columns = ["MARKET", "SPEND_AMOUNT", "TRANS_COUNT", "TRANS_DATE", "BRAND_ID", "STATE_ABBR"]
    for file in _files(paths, "daily-spend-brand-and-state-rice"):
        for chunk in _read_chunks(file, columns, chunksize=150_000):
            if not quality.observe(
                chunk,
                required=columns,
                key_columns=("BRAND_ID", "STATE_ABBR", "TRANS_DATE"),
                date_columns=("TRANS_DATE",),
                numeric_ranges={"SPEND_AMOUNT": (0, float("inf")), "TRANS_COUNT": (0, float("inf"))},
            ):
                continue
            quality.check_allowed_values(chunk, "MARKET", set(MARKET_TO_CITY))
            rows_read += len(chunk)
            expanded = _expand_city_allocations(chunk)
            if expanded.empty:
                continue
            partial_cities.update(expanded.loc[expanded["evidence_status"] == "partial", "city"].unique())
            expanded["date"] = pd.to_datetime(expanded["TRANS_DATE"], errors="coerce")
            expanded["spend"] = pd.to_numeric(expanded["SPEND_AMOUNT"], errors="coerce") * expanded["allocation"]
            expanded["transactions"] = pd.to_numeric(expanded["TRANS_COUNT"], errors="coerce") * expanded["allocation"]
            expanded = expanded.dropna(subset=["date", "spend", "transactions"])
            rows.append(expanded.groupby(["city", "STATE_ABBR", "date"], as_index=False).agg(
                spend=("spend", "sum"), transactions=("transactions", "sum"), brand_count=("BRAND_ID", "nunique")
            ))
    result = (
        pd.concat(rows, ignore_index=True).groupby(["city", "STATE_ABBR", "date"], as_index=False).sum()
        if rows else pd.DataFrame(columns=["city", "STATE_ABBR", "date", "spend", "transactions", "brand_count"])
    )
    result = result.rename(columns={"STATE_ABBR": "state"})
    result["source_dataset"] = "daily-spend-brand-and-state-rice"
    result["evidence_status"] = np.where(result["city"].isin(partial_cities), "partial", "derived")
    path = _write(result.sort_values(["city", "date"]), paths, "brand_spend_city_daily.parquet")
    warnings = list(quality.warnings)
    if partial_cities:
        warnings.append("Combined source markets were equally allocated; affected city economic summaries are partial.")
    return path, _market_manifest(
        paths,
        "daily-spend-brand-and-state-rice",
        rows_read,
        len(result),
        path,
        warnings,
        quality.report(),
        force_partial=bool(partial_cities),
    )


def _resume_store_visits(paths: ProjectPaths) -> tuple[Path, Path, DataManifest]:
    """Reuse store artifacts, preserving certified accounting when hashes match."""

    total_path = paths.artifact_root / "visits_daily.parquet"
    category_path = paths.artifact_root / "visits_daily_category.parquet"
    if not total_path.exists() or not category_path.exists():
        raise FileNotFoundError("Resume requested, but completed visit artifacts are not present.")
    total = pd.read_parquet(total_path)
    category = pd.read_parquet(category_path, columns=["city"])
    manifest_path = paths.artifact_root / "manifest.json"
    try:
        prior_payload = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    except (OSError, json.JSONDecodeError):
        prior_payload = {}
    prior = next(
        (
            item
            for item in prior_payload.get("datasets", [])
            if isinstance(item, dict) and item.get("dataset") == "store-visits-rice"
        ),
        None,
    )
    if (
        prior
        and int(prior.get("rows_read", 0)) > 0
        and prior.get("artifact_sha256") == _sha256(total_path)
        and isinstance(prior.get("quality"), dict)
    ):
        prior_quality = prior["quality"]
        quality = DataQualityReport(
            generated_at_utc=str(prior_quality.get("generated_at_utc", prior.get("generated_at_utc", ""))),
            checks=tuple(prior_quality.get("checks", ())),
            errors=tuple(prior_quality.get("errors", ())),
            warnings=tuple(prior_quality.get("warnings", ())),
            rows_read=int(prior_quality.get("rows_read", prior["rows_read"])),
            coverage_start=prior_quality.get("coverage_start", prior.get("coverage_start")),
            coverage_end=prior_quality.get("coverage_end", prior.get("coverage_end")),
        )
        warnings = [
            str(warning)
            for warning in prior.get("warnings", [])
            if "recovered" not in str(warning).lower()
        ]
        manifest = _market_manifest(
            paths,
            "store-visits-rice",
            quality.rows_read,
            len(total),
            total_path,
            warnings,
            quality,
            force_partial=prior.get("status") == EvidenceStatus.PARTIAL.value,
        )
        return total_path, category_path, manifest

    coverage_dates = pd.to_datetime(total.get("date"), errors="coerce").dropna()
    warning = (
        "Complete visit artifacts were recovered after a post-write manifest failure; raw rows were processed, "
        "but the in-memory raw-row counter was not recoverable. Rebuild store visits before final release certification."
    )
    quality = DataQualityReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        checks=(
            {
                "name": "recovered_artifacts",
                "visits_daily_rows": len(total),
                "visits_category_rows": len(category),
            },
        ),
        warnings=(warning,),
        rows_read=0,
        coverage_start=coverage_dates.min().date().isoformat() if not coverage_dates.empty else None,
        coverage_end=coverage_dates.max().date().isoformat() if not coverage_dates.empty else None,
    )
    manifest = _market_manifest(
        paths,
        "store-visits-rice",
        0,
        len(total),
        total_path,
        [warning],
        quality,
        force_partial=True,
    )
    return total_path, category_path, manifest


def build_all(paths: ProjectPaths, *, resume: bool = False) -> dict[str, object]:
    require_data_root(paths)
    paths.artifact_root.mkdir(parents=True, exist_ok=True)
    manifests: list[DataManifest] = []
    outputs: dict[str, str] = {}
    for builder in (build_store_visits, build_weather, build_uhi, build_spend_origins, build_poi, build_brand_spend):
        if builder is build_store_visits and resume:
            print("[etl] resuming from completed Rice WC Hack store-visit artifacts", flush=True)
            result = _resume_store_visits(paths)
        else:
            print(f"[etl] building {builder.__name__}", flush=True)
            result = builder(paths)
        if builder is build_store_visits:
            first, second, manifest = result
            outputs["visits_daily"] = _portable_path(paths, first)
            outputs["visits_daily_category"] = _portable_path(paths, second)
        else:
            artifact, manifest = result
            outputs[manifest.dataset] = _portable_path(paths, artifact)
        manifests.append(manifest)
        print(f"[etl] completed {manifest.dataset}: {manifest.rows_written:,} derived rows", flush=True)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_collection": RICE_COLLECTION,
        "data_root": RICE_COLLECTION,
        "artifacts": outputs,
        "datasets": [manifest.to_dict() for manifest in manifests],
        "status": "partial" if any(
            manifest.status == EvidenceStatus.PARTIAL or (manifest.quality is not None and not manifest.quality.passed)
            for manifest in manifests
        ) else "observed",
    }
    (paths.artifact_root / "manifest.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (paths.artifact_root / "qa_report.json").write_text(
        json.dumps(
            {
                "generated_at_utc": payload["generated_at_utc"],
                "source_collection": RICE_COLLECTION,
                "status": payload["status"],
                "datasets": [manifest.to_dict() for manifest in manifests],
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--resume", action="store_true", help="Reuse completed store-visit artifacts when their hash is verified.")
    args = parser.parse_args()
    paths = project_paths(explicit_data_root=args.data_root)
    if args.output:
        paths = ProjectPaths(paths.repo_root, paths.data_root, Path(args.output).resolve())
    payload = build_all(paths, resume=args.resume)
    print(json.dumps(payload, indent=2, default=str))


if __name__ == "__main__":
    main()
