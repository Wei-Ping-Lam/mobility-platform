"""Strict cache-only loaders for compact public-evidence snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.pipeline.public.common import artifact_hash, read_json, validate_source


def _load(path: str | Path, expected_kind: str) -> dict[str, Any]:
    snapshot = read_json(Path(path))
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError(f"Contract mismatch in {path}")
    if snapshot.get("snapshot_kind") != expected_kind:
        raise ValueError(f"Expected {expected_kind}, found {snapshot.get('snapshot_kind')}")
    expected_hash = snapshot.get("artifact_sha256")
    if expected_hash and expected_hash != artifact_hash(snapshot):
        raise ValueError(f"Artifact content hash mismatch: {path}")
    return snapshot


def load_schedule_snapshot(path: str | Path = "data/snapshots/fifa/fifa_2026_us_schedule.json") -> dict[str, Any]:
    snapshot = _load(path, "fifa_schedule")
    validate_source(snapshot["source"])
    return snapshot


def load_factor_registry(path: str | Path = "data/snapshots/factors/planning_factors.json") -> dict[str, Any]:
    snapshot = _load(path, "planning_factor_registry")
    for source in snapshot["sources"].values():
        validate_source(source)
    from dashboard.models.interventions import factor_registry_from_snapshot

    factor_registry_from_snapshot(snapshot)
    return snapshot


def load_walking_snapshot(path: str | Path = "data/snapshots/osm/walking_networks.json") -> dict[str, Any]:
    snapshot = _load(path, "osm_walking_networks")
    from dashboard.pipeline.public.walking import validate_snapshot

    validate_snapshot(snapshot)
    return snapshot


def load_gtfs_snapshot(path: str | Path = "data/snapshots/gtfs/gtfs_venue_access.json") -> dict[str, Any]:
    snapshot = _load(path, "gtfs_venue_access")
    for city in snapshot.get("cities", {}).values():
        for feed in city.get("feeds", []):
            status = feed.get("status", "unavailable")
            digest = feed.get("sha256")
            if status in {"observed", "partial"} and (not isinstance(digest, str) or len(digest) != 64):
                raise ValueError("Available GTFS evidence is missing its feed hash")
        if city.get("feed_status") == "unavailable":
            city["gtfs_transit_score"] = None
            city["score_status"] = "unavailable"
    return snapshot
