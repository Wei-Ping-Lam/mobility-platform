"""Validate pinned OSM walking evidence or generate an explicit deterministic fixture."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash, base_snapshot, sha256_bytes, validate_source, write_json

OSM_URL = "https://www.openstreetmap.org/copyright"
FIXTURE_TIME = "2026-08-01T00:00:00Z"


def _circle(lon: float, lat: float, radius_m: float, vertices: int = 16) -> dict[str, Any]:
    coordinates = []
    for index in range(vertices):
        angle = 2 * math.pi * index / vertices
        dy = radius_m / 111_320 * math.sin(angle)
        dx = radius_m / (111_320 * math.cos(math.radians(lat))) * math.cos(angle)
        coordinates.append([round(lon + dx, 6), round(lat + dy, 6)])
    coordinates.append(coordinates[0])
    return {"type": "Polygon", "coordinates": [coordinates]}


def validate_walking_city(row: dict[str, Any]) -> None:
    straight = float(row["straight_distance_m"])
    network = float(row["network_distance_m"])
    if straight < 0 or network < straight - 1:
        raise ValueError(f"Network distance invariant failed for {row.get('city')}")
    expected = network / straight if straight else 1.0
    if abs(float(row["detour_ratio"]) - expected) > 0.001:
        raise ValueError(f"Detour ratio is inconsistent for {row.get('city')}")
    for field in ("sidewalk_tag_coverage_pct", "crossing_tag_coverage_pct"):
        if not 0 <= float(row[field]) <= 100:
            raise ValueError(f"Invalid {field} for {row.get('city')}")
    if row.get("status") == "observed" and row.get("snapshot_kind") == "fixture":
        raise ValueError("A deterministic fixture cannot be observed OSM evidence")


def build_fixture() -> dict[str, Any]:
    source_descriptor = {
        "url": OSM_URL,
        "license": "Open Database License (ODbL); fixture contains no extracted OSM features",
        "version": "fixture-schema-1",
    }
    source = {
        "source": "OpenStreetMap walking-network schema fixture",
        "url": OSM_URL,
        "publisher": "OpenStreetMap contributors",
        "retrieved_at_utc": FIXTURE_TIME,
        "version": "fixture-schema-1",
        "sha256": sha256_bytes(json.dumps(source_descriptor, sort_keys=True).encode()),
        "license": source_descriptor["license"],
        "coverage_start": None,
        "coverage_end": None,
        "status": "estimated",
        "hash_scope": "canonical fixture source descriptor; no OSM extract bytes are represented",
        "notes": "Deterministic contract fixture only; run validation against a pinned five-mile OSM extract before promotion.",
    }
    cities: dict[str, Any] = {}
    for index, (city, venue) in enumerate(HOST_CITIES.items()):
        straight = float(300 + index * 41)
        ratio = round(1.08 + (index % 5) * 0.07, 3)
        network = round(straight * ratio, 1)
        row = {
            "city": city,
            "venue": venue["venue"],
            "venue_lat": venue["lat"],
            "venue_lon": venue["lon"],
            "snapshot_kind": "fixture",
            "status": "estimated",
            "target_kind": "representative transit access point",
            "straight_distance_m": straight,
            "network_distance_m": network,
            "detour_ratio": round(network / straight, 3),
            "sidewalk_tag_coverage_pct": float(35 + (index * 7) % 50),
            "crossing_tag_coverage_pct": float(25 + (index * 9) % 55),
            "accessibility_status": "not_measured",
            "isochrones": [
                {"minutes": 15, "geometry": _circle(float(venue["lon"]), float(venue["lat"]), 1_000)},
                {"minutes": 30, "geometry": _circle(float(venue["lon"]), float(venue["lat"]), 2_000)},
            ],
            "source": source,
        }
        validate_walking_city(row)
        cities[city] = row
    snapshot = base_snapshot("osm_walking_fixture", FIXTURE_TIME)
    snapshot.update(
        {
            "status": "estimated",
            "source": source,
            "radius_miles": 5.0,
            "cities": cities,
            "schema": {
                "required_city_fields": sorted(next(iter(cities.values())).keys()),
                "observed_promotion_gate": "Pinned extract hash, connected walking graph, and validated path are required",
                "ada_policy": "Missing OSM tags never imply ADA accessibility",
            },
        }
    )
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Walking snapshot contract version mismatch")
    validate_source(snapshot["source"])
    cities = snapshot.get("cities")
    if not isinstance(cities, dict) or set(cities) != set(HOST_CITIES):
        raise ValueError("Walking snapshot must contain exactly all 11 U.S. host cities")
    for row in cities.values():
        validate_walking_city(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture", action="store_true", help="Write the deterministic non-observed contract fixture")
    source.add_argument("--validate", type=Path, help="Validate a compact snapshot built from a pinned local OSM extract")
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/osm/walking_networks.json"))
    args = parser.parse_args()
    snapshot = build_fixture() if args.fixture else json.loads(args.validate.read_text(encoding="utf-8"))
    validate_snapshot(snapshot)
    digest = write_json(args.output, snapshot) if args.fixture else sha256_bytes(args.validate.read_bytes())
    print(json.dumps({"status": snapshot["status"], "cities": len(snapshot["cities"]), "sha256": digest}))


if __name__ == "__main__":
    main()
