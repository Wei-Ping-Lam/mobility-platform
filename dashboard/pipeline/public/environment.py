"""Build pinned venue-proximate weather and surface-UHI supplements.

Runtime composition reads only the compact checked snapshot. Network access is
limited to the explicit ``--refresh`` command, while raw NOAA responses,
Planetary Computer STAC responses, and Landsat window arrays remain ignored.
"""

from __future__ import annotations

import argparse
import io
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import rasterio
import requests
from pyproj import Transformer
from rasterio.windows import from_bounds

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import (
    artifact_hash,
    base_snapshot,
    read_json,
    sha256_bytes,
    validate_source,
    write_json,
)

SCHEMA_VERSION = "1.0.0"
DEFAULT_RAW_ROOT = Path("data/raw/environment")
DEFAULT_OUTPUT = Path("data/snapshots/environment/venue_environment.json")
NOAA_ENDPOINT = "https://www.ncei.noaa.gov/access/services/data/v1"
PC_STAC_ENDPOINT = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
PC_SIGN_ENDPOINT = "https://planetarycomputer.microsoft.com/api/sas/v1/sign"
LANDSAT_COLLECTION = "landsat-c2-l2"
SUMMER_YEARS = (2022, 2023, 2024)
VENUE_RADIUS_M = 2 * 1609.344
REFERENCE_INNER_M = 3 * 1609.344
REFERENCE_OUTER_M = 8 * 1609.344

NOAA_STATIONS: dict[str, dict[str, Any]] = {
    "Miami": {
        "station": "72202412882",
        "ghcn_station": "USW00012882",
        "station_name": "Miami Opa Locka Airport",
        "lat": 25.9103,
        "lon": -80.2828,
        "timezone": "America/New_York",
    },
    "New York/NJ": {
        "station": "72502594741",
        "ghcn_station": "USW00094741",
        "station_name": "Teterboro Airport",
        "lat": 40.8589,
        "lon": -74.0561,
        "timezone": "America/New_York",
    },
}


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.7613
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_miles * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _aggregate_hash(values: list[str]) -> str:
    return sha256_bytes("\n".join(sorted(values)).encode("utf-8"))


def _noaa_url(station: str, year: int) -> str:
    params = {
        "dataset": "global-hourly",
        "stations": station,
        "startDate": f"{year}-06-01T00:00:00",
        "endDate": f"{year}-07-31T23:59:59",
        "format": "json",
        "includeAttributes": "true",
        "includeStationName": "true",
    }
    prepared = requests.Request("GET", NOAA_ENDPOINT, params=params).prepare()
    return str(prepared.url)


def _parse_isd_value(raw: object) -> float | None:
    if raw is None:
        return None
    token = str(raw).split(",", 1)[0].strip()
    try:
        value = int(token)
    except ValueError:
        return None
    if abs(value) >= 9999:
        return None
    return value / 10.0


def relative_humidity(temp_c: float, dewpoint_c: float) -> float:
    """Derive relative humidity using the Magnus saturation-vapor relation."""

    numerator = math.exp((17.625 * dewpoint_c) / (243.04 + dewpoint_c))
    denominator = math.exp((17.625 * temp_c) / (243.04 + temp_c))
    return float(np.clip(100 * numerator / denominator, 0, 100))


def _refresh_noaa(raw_root: Path, timeout_seconds: int) -> None:
    noaa_root = raw_root / "noaa"
    noaa_root.mkdir(parents=True, exist_ok=True)
    for definition in NOAA_STATIONS.values():
        for year in SUMMER_YEARS:
            response = requests.get(_noaa_url(definition["station"], year), timeout=timeout_seconds)
            response.raise_for_status()
            if not response.content or response.content.lstrip().startswith(b"<"):
                raise ValueError(f"NOAA returned an invalid response for {definition['station']} {year}")
            target = noaa_root / f"{definition['station']}_{year}_summer.json"
            target.write_bytes(response.content)


def _stac_query(year: int) -> dict[str, Any]:
    meta = HOST_CITIES["Boston"]
    return {
        "collections": [LANDSAT_COLLECTION],
        "intersects": {"type": "Point", "coordinates": [meta["lon"], meta["lat"]]},
        "datetime": f"{year}-06-01T00:00:00Z/{year}-07-31T23:59:59Z",
        "limit": 100,
        "query": {
            "eo:cloud_cover": {"lt": 25},
            "landsat:collection_category": {"eq": "T1"},
        },
    }


def _signed_href(href: str, timeout_seconds: int) -> str:
    response = requests.get(PC_SIGN_ENDPOINT, params={"href": href}, timeout=timeout_seconds)
    response.raise_for_status()
    signed = response.json().get("href")
    if not signed:
        raise ValueError("Planetary Computer did not return a signed Landsat asset URL")
    return str(signed)


def _read_landsat_window(item: Mapping[str, Any], timeout_seconds: int) -> tuple[np.ndarray, np.ndarray, Any, str]:
    assets = item.get("assets", {})
    temp_asset = assets.get("lwir11", {})
    qa_asset = assets.get("qa_pixel", {})
    temp_href = str(temp_asset.get("href", ""))
    qa_href = str(qa_asset.get("href", ""))
    if not temp_href or not qa_href:
        raise ValueError(f"Landsat item {item.get('id')} lacks temperature or QA assets")
    temp_signed = _signed_href(temp_href, timeout_seconds)
    qa_signed = _signed_href(qa_href, timeout_seconds)
    meta = HOST_CITIES["Boston"]
    with rasterio.open(temp_signed) as temperature_source:
        transformer = Transformer.from_crs("EPSG:4326", temperature_source.crs, always_xy=True)
        venue_x, venue_y = transformer.transform(meta["lon"], meta["lat"])
        window = from_bounds(
            venue_x - REFERENCE_OUTER_M,
            venue_y - REFERENCE_OUTER_M,
            venue_x + REFERENCE_OUTER_M,
            venue_y + REFERENCE_OUTER_M,
            temperature_source.transform,
        ).round_offsets().round_lengths()
        raw_temperature = temperature_source.read(1, window=window, boundless=True, fill_value=0)
        transform = temperature_source.window_transform(window)
    with rasterio.open(qa_signed) as qa_source:
        raw_qa = qa_source.read(1, window=window, boundless=True, fill_value=1)
    if raw_temperature.shape != raw_qa.shape:
        raise ValueError(f"Landsat item {item.get('id')} temperature and QA windows do not align")
    return raw_temperature, raw_qa, transform, temp_href


def _scene_statistics(
    item: Mapping[str, Any],
    raw_temperature: np.ndarray,
    qa: np.ndarray,
    transform: Any,
) -> tuple[dict[str, Any] | None, np.ndarray]:
    meta = HOST_CITIES["Boston"]
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{item['properties']['proj:epsg']}", always_xy=True)
    venue_x, venue_y = transformer.transform(meta["lon"], meta["lat"])
    rows, columns = np.indices(raw_temperature.shape)
    xs, ys = rasterio.transform.xy(transform, rows, columns, offset="center")
    x_array = np.asarray(xs).reshape(raw_temperature.shape)
    y_array = np.asarray(ys).reshape(raw_temperature.shape)
    distance = np.hypot(x_array - venue_x, y_array - venue_y)
    fill = (qa & 1) != 0
    dilated = (qa & (1 << 1)) != 0
    cirrus = (qa & (1 << 2)) != 0
    cloud = (qa & (1 << 3)) != 0
    shadow = (qa & (1 << 4)) != 0
    snow = (qa & (1 << 5)) != 0
    water = (qa & (1 << 7)) != 0
    valid = ~(fill | dilated | cirrus | cloud | shadow | snow | water) & (raw_temperature > 0)
    temperature_c = raw_temperature.astype("float32") * 0.00341802 + 149.0 - 273.15
    temperature_c[~valid] = np.nan
    venue_mask = valid & (distance <= VENUE_RADIUS_M)
    reference_mask = valid & (distance >= REFERENCE_INNER_M) & (distance <= REFERENCE_OUTER_M)
    venue_total = int(np.sum(distance <= VENUE_RADIUS_M))
    reference_total = int(np.sum((distance >= REFERENCE_INNER_M) & (distance <= REFERENCE_OUTER_M)))
    venue_count = int(venue_mask.sum())
    reference_count = int(reference_mask.sum())
    if venue_count < 500 or reference_count < 5_000:
        return None, temperature_c
    venue_coverage = venue_count / max(venue_total, 1)
    reference_coverage = reference_count / max(reference_total, 1)
    if venue_coverage < 0.60 or reference_coverage < 0.60:
        return None, temperature_c
    reference_median = float(np.nanmedian(temperature_c[reference_mask]))
    venue_values = temperature_c[venue_mask]
    return (
        {
            "item_id": item["id"],
            "acquired_at_utc": item["properties"]["datetime"],
            "scene_cloud_cover_pct": float(item["properties"].get("eo:cloud_cover", 100)),
            "venue_valid_pixels": venue_count,
            "reference_valid_pixels": reference_count,
            "venue_valid_coverage": round(venue_coverage, 6),
            "reference_valid_coverage": round(reference_coverage, 6),
            "venue_mean_surface_temp_c": round(float(np.nanmean(venue_values)), 4),
            "venue_p90_surface_temp_c": round(float(np.nanpercentile(venue_values, 90)), 4),
            "reference_median_surface_temp_c": round(reference_median, 4),
            "venue_mean_surface_uhi_c": round(float(np.nanmean(venue_values)) - reference_median, 4),
            "venue_p90_surface_uhi_c": round(float(np.nanpercentile(venue_values, 90)) - reference_median, 4),
            "venue_max_surface_uhi_c": round(float(np.nanmax(venue_values)) - reference_median, 4),
        },
        temperature_c,
    )


def _refresh_landsat(raw_root: Path, timeout_seconds: int) -> None:
    landsat_root = raw_root / "landsat"
    landsat_root.mkdir(parents=True, exist_ok=True)
    observations: list[dict[str, Any]] = []
    search_records: list[dict[str, Any]] = []
    for year in SUMMER_YEARS:
        query = _stac_query(year)
        response = requests.post(PC_STAC_ENDPOINT, json=query, timeout=timeout_seconds)
        response.raise_for_status()
        target = landsat_root / f"stac_boston_{year}.json"
        target.write_bytes(response.content)
        payload = response.json()
        search_records.append({"year": year, "query": query, "raw_filename": target.name, "sha256": sha256_bytes(response.content)})
        items = sorted(
            payload.get("features", []),
            key=lambda item: (
                float(item.get("properties", {}).get("eo:cloud_cover", 100)),
                str(item.get("properties", {}).get("datetime", "")),
                str(item.get("id", "")),
            ),
        )
        selected = 0
        for item in items:
            assets = item.get("assets", {})
            if "lwir11" not in assets or "qa_pixel" not in assets:
                continue
            raw_temperature, qa, transform, asset_href = _read_landsat_window(item, timeout_seconds)
            statistics, temperature_c = _scene_statistics(item, raw_temperature, qa, transform)
            if statistics is None:
                continue
            buffer = io.BytesIO()
            np.save(buffer, temperature_c, allow_pickle=False)
            clip_bytes = buffer.getvalue()
            clip_filename = f"{item['id']}_boston_8mi_temperature.npy"
            (landsat_root / clip_filename).write_bytes(clip_bytes)
            statistics.update(
                {
                    "year": year,
                    "asset_href": asset_href,
                    "clip_filename": clip_filename,
                    "clip_sha256": sha256_bytes(clip_bytes),
                    "scale": 0.00341802,
                    "offset_kelvin": 149.0,
                    "qa_exclusions": ["fill", "dilated cloud", "cirrus", "cloud", "cloud shadow", "snow", "water"],
                }
            )
            observations.append(statistics)
            selected += 1
            if selected == 2:
                break
        if selected < 1:
            raise ValueError(f"No locally valid Landsat surface-temperature scene found for Boston in {year}")
    raw_manifest = {
        "collection": LANDSAT_COLLECTION,
        "stac_endpoint": PC_STAC_ENDPOINT,
        "usgs_product": "Landsat Collection 2 Level-2 Surface Temperature",
        "venue_radius_m": VENUE_RADIUS_M,
        "reference_inner_m": REFERENCE_INNER_M,
        "reference_outer_m": REFERENCE_OUTER_M,
        "searches": search_records,
        "observations": observations,
    }
    write_json(landsat_root / "boston_landsat_observations.json", raw_manifest)


def refresh_source_files(raw_root: Path = DEFAULT_RAW_ROOT, timeout_seconds: int = 120) -> None:
    raw_root.mkdir(parents=True, exist_ok=True)
    _refresh_noaa(raw_root, timeout_seconds)
    _refresh_landsat(raw_root, timeout_seconds)


def _build_weather(raw_root: Path, generated_at_utc: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    sources: dict[str, dict[str, Any]] = {}
    for city, definition in NOAA_STATIONS.items():
        raw_hashes: list[str] = []
        retrievals: list[dict[str, Any]] = []
        hourly_rows: list[dict[str, Any]] = []
        timezone = ZoneInfo(definition["timezone"])
        for year in SUMMER_YEARS:
            path = raw_root / "noaa" / f"{definition['station']}_{year}_summer.json"
            if not path.exists():
                raise FileNotFoundError(f"Missing pinned NOAA response: {path}")
            raw_bytes = path.read_bytes()
            raw_hash = sha256_bytes(raw_bytes)
            raw_hashes.append(raw_hash)
            retrievals.append({"year": year, "url": _noaa_url(definition["station"], year), "raw_filename": path.name, "sha256": raw_hash})
            payload = json.loads(raw_bytes)
            if not isinstance(payload, list) or not payload:
                raise ValueError(f"NOAA response is empty for {city} {year}")
            for row in payload:
                temp_c = _parse_isd_value(row.get("TMP"))
                dewpoint_c = _parse_isd_value(row.get("DEW"))
                if temp_c is None or dewpoint_c is None or temp_c < -60 or temp_c > 60 or dewpoint_c > temp_c + 2:
                    continue
                timestamp = pd.Timestamp(row["DATE"], tz="UTC").tz_convert(timezone)
                hourly_rows.append(
                    {
                        "timestamp": timestamp,
                        "date": timestamp.date().isoformat(),
                        "temp_c": temp_c,
                        "humidity": relative_humidity(temp_c, dewpoint_c),
                    }
                )
        hourly = pd.DataFrame(hourly_rows).drop_duplicates("timestamp").sort_values("timestamp")
        if hourly.empty:
            raise ValueError(f"No valid NOAA temperature/dew-point pairs for {city}")
        daily = hourly.groupby("date", as_index=False).agg(
            avg_temp_c=("temp_c", "mean"),
            humidity=("humidity", "mean"),
            hourly_observations=("timestamp", "count"),
        )
        daily = daily[daily["hourly_observations"] >= 18]
        if len(daily) < 150:
            raise ValueError(f"Insufficient NOAA daily coverage for {city}: {len(daily)} valid days")
        venue = HOST_CITIES[city]
        distance = _haversine_miles(venue["lat"], venue["lon"], definition["lat"], definition["lon"])
        for row in daily.to_dict("records"):
            records.append(
                {
                    "city": city,
                    "date": row["date"],
                    "avg_temp_c": round(float(row["avg_temp_c"]), 4),
                    "humidity": round(float(row["humidity"]), 4),
                    "station": definition["station"],
                    "station_name": definition["station_name"],
                    "station_distance_mi": round(distance, 3),
                    "hourly_observations": int(row["hourly_observations"]),
                    "source_dataset": "noaa-global-hourly-supplement",
                    "evidence_status": "derived",
                    "source_id": f"noaa_global_hourly_{definition['station']}",
                }
            )
        sources[f"noaa_global_hourly_{definition['station']}"] = {
            "source": f"NOAA NCEI Global Hourly - {definition['station_name']}",
            "url": "https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database",
            "publisher": "NOAA National Centers for Environmental Information",
            "retrieved_at_utc": generated_at_utc,
            "version": "Global Hourly observations for June-July 2022-2024",
            "sha256": _aggregate_hash(raw_hashes),
            "license": "U.S. Government public data; retain NOAA attribution",
            "coverage_start": f"{min(SUMMER_YEARS)}-06-01",
            "coverage_end": f"{max(SUMMER_YEARS)}-07-31",
            "status": "derived",
            "notes": "SHA-256 aggregates the six pinned raw JSON response hashes; humidity is derived from observed temperature and dew point.",
            "city": city,
            "station": definition["station"],
            "ghcn_station": definition["ghcn_station"],
            "station_lat": definition["lat"],
            "station_lon": definition["lon"],
            "station_distance_mi": round(distance, 3),
            "retrievals": retrievals,
        }
    return records, sources


def _build_uhi(raw_root: Path, generated_at_utc: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = raw_root / "landsat" / "boston_landsat_observations.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    observations = manifest.get("observations", [])
    if len(observations) < 3 or len({row["year"] for row in observations}) < 2:
        raise ValueError("Boston Landsat supplement requires at least three valid scenes across two years")
    clip_hashes: list[str] = []
    for observation in observations:
        clip_path = raw_root / "landsat" / observation["clip_filename"]
        clip_hash = sha256_bytes(clip_path.read_bytes())
        if clip_hash != observation["clip_sha256"]:
            raise ValueError(f"Boston Landsat clip hash mismatch: {clip_path}")
        clip_hashes.append(clip_hash)
    mean_uhi = float(np.median([row["venue_mean_surface_uhi_c"] for row in observations]))
    p90_uhi = float(np.median([row["venue_p90_surface_uhi_c"] for row in observations]))
    max_uhi = float(max(row["venue_max_surface_uhi_c"] for row in observations))
    point_count = int(sum(row["venue_valid_pixels"] for row in observations))
    row = {
        "city": "Boston",
        "avg_uhi": round(mean_uhi, 4),
        "p90_uhi": round(p90_uhi, 4),
        "max_uhi": round(max_uhi, 4),
        "venue_avg_uhi": round(mean_uhi, 4),
        "venue_p90_uhi": round(p90_uhi, 4),
        "venue_points": point_count,
        "scene_count": len(observations),
        "coverage_start": min(row["acquired_at_utc"] for row in observations),
        "coverage_end": max(row["acquired_at_utc"] for row in observations),
        "source_dataset": "usgs-landsat-surface-uhi-supplement",
        "evidence_status": "derived",
        "source_id": "usgs_landsat_c2l2_boston_surface_uhi",
        "unit": "degrees Celsius surface-temperature anomaly",
        "method": "Median scene-level venue temperature minus 3-8 mile reference median; 2-mile venue buffer",
    }
    combined_hash = _aggregate_hash([sha256_bytes(manifest_bytes), *clip_hashes])
    source = {
        "source": "USGS Landsat Collection 2 Level-2 Surface Temperature",
        "url": "https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature",
        "publisher": "U.S. Geological Survey; COG access via Microsoft Planetary Computer public mirror",
        "retrieved_at_utc": generated_at_utc,
        "version": f"{len(observations)} Tier-1 summer scenes from 2022-2024",
        "sha256": combined_hash,
        "license": "USGS Landsat data are public domain; mirror terms and attribution retained",
        "coverage_start": row["coverage_start"],
        "coverage_end": row["coverage_end"],
        "status": "derived",
        "notes": "Hash aggregates the pinned STAC manifest and extracted temperature-window bytes; this is surface UHI, not air temperature or physiological exposure.",
        "city": "Boston",
        "stac_endpoint": PC_STAC_ENDPOINT,
        "collection": LANDSAT_COLLECTION,
        "venue_radius_m": VENUE_RADIUS_M,
        "reference_inner_m": REFERENCE_INNER_M,
        "reference_outer_m": REFERENCE_OUTER_M,
        "observations": observations,
    }
    return [row], source


def build_snapshot(raw_root: Path, generated_at_utc: str) -> dict[str, Any]:
    weather_daily, weather_sources = _build_weather(raw_root, generated_at_utc)
    uhi_city, uhi_source = _build_uhi(raw_root, generated_at_utc)
    sources = {**weather_sources, "usgs_landsat_c2l2_boston_surface_uhi": uhi_source}
    snapshot = {
        **base_snapshot("venue_environment_supplements", generated_at_utc),
        "schema_version": SCHEMA_VERSION,
        "status": "derived",
        "source_hash_scope": "Pinned NOAA JSON responses, STAC response manifest, and extracted Landsat temperature windows",
        "weather_daily": weather_daily,
        "uhi_city": uhi_city,
        "sources": sources,
        "replacement_policy": {
            "weather": ["Miami", "New York/NJ"],
            "uhi": ["Boston"],
            "reason": "Replace only Rice rows that fail strict venue-distance or venue-buffer coverage gates.",
        },
        "semantic_limits": [
            "NOAA station observations represent nearby ambient conditions, not venue microsensors.",
            "Landsat surface UHI is not air temperature, shade, mean radiant temperature, or physiological heat exposure.",
            "No supplement changes movement demand, observed mode share, or roadway congestion claims.",
        ],
    }
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: Mapping[str, Any]) -> None:
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Environment snapshot contract mismatch")
    if snapshot.get("snapshot_kind") != "venue_environment_supplements":
        raise ValueError("Unexpected environment snapshot kind")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Environment snapshot schema mismatch")
    if snapshot.get("artifact_sha256") != artifact_hash(dict(snapshot)):
        raise ValueError("Environment snapshot content hash mismatch")
    sources = snapshot.get("sources")
    if not isinstance(sources, Mapping) or len(sources) != 3:
        raise ValueError("Environment source inventory is incomplete")
    for source in sources.values():
        validate_source(dict(source))
    weather = snapshot.get("weather_daily")
    if not isinstance(weather, list) or not weather:
        raise ValueError("Environment weather rows are missing")
    weather_cities = {row.get("city") for row in weather}
    if weather_cities != {"Miami", "New York/NJ"}:
        raise ValueError("Environment weather coverage must include Miami and New York/NJ")
    for row in weather:
        if row.get("evidence_status") != "derived" or row.get("station_distance_mi", 999) > 15:
            raise ValueError(f"Environment weather row fails evidence or distance gate: {row.get('city')}")
        if row.get("hourly_observations", 0) < 18:
            raise ValueError(f"Environment weather row lacks hourly coverage: {row.get('city')} {row.get('date')}")
        if not (0 <= row.get("humidity", -1) <= 100):
            raise ValueError("Environment humidity is physically invalid")
    uhi_rows = snapshot.get("uhi_city")
    if not isinstance(uhi_rows, list) or len(uhi_rows) != 1 or uhi_rows[0].get("city") != "Boston":
        raise ValueError("Environment UHI coverage must contain Boston")
    uhi = uhi_rows[0]
    if uhi.get("evidence_status") != "derived" or uhi.get("scene_count", 0) < 3 or uhi.get("venue_points", 0) <= 0:
        raise ValueError("Boston surface-UHI supplement fails evidence coverage")
    if uhi.get("unit") != "degrees Celsius surface-temperature anomaly":
        raise ValueError("Boston surface-UHI unit is not explicit")


def load_snapshot(path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    snapshot = read_json(path)
    validate_snapshot(snapshot)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--retrieved-at", required=True, help="UTC ISO timestamp used for deterministic provenance")
    parser.add_argument("--refresh", action="store_true", help="Explicitly refresh NOAA and Landsat source material")
    args = parser.parse_args()
    if args.refresh:
        refresh_source_files(args.raw_root)
    snapshot = build_snapshot(args.raw_root, args.retrieved_at)
    write_json(args.output, snapshot)


if __name__ == "__main__":
    main()
