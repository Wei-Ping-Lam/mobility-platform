"""Portfolio-level view model for the all-city landing experience."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from dashboard.domain.comparison import build_city_comparison

PACKAGE_NAMES = ("Baseline", "Operational Package", "Capital Package")


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if pd.notna(parsed) else None


def _recommendation(
    city: str,
    match_id: str,
    intervention: object,
    rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    candidates = [
        row
        for row in rows
        if str(row.get("city")) == city
        and str(row.get("match_id")) == match_id
        and str(row.get("intervention")) == str(intervention)
    ]
    return min(
        candidates,
        key=lambda row: (
            _number(row.get("cost_per_passenger")) or float("inf"),
            str(row.get("intervention") or ""),
        ),
        default={},
    )


def _package_outcome(
    city: str,
    match_id: str,
    package_name: str,
    rows: Sequence[Mapping[str, Any]],
) -> Mapping[str, Any]:
    for row in rows:
        package = row.get("package", {})
        name = package.get("name") if isinstance(package, Mapping) else row.get("name")
        if (
            str(row.get("city")) == city
            and str(row.get("match_id")) == match_id
            and str(name) == package_name
        ):
            return row
    return {}


def _option_set(
    city: str,
    match_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    qualified: bool,
) -> str:
    names = sorted(
        {
            str(row.get("intervention"))
            for row in rows
            if str(row.get("city")) == city
            and str(row.get("match_id")) == match_id
            and bool(row.get("evidence_qualified", False)) is qualified
            and row.get("intervention")
        }
    )
    return "; ".join(names) if names else "None"


@dataclass(frozen=True)
class PortfolioSummary:
    city_count: int
    match_count: int
    strict_rankable_cities: int
    access_ranked_cities: int
    cities_with_qualified_options: int
    largest_access_gap_pph: float | None


def build_portfolio_overview(
    metrics: pd.DataFrame,
    access_rows: Sequence[Mapping[str, Any]],
    recommendation_rows: Sequence[Mapping[str, Any]],
    outcome_rows: Sequence[Mapping[str, Any]],
    *,
    weights: Mapping[str, float],
    package_name: str = "Operational Package",
) -> pd.DataFrame:
    """Build one deterministic row per city for overview and comparison views."""

    if package_name not in PACKAGE_NAMES:
        raise ValueError(f"Unknown overview package: {package_name}")
    comparison = build_city_comparison(
        metrics,
        access_rows,
        recommendation_rows,
        weights=weights,
    ).copy()
    additions: list[dict[str, Any]] = []
    for row in comparison.to_dict("records"):
        city = str(row["city"])
        match_id = str(row.get("representative_match_id") or "")
        recommendation = _recommendation(city, match_id, row.get("top_intervention"), recommendation_rows)
        outcome = _package_outcome(city, match_id, package_name, outcome_rows)
        package_cost = _number(outcome.get("cost_base"))
        package_gap = _number(outcome.get("gap_resolved_passengers"))
        additions.append(
            {
                "top_cost_low": _number(recommendation.get("cost_low")),
                "top_cost_base": _number(recommendation.get("cost_base")),
                "top_cost_high": _number(recommendation.get("cost_high")),
                "top_option_qualified": bool(recommendation.get("evidence_qualified", False)),
                "top_evidence_quality": str(recommendation.get("evidence_quality") or "unavailable"),
                "qualified_interventions": _option_set(city, match_id, recommendation_rows, qualified=True),
                "exploratory_interventions": _option_set(city, match_id, recommendation_rows, qualified=False),
                "package_name": package_name,
                "package_status": str(outcome.get("status") or "unavailable"),
                "package_gap_resolved": package_gap,
                "package_cost_low": _number(outcome.get("cost_low")),
                "package_cost_base": _number(outcome.get("cost_base")),
                "package_cost_high": _number(outcome.get("cost_high")),
                "package_net_co2e_low": _number(outcome.get("net_co2e_kg_low")),
                "package_net_co2e_base": _number(outcome.get("net_co2e_kg_base")),
                "package_net_co2e_high": _number(outcome.get("net_co2e_kg_high")),
                "package_vehicle_trips_base": _number(outcome.get("venue_vehicle_trips_base")),
                "package_cost_per_passenger": (
                    package_cost / package_gap
                    if package_cost is not None and package_gap is not None and package_gap > 0
                    else None
                ),
            }
        )
    additions_frame = pd.DataFrame(additions, index=comparison.index)
    return pd.concat([comparison, additions_frame], axis=1)


def portfolio_summary(frame: pd.DataFrame, match_count: int) -> PortfolioSummary:
    """Summarize coverage without aggregating incompatible match scenarios."""

    gap = pd.to_numeric(frame.get("capacity_qualified_gap_pph"), errors="coerce")
    return PortfolioSummary(
        city_count=len(frame),
        match_count=int(match_count),
        strict_rankable_cities=int(frame.get("strict_rankable", pd.Series(dtype=bool)).fillna(False).sum()),
        access_ranked_cities=int(frame.get("access_priority_order", pd.Series(dtype=float)).notna().sum()),
        cities_with_qualified_options=int((pd.to_numeric(frame.get("qualified_option_count"), errors="coerce") > 0).sum()),
        largest_access_gap_pph=float(gap.max()) if not gap.dropna().empty else None,
    )
