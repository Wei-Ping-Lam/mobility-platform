import pandas as pd

from dashboard.models.demand import seasonal_baseline


def test_seasonal_baseline_has_expected_shape():
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="7D")
    visits = pd.DataFrame({"city": "Atlanta", "date": dates, "daily_visits": 100.0})
    result = seasonal_baseline(visits, "Atlanta")
    assert len(result) == len(visits)
    assert {"date", "actual", "baseline"}.issubset(result.columns)
