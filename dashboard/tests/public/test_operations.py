from __future__ import annotations

import copy
from pathlib import Path

import pytest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash
from dashboard.pipeline.public.operations import (
    SOURCE_DEFINITIONS,
    load_snapshot,
    missing_verification_terms,
    validate_snapshot,
)

SNAPSHOT = Path("data/snapshots/operations/world_cup_2026_operations.json")


def test_operational_snapshot_is_hashed_scoped_and_complete():
    snapshot = load_snapshot(SNAPSHOT)
    assert set(snapshot["city_coverage"]) == set(HOST_CITIES)
    assert len(snapshot["sources"]) == 11
    assert len(snapshot["metrics"]) == 33
    assert len(snapshot["event_records"]) == 13
    assert sum(row["metric_count"] > 0 for row in snapshot["city_coverage"].values()) == 11
    assert all(len(source["sha256"]) == 64 for source in snapshot["sources"].values())
    assert all(source["verification_terms"] for source in snapshot["sources"].values())
    assert all(row["source_locator"] and row["not_suitable_for"] for row in snapshot["metrics"])
    assert all(not row["match_hour_calibration_ready"] for row in snapshot["city_coverage"].values())
    assert {row["city"] for row in snapshot["event_records"]} == {
        "Houston", "New York/NJ", "San Francisco"
    }


def test_operational_snapshot_tampering_fails_closed():
    snapshot = load_snapshot(SNAPSHOT)
    changed = copy.deepcopy(snapshot)
    changed["metrics"][0]["value"] += 1
    with pytest.raises(ValueError, match="content hash"):
        validate_snapshot(changed)
    changed["artifact_sha256"] = artifact_hash(changed)
    validate_snapshot(changed)


def test_metric_source_and_city_counts_reconcile():
    snapshot = load_snapshot(SNAPSHOT)
    for city, coverage in snapshot["city_coverage"].items():
        rows = [row for row in snapshot["metrics"] if row["city"] == city]
        assert coverage["metric_count"] == len(rows)
        assert coverage["event_record_count"] == sum(
            row["city"] == city for row in snapshot["event_records"]
        )
        assert coverage["open_request_fields"]
        assert all(row["source_id"] in snapshot["sources"] for row in rows)


def test_source_review_terms_fail_closed():
    definition = SOURCE_DEFINITIONS["marta_world_cup_situation_2026"]
    assert missing_verification_terms(definition, b"unrelated response") == ["4,655,000", "240,000"]
    assert missing_verification_terms(definition, b"4,655,000 and 240,000") == []
