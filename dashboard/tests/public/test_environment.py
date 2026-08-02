from __future__ import annotations

import copy
from pathlib import Path

import pytest

from dashboard.pipeline.public.environment import (
    load_snapshot,
    relative_humidity,
    validate_snapshot,
)

SNAPSHOT = Path("data/snapshots/environment/venue_environment.json")


def test_environment_snapshot_is_hashed_and_semantically_explicit():
    snapshot = load_snapshot(SNAPSHOT)
    assert snapshot["schema_version"] == "1.0.0"
    assert len(snapshot["weather_daily"]) == 366
    assert {row["city"] for row in snapshot["weather_daily"]} == {"Miami", "New York/NJ"}
    assert all(row["station_distance_mi"] < 5 for row in snapshot["weather_daily"])
    assert all(row["hourly_observations"] >= 18 for row in snapshot["weather_daily"])
    boston = snapshot["uhi_city"][0]
    assert boston["city"] == "Boston"
    assert boston["scene_count"] == 5
    assert boston["venue_points"] > 0
    assert "surface-temperature anomaly" in boston["unit"]
    assert snapshot["replacement_policy"]["weather"] == ["Miami", "New York/NJ"]
    assert snapshot["replacement_policy"]["uhi"] == ["Boston"]


def test_relative_humidity_is_bounded_and_responds_to_dewpoint():
    assert relative_humidity(30, 10) < relative_humidity(30, 20) < relative_humidity(30, 30)
    assert relative_humidity(30, 30) == pytest.approx(100)


def test_environment_snapshot_tampering_fails_closed():
    changed = copy.deepcopy(load_snapshot(SNAPSHOT))
    changed["weather_daily"][0]["avg_temp_c"] += 1
    with pytest.raises(ValueError, match="content hash"):
        validate_snapshot(changed)
