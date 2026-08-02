from __future__ import annotations

import pandas as pd
import pytest

from dashboard.mobility_platform.contracts import EvidenceStatus
from dashboard.models.access import (
    access_friction_index,
    access_results_frame,
    build_access_gap_result,
)
from dashboard.models.movement import build_movement_scenario


def test_access_gap_exposes_peak_capacity_and_residual(movement, event_service, walk_metrics):
    result = build_access_gap_result(
        movement,
        event_service,
        walk_metrics,
        service_span_after_match_min=180,
    )

    assert result.status == EvidenceStatus.SCENARIO
    assert result.peak_demand_per_hour == 30_353
    assert result.transit_capacity_low == 4_000
    assert result.transit_capacity_base == 5_600
    assert result.transit_capacity_high == 7_200
    assert result.residual_passengers == 24_753
    assert result.network_walk_distance_m == 620
    assert result.service_span_after_match_min == 180
    assert result.route_heat_exposure_c == 33


def test_access_builder_accepts_single_service_dict(movement, event_service, walk_metrics):
    result = build_access_gap_result(movement.to_dict(), event_service.iloc[0].to_dict(), walk_metrics)
    assert result.transit_capacity_base == 5_600


def test_more_capacity_cannot_increase_gap(movement, event_service, walk_metrics):
    lower = build_access_gap_result(movement, event_service, walk_metrics)
    expanded = event_service.assign(departures_per_hour=16)
    higher = build_access_gap_result(movement, expanded, walk_metrics)

    assert higher.residual_passengers <= lower.residual_passengers


def test_higher_attendance_cannot_reduce_gap(match_record, event_service, walk_metrics):
    low = build_movement_scenario(
        match_record,
        {"attendance_low": 10_000, "attendance_base": 20_000, "attendance_high": 30_000},
    )
    high = build_movement_scenario(
        match_record,
        {"attendance_low": 20_000, "attendance_base": 40_000, "attendance_high": 60_000},
    )

    low_gap = build_access_gap_result(low, event_service, walk_metrics)
    high_gap = build_access_gap_result(high, event_service, walk_metrics)
    assert high_gap.residual_passengers >= low_gap.residual_passengers


def test_unavailable_transit_remains_unavailable(movement, walk_metrics):
    unavailable = pd.DataFrame([{"status": "unavailable"}])
    result = build_access_gap_result(movement, unavailable, walk_metrics)
    friction = access_friction_index(result)

    assert result.status == EvidenceStatus.UNAVAILABLE
    assert friction["status"] == "unavailable"
    assert friction["friction_index"] is None
    assert any("sentinels" in assumption for assumption in result.assumptions)


def test_valid_zero_departures_are_not_treated_as_missing(movement, event_service, walk_metrics):
    result = build_access_gap_result(
        movement,
        event_service.assign(departures_per_hour=0),
        walk_metrics,
    )

    assert result.status == EvidenceStatus.SCENARIO
    assert result.transit_capacity_base == 0
    assert result.residual_passengers == result.peak_demand_per_hour


def test_network_distance_cannot_be_shorter_than_straight_line(movement, event_service):
    with pytest.raises(ValueError, match="network walk distance"):
        build_access_gap_result(
            movement,
            event_service,
            {
                "network_walk_distance_m": 400,
                "straight_line_distance_m": 500,
                "route_heat_exposure_c": 30,
                "status": "derived",
            },
        )


def test_one_metre_distance_tolerance_allows_numeric_noise(movement, event_service):
    result = build_access_gap_result(
        movement,
        event_service,
        {
            "network_walk_distance_m": 499.5,
            "straight_line_distance_m": 500,
            "route_heat_exposure_c": 30,
            "status": "derived",
        },
    )
    assert result.network_walk_distance_m == 499.5


def test_longer_walk_and_higher_heat_cannot_improve_friction(movement, event_service, walk_metrics):
    baseline = build_access_gap_result(movement, event_service, walk_metrics)
    longer = build_access_gap_result(
        movement,
        event_service,
        {**walk_metrics, "network_walk_distance_m": 1_200},
    )
    hotter = build_access_gap_result(
        movement,
        event_service,
        {**walk_metrics, "route_heat_exposure_c": 38},
    )

    base_index = access_friction_index(baseline)["friction_index"]
    assert access_friction_index(longer)["friction_index"] >= base_index
    assert access_friction_index(hotter)["friction_index"] >= base_index


def test_missing_optional_metric_is_partial_and_weights_are_transparent(movement, event_service):
    result = build_access_gap_result(
        movement,
        event_service,
        {"network_walk_distance_m": 600, "straight_line_distance_m": 500, "status": "derived"},
        service_span_after_match_min=180,
    )
    friction = access_friction_index(result)

    assert result.status == EvidenceStatus.PARTIAL
    assert friction["status"] == "partial"
    assert "route_heat" not in friction["components"]
    assert sum(friction["effective_weights"].values()) == pytest.approx(1.0, abs=1e-5)


def test_peak_hour_and_direction_filter_service_rows(match_record, walk_metrics):
    movement = build_movement_scenario(
        match_record,
        {"attendance_low": 100, "attendance_base": 100, "attendance_high": 100},
        arrival_profile={-1: 1.0},
        departure_profile={0: 1.0},
    )
    service = pd.DataFrame(
        [
            {
                "hour_start_local": "2026-06-15T14:00:00-04:00",
                "direction": "arrival",
                "departures_per_hour": 2,
                "vehicle_capacity_low": 10,
                "vehicle_capacity_base": 20,
                "vehicle_capacity_high": 30,
                "status": "observed",
            },
            {
                "hour_start_local": "2026-06-15T14:00:00-04:00",
                "direction": "departure",
                "departures_per_hour": 100,
                "vehicle_capacity_low": 10,
                "vehicle_capacity_base": 20,
                "vehicle_capacity_high": 30,
                "status": "observed",
            },
        ]
    )

    result = build_access_gap_result(
        movement,
        service,
        walk_metrics,
        service_span_after_match_min=180,
    )
    assert result.transit_capacity_base == 40


def test_access_table_can_include_optional_friction(movement, event_service, walk_metrics):
    result = build_access_gap_result(movement, event_service, walk_metrics)
    frame = access_results_frame(result, include_friction=True)

    assert frame.loc[0, "match_id"] == "ATL-01"
    assert 0 <= frame.loc[0, "friction_index"] <= 100


def test_capacity_ranges_must_be_ordered(movement, event_service, walk_metrics):
    invalid = event_service.assign(
        vehicle_capacity_low=800,
        vehicle_capacity_base=700,
        vehicle_capacity_high=600,
    )
    with pytest.raises(ValueError, match="ordered"):
        build_access_gap_result(movement, invalid, walk_metrics)


def test_empty_custom_friction_weights_are_rejected(movement, event_service, walk_metrics):
    result = build_access_gap_result(movement, event_service, walk_metrics)
    with pytest.raises(ValueError, match="exactly"):
        access_friction_index(result, weights={})


def test_nonfinite_walk_metrics_are_rejected(movement, event_service, walk_metrics):
    with pytest.raises(ValueError, match="finite"):
        build_access_gap_result(
            movement,
            event_service,
            {**walk_metrics, "network_walk_distance_m": float("inf")},
        )


def test_invalid_event_hours_do_not_become_peak_capacity(movement, event_service, walk_metrics):
    result = build_access_gap_result(
        movement,
        event_service.assign(hour_start_local="not-a-time"),
        walk_metrics,
    )
    assert result.status == EvidenceStatus.UNAVAILABLE
    assert result.transit_capacity_base == 0
