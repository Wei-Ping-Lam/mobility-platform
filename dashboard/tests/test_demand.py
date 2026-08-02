import pandas as pd

from dashboard.models.demand import scenario_band, seasonal_baseline, validation_metrics


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


def test_validation_excludes_pandemic_years_from_primary_training():
    dates = pd.date_range("2020-01-01", "2024-12-31", freq="D")
    visits = pd.DataFrame({"city": "Atlanta", "date": dates, "daily_visits": 100.0})
    result = validation_metrics(visits)
    assert not result.empty
    assert pd.to_datetime(result["training_start"]).min() >= pd.Timestamp("2022-01-01")


def test_event_scenario_preserves_seasonal_weekday_shape():
    dates = pd.date_range("2022-01-01", "2024-12-31", freq="D")
    visits = pd.DataFrame({
        "city": "Atlanta",
        "date": dates,
        "daily_visits": [200.0 if date.dayofweek >= 5 else 100.0 for date in dates],
    })
    result = scenario_band(visits, "Atlanta")
    assert result["base"].nunique() > 1
    assert set(result["status"]) == {"scenario"}
