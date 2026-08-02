import json
from datetime import datetime
from pathlib import Path

import pytest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash
from dashboard.pipeline.public.loaders import load_schedule_snapshot
from dashboard.pipeline.public.schedule import build_schedule

SNAPSHOT = Path("data/snapshots/fifa/fifa_2026_us_schedule.json")


def test_official_schedule_covers_all_us_matches_and_city_mappings():
    schedule = load_schedule_snapshot(SNAPSHOT)
    assert schedule["event_count"] == 78
    assert set(schedule["city_counts"]) == set(HOST_CITIES)
    assert schedule["city_counts"] == {city: int(meta["games"]) for city, meta in HOST_CITIES.items()}
    assert all(datetime.fromisoformat(event["kickoff_local"]).utcoffset() is not None for event in schedule["events"])
    assert all(event["kickoff_utc"].endswith("Z") for event in schedule["events"])


def test_schedule_has_source_hash_and_detects_artifact_tampering(tmp_path):
    schedule = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert len(schedule["source"]["sha256"]) == 64
    assert schedule["artifact_sha256"] == artifact_hash(schedule)
    schedule["event_count"] = 77
    path = tmp_path / "schedule.json"
    path.write_text(json.dumps(schedule), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_schedule_snapshot(path)


def test_unmapped_us_city_fails_closed():
    payload = json.dumps(
        {
            "Results": [
                {
                    "IdSeason": "285023",
                    "IdMatch": "x",
                    "MatchNumber": 1,
                    "Date": "2026-06-11T12:00:00Z",
                    "Stadium": {
                        "IdCountry": "USA",
                        "CityName": [{"Locale": "en-GB", "Description": "Unknown"}],
                    },
                }
            ]
        }
    ).encode()
    with pytest.raises(ValueError, match="Unmapped"):
        build_schedule(payload, "2026-01-01T00:00:00Z")
