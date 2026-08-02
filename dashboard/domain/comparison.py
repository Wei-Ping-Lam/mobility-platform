"""Honest all-city screening and strict transportation comparison outputs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from dashboard.domain.scoring import DIMENSIONS, OBSERVED_STATUSES, normalize_weights


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) else None


def _screening_score(row: Mapping[str, Any], weights: Mapping[str, float]) -> dict[str, Any]:
    """Use available numeric evidence while bounding every non-strict component.

    The point estimate never fills a missing component. Low/high bounds allow any
    partial, estimated, scenario, or unavailable component to range from 0 to 100.
    This is deliberately conservative and is not a confidence interval.
    """

    weighted_sum = 0.0
    numeric_weight = 0.0
    fixed_sum = 0.0
    uncertain_weight = 0.0
    reasons: list[str] = []
    for dimension in DIMENSIONS:
        weight = float(weights[dimension])
        if weight <= 0:
            continue
        value = _number(row.get(f"{dimension}_score"))
        status = str(row.get(f"{dimension}_status") or "unavailable")
        if value is not None:
            weighted_sum += weight * max(0.0, min(100.0, value))
            numeric_weight += weight
        if value is not None and status in OBSERVED_STATUSES:
            fixed_sum += weight * max(0.0, min(100.0, value))
        else:
            uncertain_weight += weight
            reasons.append(f"{dimension}: {status if value is not None else 'unavailable'}")

    point = weighted_sum / numeric_weight if numeric_weight else None
    low = fixed_sum
    high = fixed_sum + uncertain_weight * 100.0
    if uncertain_weight == 0:
        confidence = "high"
    elif numeric_weight >= 1.0 and uncertain_weight <= 0.35:
        confidence = "medium"
    elif numeric_weight >= 0.65:
        confidence = "low"
    else:
        confidence = "insufficient"
    return {
        "screening_score": round(point, 1) if point is not None else None,
        "screening_low": round(low, 1),
        "screening_high": round(high, 1),
        "screening_numeric_coverage": round(numeric_weight, 3),
        "screening_confidence": confidence,
        "screening_limitations": "; ".join(reasons) or "All selected components use observed or derived evidence.",
    }


def _event_summary(
    city: str,
    access_rows: Sequence[Mapping[str, Any]],
    recommendation_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    city_access = [row for row in access_rows if str(row.get("city")) == city]
    qualified = [
        row
        for row in city_access
        if bool(
            row.get(
                "capacity_qualified",
                str(row.get("status")) in {"observed", "derived", "scenario"},
            )
        )
    ]
    partial = [row for row in city_access if str(row.get("status")) == "partial"]
    unavailable = [row for row in city_access if str(row.get("status")) == "unavailable"]
    peak_row = max(
        qualified or city_access,
        key=lambda row: _number(row.get("residual_passengers")) or _number(row.get("peak_demand_per_hour")) or 0.0,
        default={},
    )
    match_id = str(peak_row.get("match_id") or "")
    candidates = [
        row
        for row in recommendation_rows
        if str(row.get("city")) == city and str(row.get("match_id")) == match_id
    ]
    eligible_candidates = [row for row in candidates if bool(row.get("evidence_qualified"))]
    recommendation = min(
        eligible_candidates or candidates,
        key=lambda row: (
            _number(row.get("cost_per_passenger")) or float("inf"),
            str(row.get("intervention") or ""),
        ),
        default={},
    )
    return {
        "representative_match_id": match_id or None,
        "qualified_matches": len(qualified),
        "partial_matches": len(partial),
        "unavailable_matches": len(unavailable),
        "peak_demand_pph": _number(peak_row.get("peak_demand_per_hour")),
        "capacity_qualified_gap_pph": (
            _number(peak_row.get("residual_passengers")) if peak_row in qualified else None
        ),
        "top_intervention": recommendation.get("intervention"),
        "top_cost_per_passenger": _number(recommendation.get("cost_per_passenger")),
        "top_net_co2e_kg": _number(recommendation.get("net_co2e_kg")),
        "top_lead_time": recommendation.get("lead_time_band"),
        "top_evidence": recommendation.get("status"),
        "qualified_option_count": len(eligible_candidates),
        "exploratory_option_count": len(candidates) - len(eligible_candidates),
    }


def build_city_comparison(
    metrics: pd.DataFrame,
    access_rows: Sequence[Mapping[str, Any]],
    recommendation_rows: Sequence[Mapping[str, Any]],
    *,
    weights: Mapping[str, float] | None = None,
) -> pd.DataFrame:
    """Return strict rankings and a separate all-city evidence screening table."""

    normalized = normalize_weights(dict(weights) if weights is not None else None)
    rows: list[dict[str, Any]] = []
    for metric in metrics.to_dict("records"):
        city = str(metric["city"])
        screening = _screening_score(metric, normalized)
        strict_rankable = bool(metric.get("rankable"))
        strict_reason = (
            "All selected components use eligible observed or derived evidence."
            if strict_rankable
            else screening["screening_limitations"]
        )
        rows.append(
            {
                "city": city,
                "venue": metric.get("venue"),
                "lat": metric.get("lat"),
                "lon": metric.get("lon"),
                "strict_score": _number(metric.get("score")) if strict_rankable else None,
                "strict_rankable": strict_rankable,
                "strict_exclusion_reason": strict_reason,
                **screening,
                **_event_summary(city, access_rows, recommendation_rows),
            }
        )
    frame = pd.DataFrame(rows)
    strict = frame[frame["strict_rankable"] & frame["strict_score"].notna()].sort_values(
        ["strict_score", "city"], ascending=[False, True]
    )
    strict_ranks = {city: rank for rank, city in enumerate(strict["city"], 1)}
    frame["strict_rank"] = frame["city"].map(strict_ranks).astype("Int64")
    screening = frame[frame["screening_score"].notna()].sort_values(
        ["screening_score", "screening_confidence", "city"], ascending=[False, True, True]
    )
    screening_ranks = {city: rank for rank, city in enumerate(screening["city"], 1)}
    frame["screening_order"] = frame["city"].map(screening_ranks).astype("Int64")
    access_priority = frame[frame["capacity_qualified_gap_pph"].notna()].sort_values(
        ["capacity_qualified_gap_pph", "peak_demand_pph", "city"],
        ascending=[False, False, True],
    )
    access_ranks = {city: rank for rank, city in enumerate(access_priority["city"], 1)}
    frame["access_priority_order"] = frame["city"].map(access_ranks).astype("Int64")
    return frame.sort_values(["strict_rankable", "strict_rank", "screening_order"], ascending=[False, True, True], na_position="last").reset_index(drop=True)
