import pandas as pd

from dashboard.models.demand import seasonal_baseline, validation_metrics


def test_seasonal_baseline_has_expected_shape():
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="7D")
    visits = pd.DataFrame({"city": "Atlanta", "date": dates, "daily_visits": 100.0})
    result = seasonal_baseline(visits, "Atlanta")
    assert len(result) == len(visits)
    assert {"date", "actual", "baseline"}.issubset(result.columns)


def test_validation_reports_rolling_seasonal_naive_comparison():
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="7D")
    visits = pd.DataFrame({"city": "Atlanta", "date": dates, "daily_visits": 100.0})
    result = validation_metrics(visits)
    assert {"holdout_year", "wape", "seasonal_naive_wape", "outperforms_seasonal_naive"}.issubset(result.columns)
    assert set(result["holdout_year"]) == {2023, 2024}
