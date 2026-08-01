"""Evidence-first demand baselines, scenarios, and holdout validation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def seasonal_baseline(visits: pd.DataFrame, city: str) -> pd.DataFrame:
    if visits.empty:
        return pd.DataFrame(columns=["date", "actual", "baseline"])
    frame = visits[visits["city"] == city].copy()
    if frame.empty:
        return pd.DataFrame(columns=["date", "actual", "baseline"])
    frame["date"] = pd.to_datetime(frame["date"])
    frame["year"] = frame["date"].dt.year
    frame["month"] = frame["date"].dt.month
    frame["weekday"] = frame["date"].dt.dayofweek
    training = frame[frame["year"].between(2022, 2023)]
    if training.empty:
        training = frame
    profile = training.groupby(["month", "weekday"], as_index=False)["daily_visits"].median().rename(columns={"daily_visits": "baseline"})
    result = frame.merge(profile, on=["month", "weekday"], how="left").rename(columns={"daily_visits": "actual"})
    result["baseline"] = result["baseline"].fillna(result["actual"].median())
    return result[["date", "actual", "baseline"]].sort_values("date")


def validation_metrics(visits: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for city in sorted(visits["city"].dropna().unique()) if not visits.empty else []:
        series = seasonal_baseline(visits, city)
        holdout = series[series["date"].dt.year == 2024]
        if holdout.empty:
            continue
        error = holdout["actual"] - holdout["baseline"]
        denominator = holdout["actual"].abs().sum()
        rows.append({
            "city": city,
            "n": len(holdout),
            "mae": float(error.abs().mean()),
            "rmse": float(np.sqrt((error**2).mean())),
            "wape": float(error.abs().sum() / denominator) if denominator else None,
        })
    return pd.DataFrame(rows)


def scenario_band(visits: pd.DataFrame, city: str, uplift_low: float = 1.5, uplift_base: float = 3.0, uplift_high: float = 4.5) -> pd.DataFrame:
    baseline = seasonal_baseline(visits, city)
    if baseline.empty:
        return pd.DataFrame(columns=["date", "low", "base", "high", "status"])
    event_dates = pd.date_range("2026-06-11", "2026-07-19", freq="D")
    reference = float(baseline["baseline"].median())
    return pd.DataFrame({
        "date": event_dates,
        "low": reference * uplift_low,
        "base": reference * uplift_base,
        "high": reference * uplift_high,
        "status": "scenario",
    })
