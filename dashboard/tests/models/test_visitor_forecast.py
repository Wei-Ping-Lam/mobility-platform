from __future__ import annotations

import pandas as pd
import pytest

from dashboard.models.visitor_forecast import build_visitor_flow_forecast


def _origins() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"city": "Atlanta", "home_state": "GA", "customer_count": 60, "evidence_status": "derived"},
            {"city": "Atlanta", "home_state": "AL", "customer_count": 20, "evidence_status": "derived"},
            {"city": "Atlanta", "home_state": "CA", "customer_count": 20, "evidence_status": "derived"},
        ]
    )


def _access(*, capacity: int = 8_000, demand: int = 18_000) -> dict[str, object]:
    return {
        "city": "Atlanta",
        "match_id": "ATL-01",
        "peak_demand_per_hour": demand,
        "transit_capacity_base": capacity,
        "network_walk_distance_m": 500,
    }


def _count(rows, label_field: str, label: str, case: str = "base") -> int:
    return next(
        int(row[f"attendees_{case}"])
        for row in rows
        if row[label_field] == label
    )


def test_visitor_forecast_reconciles_origins_modes_and_stage_scenario(
    match_record, movement
) -> None:
    forecast = build_visitor_flow_forecast(
        match_record,
        movement,
        _origins(),
        transit_score=70,
        access=_access(),
    )

    for case, attendance in (
        ("low", movement.attendance_low),
        ("base", movement.attendance_base),
        ("high", movement.attendance_high),
    ):
        assert sum(row[f"attendees_{case}"] for row in forecast["origin_rows"]) == attendance
        assert sum(row[f"attendees_{case}"] for row in forecast["mode_rows"]) == attendance
    assert _count(
        forecast["origin_rows"], "origin_type", "International / unobserved"
    ) == round(movement.attendance_base * 0.20)
    assert forecast["origin_prior_status"] == "context_only"
    assert forecast["validation_status"].startswith("not calibrated")


def test_final_scenario_has_more_international_demand_than_group(
    match_record, movement
) -> None:
    group = build_visitor_flow_forecast(
        match_record,
        movement,
        _origins(),
        transit_score=50,
        access=_access(),
    )
    final_match = {**match_record, "stage": "Final"}
    final = build_visitor_flow_forecast(
        final_match,
        movement,
        _origins(),
        transit_score=50,
        access=_access(),
    )

    assert final["international_share_base"] > group["international_share_base"]
    assert _count(
        final["origin_rows"], "origin_type", "International / unobserved"
    ) > _count(group["origin_rows"], "origin_type", "International / unobserved")


def test_scheduled_transit_scenario_responds_to_readiness_and_capacity(
    match_record, movement
) -> None:
    constrained = build_visitor_flow_forecast(
        match_record,
        movement,
        _origins(),
        transit_score=10,
        access=_access(capacity=0),
    )
    supported = build_visitor_flow_forecast(
        match_record,
        movement,
        _origins(),
        transit_score=90,
        access=_access(capacity=18_000),
    )

    assert _count(
        supported["mode_rows"], "mode", "Scheduled transit"
    ) > _count(constrained["mode_rows"], "mode", "Scheduled transit")


def test_missing_commercial_origins_uses_visible_fallback(match_record, movement) -> None:
    forecast = build_visitor_flow_forecast(
        match_record,
        movement,
        pd.DataFrame(),
        transit_score=None,
        access=_access(),
    )

    assert forecast["origin_prior_status"] == "unavailable"
    assert forecast["origin_prior_coverage_pct"] == 0
    assert sum(row["attendees_base"] for row in forecast["origin_rows"]) == movement.attendance_base


def test_visitor_forecast_rejects_cross_match_access(match_record, movement) -> None:
    mismatched_access = {**_access(), "match_id": "OTHER"}
    with pytest.raises(ValueError, match="access result must match"):
        build_visitor_flow_forecast(
            match_record,
            movement,
            _origins(),
            transit_score=70,
            access=mismatched_access,
        )
