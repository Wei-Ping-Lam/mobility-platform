"""Transparent economic-activity scenario ranges."""

from __future__ import annotations

import pandas as pd


def economic_impact_range(
    brand_spend: pd.DataFrame,
    city: str,
    *,
    event_days: int = 39,
    uplift_low: float = 0.02,
    uplift_base: float = 0.05,
    uplift_high: float = 0.10,
) -> dict[str, object]:
    """Estimate a range of incremental local spend without claiming causality.

    The baseline is the median daily observed spend for 2022--2024. The uplift
    rates are explicit scenario assumptions, not an estimated treatment effect.
    """

    required = {"city", "date", "spend"}
    if brand_spend.empty or not required.issubset(brand_spend.columns):
        return {
            "city": city,
            "status": "unavailable",
            "unit": "USD",
            "value": None,
            "low": None,
            "base": None,
            "high": None,
            "sample_size": 0,
            "coverage_start": None,
            "coverage_end": None,
            "assumptions": ["Brand/state spend artifact is unavailable or missing required columns."],
        }

    frame = brand_spend[brand_spend["city"] == city].copy()
    if frame.empty:
        return {
            "city": city,
            "status": "unavailable",
            "unit": "USD",
            "value": None,
            "low": None,
            "base": None,
            "high": None,
            "sample_size": 0,
            "coverage_start": None,
            "coverage_end": None,
            "assumptions": ["No observed brand/state activity is available for this city."],
        }

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["spend"] = pd.to_numeric(frame["spend"], errors="coerce")
    frame = frame.dropna(subset=["date", "spend"])
    training = frame[frame["date"].dt.year.between(2022, 2024)]
    if training.empty:
        training = frame
    daily = training.groupby("date", as_index=False)["spend"].sum()
    baseline_daily = float(daily["spend"].median()) if not daily.empty else None
    if baseline_daily is None:
        return {
            "city": city,
            "status": "unavailable",
            "unit": "USD",
            "value": None,
            "low": None,
            "base": None,
            "high": None,
            "sample_size": 0,
            "coverage_start": None,
            "coverage_end": None,
            "assumptions": ["No valid daily spend observations remain after validation."],
        }

    return {
        "city": city,
        "status": "scenario",
        "unit": "USD incremental spend over event window",
        "value": round(baseline_daily * event_days * uplift_base, 2),
        "baseline_daily_spend": round(baseline_daily, 2),
        "low": round(baseline_daily * event_days * uplift_low, 2),
        "base": round(baseline_daily * event_days * uplift_base, 2),
        "high": round(baseline_daily * event_days * uplift_high, 2),
        "sample_size": int(len(daily)),
        "coverage_start": str(daily["date"].min().date()),
        "coverage_end": str(daily["date"].max().date()),
        "assumptions": [
            f"Event window is {event_days} days.",
            f"Uplift assumptions are {uplift_low:.0%}/{uplift_base:.0%}/{uplift_high:.0%} low/base/high.",
            "This uses general commercial activity and is not causal attribution or ticketed-fan spend.",
        ],
    }

