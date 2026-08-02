import json

import pandas as pd

from dashboard.mobility_platform.config import ProjectPaths
from dashboard.pipeline.etl.build import _customer_origin_items, _expand_city_allocations, _resume_store_visits, _sha256
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


def test_combined_rice_markets_are_explicitly_partial_allocations():
    frame = pd.DataFrame({"MARKET": ["Dallas / Houston"], "value": [10]})
    result = _expand_city_allocations(frame)
    assert set(result["city"]) == {"Dallas", "Houston"}
    assert set(result["allocation"]) == {0.5}
    assert set(result["source_market"]) == {"Dallas / Houston"}
    assert set(result["evidence_status"]) == {"partial"}


def test_customer_origins_support_plain_mapping_schema():
    result = dict(_customer_origin_items('{"Clayton, CA": 2, "Reno, NV": 1}'))
    assert result == {"Clayton, CA": 2, "Reno, NV": 1}


def test_customer_origins_support_key_value_schema():
    raw = '{"key_value": [{"key": "Clayton, CA", "value": 2}, {"key": "Reno, NV", "value": 1}]}'
    result = dict(_customer_origin_items(raw))
    assert result == {"Clayton, CA": 2, "Reno, NV": 1}


def test_resume_preserves_certified_store_row_accounting(tmp_path):
    artifact_root = tmp_path / "cache"
    artifact_root.mkdir()
    total_path = artifact_root / "visits_daily.parquet"
    category_path = artifact_root / "visits_daily_category.parquet"
    pd.DataFrame({"city": ["Atlanta"], "date": ["2024-01-01"], "daily_visits": [10]}).to_parquet(total_path)
    pd.DataFrame({"city": ["Atlanta"], "category": ["Retail"], "daily_visits": [10]}).to_parquet(category_path)
    payload = {
        "datasets": [
            {
                "dataset": "store-visits-rice",
                "rows_read": 123,
                "generated_at_utc": "2026-01-01T00:00:00+00:00",
                "coverage_start": "2024-01-01",
                "coverage_end": "2024-01-01",
                "artifact_sha256": _sha256(total_path),
                "status": "partial",
                "warnings": ["Combined source markets remain partial."],
                "quality": {
                    "generated_at_utc": "2026-01-01T00:00:00+00:00",
                    "checks": [{"name": "summary", "rows_read": 123}],
                    "errors": [],
                    "warnings": [],
                    "rows_read": 123,
                    "coverage_start": "2024-01-01",
                    "coverage_end": "2024-01-01",
                },
            }
        ]
    }
    (artifact_root / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    paths = ProjectPaths(repo_root=tmp_path, data_root=tmp_path / "raw", artifact_root=artifact_root)

    _, _, manifest = _resume_store_visits(paths)

    assert manifest.rows_read == 123
    assert all("recovered" not in warning.lower() for warning in manifest.warnings)
