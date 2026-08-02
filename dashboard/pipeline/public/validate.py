"""Validate all compact public-evidence snapshots without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.loaders import (
    load_factor_registry,
    load_gtfs_snapshot,
    load_schedule_snapshot,
    load_walking_snapshot,
)
from dashboard.pipeline.public.walking import validate_snapshot as validate_walking


def validate_all(root: Path) -> dict[str, object]:
    schedule = load_schedule_snapshot(root / "fifa" / "fifa_2026_us_schedule.json")
    factors = load_factor_registry(root / "factors" / "planning_factors.json")
    walking = load_walking_snapshot(root / "osm" / "walking_networks.json")
    validate_walking(walking)
    gtfs = load_gtfs_snapshot(root / "gtfs" / "gtfs_venue_access.json")
    expected = set(HOST_CITIES)
    if set(schedule["city_counts"]) != expected or set(walking["cities"]) != expected or set(gtfs["cities"]) != expected:
        raise ValueError("A public snapshot is missing one or more U.S. host cities")
    return {
        "contract_version": schedule["contract_version"],
        "schedule_events": schedule["event_count"],
        "factor_count": len(factors["factors"]),
        "walking_cities": len(walking["cities"]),
        "walking_status": walking["status"],
        "gtfs_cities": len(gtfs["cities"]),
        "gtfs_status": gtfs["status"],
        "passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data/snapshots"))
    args = parser.parse_args()
    print(json.dumps(validate_all(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
