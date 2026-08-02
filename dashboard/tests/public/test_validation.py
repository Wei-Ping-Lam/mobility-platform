from pathlib import Path

from dashboard.pipeline.public.validate import validate_all


def test_all_checked_public_snapshots_validate():
    report = validate_all(Path("data/snapshots"))
    assert report == {
        "contract_version": "0.3.0",
        "schedule_events": 78,
        "factor_count": 20,
        "walking_cities": 11,
        "walking_status": "derived",
        "gtfs_cities": 11,
        "gtfs_status": "observed",
        "passed": True,
    }
