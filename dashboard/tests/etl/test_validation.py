import pandas as pd

from dashboard.pipeline.schemas.validation import QualityTracker


def test_quality_tracker_records_duplicates_ranges_and_sentinels():
    frame = pd.DataFrame({
        "id": ["a", "a"],
        "date": ["2024-01-01", "not-a-date"],
        "value": [4, -1],
        "sentinel": [-999999, 1],
    })
    tracker = QualityTracker("fixture")
    assert tracker.observe(
        frame,
        required=("id", "date", "value", "sentinel"),
        key_columns=("id",),
        date_columns=("date",),
        numeric_ranges={"value": (0, 10)},
        sentinels={"sentinel": {-999999}},
    )
    report = tracker.report()
    assert report.passed
    assert any(check["name"] == "duplicate_keys" for check in report.checks)
    assert any(check["name"] == "out_of_range_values:value" for check in report.checks)
    assert any(check["name"] == "sentinel_values:sentinel" for check in report.checks)
    assert report.warnings


def test_quality_tracker_rejects_missing_schema():
    tracker = QualityTracker("fixture")
    assert not tracker.observe(pd.DataFrame({"id": [1]}), required=("id", "missing"))
    report = tracker.report()
    assert not report.passed
    assert "missing required columns" in report.errors[0]
