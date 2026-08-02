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
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["daily_visits"] = pd.to_numeric(frame["daily_visits"], errors="coerce")
    frame = frame.dropna(subset=["date", "daily_visits"])
    if frame.empty:
        return pd.DataFrame(columns=["date", "actual", "baseline"])
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
    """Run rolling 2023/2024 holdouts against a seasonal-naive comparator."""

    rows = []
    if visits.empty or not {"city", "date", "daily_visits"}.issubset(visits.columns):
        return pd.DataFrame()
    frame = visits.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["daily_visits"] = pd.to_numeric(frame["daily_visits"], errors="coerce")
    frame = frame.dropna(subset=["city", "date", "daily_visits"])
    for city in sorted(frame["city"].unique()):
        city_frame = frame[frame["city"] == city].sort_values("date")
        for holdout_year in (2023, 2024):
            holdout_start = pd.Timestamp(f"{holdout_year}-01-01")
            holdout_end = pd.Timestamp(f"{holdout_year + 1}-01-01")
            primary_start = pd.Timestamp("2022-01-01")
            training = city_frame[(city_frame["date"] >= primary_start) & (city_frame["date"] < holdout_start)]
            holdout = city_frame[(city_frame["date"] >= holdout_start) & (city_frame["date"] < holdout_end)].copy()
            if training.empty or holdout.empty:
                continue
            training = training.assign(month=training["date"].dt.month, weekday=training["date"].dt.dayofweek)
            profile = training.groupby(["month", "weekday"])["daily_visits"].median()
            holdout["month"] = holdout["date"].dt.month
            holdout["weekday"] = holdout["date"].dt.dayofweek
            holdout["candidate"] = [profile.get((month, weekday), np.nan) for month, weekday in zip(holdout["month"], holdout["weekday"])]
            naive_lookup = training.set_index("date")["daily_visits"]
            holdout["seasonal_naive"] = [(naive_lookup.get(date - pd.Timedelta(days=364))) for date in holdout["date"]]
            holdout = holdout.dropna(subset=["candidate", "seasonal_naive"])
            if holdout.empty:
                continue
            actual = holdout["daily_visits"]
            denominator = float(actual.abs().sum())
            candidate_error = actual - holdout["candidate"]
            naive_error = actual - holdout["seasonal_naive"]
            candidate_wape = float(candidate_error.abs().sum() / denominator) if denominator else None
            naive_wape = float(naive_error.abs().sum() / denominator) if denominator else None
            rows.append({
                "city": city,
                "holdout_year": holdout_year,
                "training_start": training["date"].min(),
                "training_end": training["date"].max(),
                "n": len(holdout),
                "mae": float(candidate_error.abs().mean()),
                "rmse": float(np.sqrt((candidate_error**2).mean())),
                "wape": candidate_wape,
                "seasonal_naive_mae": float(naive_error.abs().mean()),
                "seasonal_naive_wape": naive_wape,
                "outperforms_seasonal_naive": bool(
                    candidate_wape is not None and naive_wape is not None and candidate_wape < naive_wape
                ),
            })
    return pd.DataFrame(rows)


def scenario_band(visits: pd.DataFrame, city: str, uplift_low: float = 1.5, uplift_base: float = 3.0, uplift_high: float = 4.5) -> pd.DataFrame:
    baseline = seasonal_baseline(visits, city)
    if baseline.empty:
        return pd.DataFrame(columns=["date", "low", "base", "high", "status"])
    event_dates = pd.date_range("2026-06-11", "2026-07-19", freq="D")
    reference = baseline.copy()
    reference["month"] = reference["date"].dt.month
    reference["weekday"] = reference["date"].dt.dayofweek
    profile = reference.groupby(["month", "weekday"])["baseline"].median()
    result = pd.DataFrame({"date": event_dates})
    result["month"] = result["date"].dt.month
    result["weekday"] = result["date"].dt.dayofweek
    fallback = float(baseline["baseline"].median())
    result["reference"] = [profile.get((month, weekday), fallback) for month, weekday in zip(result["month"], result["weekday"])]
    result["low"] = result["reference"] * uplift_low
    result["base"] = result["reference"] * uplift_base
    result["high"] = result["reference"] * uplift_high
    result["status"] = "scenario"
    return result[["date", "low", "base", "high", "status"]]
