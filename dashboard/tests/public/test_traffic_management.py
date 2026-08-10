from __future__ import annotations

import copy
from pathlib import Path

import pytest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash
from dashboard.pipeline.public.traffic_management import (
    SOURCE_DEFINITIONS,
    load_snapshot,
    missing_verification_terms,
    validate_snapshot,
)

SNAPSHOT = Path("data/snapshots/operations/world_cup_2026_traffic_management.json")


def test_traffic_management_snapshot_is_hashed_and_scoped():
    snapshot = load_snapshot(SNAPSHOT)
    assert set(snapshot["city_coverage"]) == set(HOST_CITIES)
    assert set(snapshot["plans"]) == {"Dallas"}
    assert snapshot["city_coverage"]["Dallas"]["published_plan_available"] is True
    assert sum(row["published_plan_available"] for row in snapshot["city_coverage"].values()) == 1
    assert all(len(source["sha256"]) == 64 for source in snapshot["sources"].values())

    dallas = snapshot["plans"]["Dallas"]
    assert dallas["primary_pattern"] == "Regional rail to charter-bus bridge"
    assert dallas["transfer_hubs"][2]["name"] == "TRE CentrePort/DFW Airport Station"
    assert len(dallas["published_controls"]) == 5


def test_traffic_management_snapshot_tampering_fails_closed():
    snapshot = load_snapshot(SNAPSHOT)
    changed = copy.deepcopy(snapshot)
    changed["plans"]["Dallas"]["arrival_window"] = "changed"
    with pytest.raises(ValueError, match="content hash"):
        validate_snapshot(changed)
    changed["artifact_sha256"] = artifact_hash(changed)
    validate_snapshot(changed)


def test_traffic_management_source_review_terms_fail_closed():
    definition = SOURCE_DEFINITIONS["dallas_fwc26_transportation_plan"]
    assert missing_verification_terms(definition, b"unrelated response") == [
        "CentrePort",
        "Dynamic Charter Buses",
        "Griffin Street",
    ]
    assert (
        missing_verification_terms(
            definition,
            b"CentrePort Dynamic Charter Buses Griffin Street",
        )
        == []
    )


def test_traffic_management_rejects_invalid_source_reference():
    snapshot = load_snapshot(SNAPSHOT)
    changed = copy.deepcopy(snapshot)
    changed["plans"]["Dallas"]["source_ids"] = ["missing"]
    changed["artifact_sha256"] = artifact_hash(changed)
    with pytest.raises(ValueError, match="invalid source references"):
        validate_snapshot(changed)
