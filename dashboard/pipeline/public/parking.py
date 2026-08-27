"""Refresh and validate compact, pinned OSM parking-facility evidence.

Mirrors the shape of dashboard/pipeline/public/walking.py: fetches real
OpenStreetMap data for each host venue via OSMnx, distills it into a compact
cache-only JSON snapshot, and is validated the same way before the dashboard
reads it. Counts amenity=parking facilities within cumulative 0.5/1/2-mile
rings of the venue (matching the GTFS stop-density convention in
dashboard/pipeline/gtfs/fetch.py), and separately sums any real OSM
`capacity` tag among the facilities that have one - most OSM parking features
are untagged for capacity, so facility counts are the primary signal and
tagged capacity is reported only where it exists, never estimated.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import osmnx as ox
import pandas as pd

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash, base_snapshot, sha256_bytes, validate_source, write_json

OSM_URL = "https://www.openstreetmap.org/copyright"
RADIUS_MILES = 2.0
RADIUS_METERS = RADIUS_MILES * 1609.344
RETRIES = 3


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_miles = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius_miles * math.asin(math.sqrt(value))


def _parse_capacity(value: Any) -> int | None:
    """Parse an OSM `capacity` tag, which is free text (e.g. "450", "~500", "no")."""

    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    digits = "".join(character for character in str(value) if character.isdigit())
    if not digits:
        return None
    parsed = int(digits)
    return parsed if parsed > 0 else None


def _feature_rows(features: pd.DataFrame, venue_lat: float, venue_lon: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if features.empty:
        return rows
    capacities = features["capacity"] if "capacity" in features.columns else pd.Series([None] * len(features))
    for geometry, capacity in zip(features.geometry, capacities):
        if geometry is None or geometry.is_empty:
            continue
        centroid = geometry.centroid
        distance_mi = _haversine_miles(venue_lat, venue_lon, float(centroid.y), float(centroid.x))
        rows.append({"distance_mi": distance_mi, "capacity": _parse_capacity(capacity)})
    return rows


def _band_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "facility_count_0_5mi": sum(1 for row in rows if row["distance_mi"] <= 0.5),
        "facility_count_1mi": sum(1 for row in rows if row["distance_mi"] <= 1.0),
        "facility_count_2mi": sum(1 for row in rows if row["distance_mi"] <= 2.0),
    }


def _band_capacity(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tagged_capacity_0_5mi": sum(row["capacity"] for row in rows if row["distance_mi"] <= 0.5 and row["capacity"]),
        "tagged_capacity_1mi": sum(row["capacity"] for row in rows if row["distance_mi"] <= 1.0 and row["capacity"]),
        "tagged_capacity_2mi": sum(row["capacity"] for row in rows if row["distance_mi"] <= 2.0 and row["capacity"]),
    }


def validate_parking_city(row: dict[str, Any]) -> None:
    counts = (row.get("facility_count_0_5mi"), row.get("facility_count_1mi"), row.get("facility_count_2mi"))
    if any(value is None for value in counts):
        if row.get("status") != "unavailable":
            raise ValueError(f"Missing facility counts for {row.get('city')}")
        return
    if not counts[0] <= counts[1] <= counts[2]:
        raise ValueError(f"Cumulative facility-count invariant failed for {row.get('city')}")
    for value in counts:
        if value < 0:
            raise ValueError(f"Negative facility count for {row.get('city')}")
    tagged = row.get("facilities_with_capacity_tag", 0)
    total = row.get("total_facilities", 0)
    if tagged > total:
        raise ValueError(f"Tagged-capacity count exceeds total facilities for {row.get('city')}")


def _fetch_features(venue: dict[str, Any]) -> pd.DataFrame:
    error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            return ox.features.features_from_point(
                (float(venue["lat"]), float(venue["lon"])),
                tags={"amenity": "parking"},
                dist=RADIUS_METERS,
            )
        except Exception as exc:  # OSMnx wraps network and Overpass errors across several libraries.
            error = exc
            if attempt < RETRIES - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"OSM parking refresh failed after {RETRIES} attempts: {error}") from error


def _city_snapshot(city: str, venue: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    query = {"center": [venue["lat"], venue["lon"]], "distance_m": RADIUS_METERS, "tags": {"amenity": "parking"}}
    try:
        features = _fetch_features(venue)
        rows = _feature_rows(features, float(venue["lat"]), float(venue["lon"]))
        descriptor = json.dumps({"city": city, "facility_count": len(rows)}, sort_keys=True).encode()
        source = {
            "source": "OpenStreetMap two-mile parking-facility extract",
            "url": OSM_URL,
            "publisher": "OpenStreetMap contributors",
            "retrieved_at_utc": retrieved_at,
            "version": f"OSMnx {ox.__version__}",
            "sha256": sha256_bytes(descriptor),
            "license": "Open Database License (ODbL)",
            "status": "derived",
            "notes": (
                "Facility counts and any tagged capacity are OSM planning evidence, not a verified stadium "
                "event-day parking supply or operator-confirmed capacity."
            ),
        }
        row = {
            "city": city,
            "venue": venue["venue"],
            "venue_lat": venue["lat"],
            "venue_lon": venue["lon"],
            "snapshot_kind": "osm_parking_density",
            "schema_version": "1.0.0",
            "status": "derived",
            "query": query,
            **_band_counts(rows),
            **_band_capacity(rows),
            "facilities_with_capacity_tag": sum(1 for row_item in rows if row_item["capacity"] is not None),
            "total_facilities": len(rows),
            "source": source,
        }
        validate_parking_city(row)
        return row
    except Exception as exc:
        descriptor = json.dumps({"city": city, "query": query, "error": str(exc)[:500]}, sort_keys=True).encode()
        return {
            "city": city,
            "venue": venue["venue"],
            "venue_lat": venue["lat"],
            "venue_lon": venue["lon"],
            "snapshot_kind": "osm_parking_density",
            "schema_version": "1.0.0",
            "status": "unavailable",
            "query": query,
            "facility_count_0_5mi": None,
            "facility_count_1mi": None,
            "facility_count_2mi": None,
            "tagged_capacity_0_5mi": None,
            "tagged_capacity_1mi": None,
            "tagged_capacity_2mi": None,
            "facilities_with_capacity_tag": None,
            "total_facilities": None,
            "error": str(exc)[:500],
            "source": {
                "source": "OpenStreetMap parking-facility refresh attempt",
                "url": OSM_URL,
                "publisher": "OpenStreetMap contributors",
                "retrieved_at_utc": retrieved_at,
                "version": f"OSMnx {ox.__version__}",
                "sha256": sha256_bytes(descriptor),
                "license": "Open Database License (ODbL)",
                "status": "unavailable",
                "notes": "No facility evidence is published for this failed refresh.",
            },
        }


def build_snapshot(
    cache_root: Path,
    selected_cities: tuple[str, ...] | None = None,
    existing_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(cache_root)
    ox.settings.requests_timeout = 180
    cities = dict((existing_snapshot or {}).get("cities", {}))
    selected = selected_cities or tuple(HOST_CITIES)
    for city in selected:
        venue = HOST_CITIES[city]
        print(json.dumps({"city": city, "phase": "parking_density_refresh"}), flush=True)
        cities[city] = _city_snapshot(city, venue, retrieved_at)
        print(json.dumps({"city": city, "status": cities[city]["status"]}), flush=True)
    city_hashes = {city: row["source"]["sha256"] for city, row in cities.items()}
    source = {
        "source": "OpenStreetMap two-mile parking-facility extracts",
        "url": OSM_URL,
        "publisher": "OpenStreetMap contributors",
        "retrieved_at_utc": retrieved_at,
        "version": f"OSMnx {ox.__version__}",
        "sha256": sha256_bytes(json.dumps(city_hashes, sort_keys=True).encode()),
        "license": "Open Database License (ODbL)",
        "status": "derived" if all(row["status"] != "unavailable" for row in cities.values()) else "partial",
        "notes": "Hashes identify each city's extract descriptor; compact derived counts are tracked, not raw OSM geometry.",
    }
    snapshot = base_snapshot("osm_parking_density", retrieved_at)
    snapshot.update(
        {
            "schema_version": "1.0.0",
            "status": source["status"],
            "source": source,
            "radius_miles": RADIUS_MILES,
            "cities": cities,
            "policy": {
                "runtime": "cache-only; no OSM request during dashboard use",
                "capacity": "Tagged capacity is reported only where OSM has it; missing tags are not estimated",
                "scope": "amenity=parking facilities only - not curb space, loading zones, or private lots without that tag",
            },
        }
    )
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Parking snapshot contract version mismatch")
    if snapshot.get("snapshot_kind") != "osm_parking_density":
        raise ValueError("Parking snapshot must be OSM-derived, not a fixture")
    validate_source(snapshot["source"])
    cities = snapshot.get("cities")
    if not isinstance(cities, dict) or set(cities) != set(HOST_CITIES):
        raise ValueError("Parking snapshot must contain exactly all 11 U.S. host cities")
    for row in cities.values():
        validate_parking_city(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Fetch parking-facility density for all 11 host venues")
    mode.add_argument("--validate", type=Path, help="Validate an existing compact parking-density snapshot")
    parser.add_argument("--cache-root", type=Path, default=Path("data/osmnx-cache"))
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/osm/parking_density.json"))
    parser.add_argument(
        "--city",
        action="append",
        choices=tuple(HOST_CITIES),
        help="Refresh only selected cities and preserve the other validated city snapshots",
    )
    args = parser.parse_args()
    existing = None
    if args.refresh and args.city and args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
    snapshot = (
        build_snapshot(args.cache_root, tuple(dict.fromkeys(args.city)) if args.city else None, existing)
        if args.refresh
        else json.loads(args.validate.read_text(encoding="utf-8"))
    )
    validate_snapshot(snapshot)
    digest = write_json(args.output, snapshot) if args.refresh else sha256_bytes(args.validate.read_bytes())
    print(json.dumps({"status": snapshot["status"], "cities": len(snapshot["cities"]), "sha256": digest}))


if __name__ == "__main__":
    main()
