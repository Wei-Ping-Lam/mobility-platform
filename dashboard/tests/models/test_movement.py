from __future__ import annotations

import pandas as pd
import pytest

from dashboard.mobility_platform.contracts import EvidenceStatus
from dashboard.models.movement import (
    PLANNING_SCENARIO,
    VALIDATED_BASELINE,
    baseline_validation_status,
    build_movement_scenario,
    generate_movement_scenarios,
    movement_hourly_frame,
    validation_label,
)


def _total(scenario, field: str) -> int:
    return sum(int(row[field]) for row in scenario.hourly_rows)


def _peak(scenario) -> int:
    return max(int(row["total_movement_base"]) for row in scenario.hourly_rows)


def test_match_scenario_reconciles_every_attendance_total(match_record):
    scenario = build_movement_scenario(
        match_record,
        {"attendance_low": 60_351, "attendance_base": 67_453, "attendance_high": 70_999},
    )

    assert scenario.status == EvidenceStatus.SCENARIO
    for level, attendance in (
        ("low", scenario.attendance_low),
        ("base", scenario.attendance_base),
        ("high", scenario.attendance_high),
    ):
        assert _total(scenario, f"arrivals_{level}") == attendance
        assert _total(scenario, f"departures_{level}") == attendance


def test_timestamps_are_match_specific_and_departures_follow_match_end(match_record):
    scenario = build_movement_scenario(
        match_record,
        {"attendance_low": 100, "attendance_base": 100, "attendance_high": 100},
        arrival_profile={-1: 1.0},
        departure_profile={0: 1.0},
        match_duration_min=120,
    )
    rows = list(scenario.hourly_rows)

    assert rows[0]["timestamp_local"] == "2026-06-15T14:00:00-04:00"
    assert rows[0]["arrivals_base"] == 100
    assert rows[1]["timestamp_local"] == "2026-06-15T17:00:00-04:00"
    assert rows[1]["departures_base"] == 100


def test_profile_dataframe_is_normalized_and_disclosed(match_record):
    profile = pd.DataFrame({"relative_hour": [-2, -1], "share": [1.0, 3.0]})
    scenario = build_movement_scenario(
        match_record,
        {"attendance_low": 100, "attendance_base": 100, "attendance_high": 100},
        arrival_profile=profile,
    )

    assert any("normalized" in assumption for assumption in scenario.assumptions)
    arrivals = [row["arrivals_base"] for row in scenario.hourly_rows if row["arrivals_base"]]
    assert arrivals == [25, 75]


def test_empty_match_table_has_zero_event_demand():
    assert generate_movement_scenarios(pd.DataFrame()) == []


def test_batch_adapter_accepts_a_single_match_dict(match_record):
    scenarios = generate_movement_scenarios(match_record)
    assert len(scenarios) == 1
    assert scenarios[0].match_id == "ATL-01"


def test_zero_attendance_has_zero_hourly_demand(match_record):
    scenario = build_movement_scenario(
        match_record,
        {"attendance_low": 0, "attendance_base": 0, "attendance_high": 0},
    )
    assert _peak(scenario) == 0


def test_higher_attendance_cannot_reduce_peak_demand(match_record):
    lower = build_movement_scenario(
        match_record,
        {"attendance_low": 10_000, "attendance_base": 20_000, "attendance_high": 30_000},
    )
    higher = build_movement_scenario(
        match_record,
        {"attendance_low": 20_000, "attendance_base": 30_000, "attendance_high": 40_000},
    )
    assert _peak(higher) >= _peak(lower)


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (
            [
                {"holdout_year": 2023, "outperforms_seasonal_naive": True},
                {"holdout_year": 2024, "outperforms_seasonal_naive": True},
            ],
            VALIDATED_BASELINE,
        ),
        ([{"holdout_year": 2023, "outperforms_seasonal_naive": True}], PLANNING_SCENARIO),
        (
            [
                {"holdout_year": 2023, "outperforms_seasonal_naive": True},
                {"holdout_year": 2024, "outperforms_seasonal_naive": False},
            ],
            PLANNING_SCENARIO,
        ),
    ],
)
def test_validation_requires_both_holdout_wins(rows, expected):
    assert validation_label(rows) == expected


def test_public_validation_helper_uses_fixed_2023_2024_gate():
    rows = [
        {"holdout_year": 2023, "outperforms_seasonal_naive": True},
        {"holdout_year": 2024, "outperforms_seasonal_naive": True},
    ]
    assert baseline_validation_status(rows) == VALIDATED_BASELINE


def test_batch_applies_city_validation_without_changing_scenario_status(match_record):
    validation = pd.DataFrame(
        {
            "city": ["Atlanta", "Atlanta"],
            "holdout_year": [2023, 2024],
            "outperforms_seasonal_naive": [True, True],
        }
    )
    scenarios = generate_movement_scenarios(pd.DataFrame([match_record]), validation=validation)

    assert scenarios[0].status == EvidenceStatus.SCENARIO
    assert any("validated baseline" in assumption for assumption in scenarios[0].assumptions)


def test_hourly_frame_preserves_contract_identity(movement):
    frame = movement_hourly_frame(movement)

    assert set(frame["city"]) == {"Atlanta"}
    assert set(frame["match_id"]) == {"ATL-01"}
    assert set(frame["status"]) == {"scenario"}


@pytest.mark.parametrize(
    "attendance",
    [
        {"attendance_low": 20, "attendance_base": 10, "attendance_high": 30},
        {"attendance_low": 10, "attendance_base": 20, "attendance_high": 80_000},
        {"occupancy_low": -0.1, "occupancy_base": 0.9, "occupancy_high": 1.0},
    ],
)
def test_invalid_attendance_assumptions_are_rejected(match_record, attendance):
    with pytest.raises(ValueError):
        build_movement_scenario(match_record, attendance)


def test_partial_explicit_attendance_is_rejected(match_record):
    with pytest.raises(ValueError, match="low, base, and high"):
        build_movement_scenario(match_record, {"attendance_base": 60_000})


def test_fractional_profile_hours_are_rejected(match_record):
    with pytest.raises(ValueError, match="whole hours"):
        build_movement_scenario(match_record, arrival_profile={-1.5: 1.0})


def test_kickoff_requires_explicit_local_offset(match_record):
    with pytest.raises(ValueError, match="UTC offset"):
        build_movement_scenario({**match_record, "kickoff_local": "2026-06-15T15:00:00"})


def test_nonfinite_assumptions_are_rejected(match_record):
    with pytest.raises(ValueError, match="nonnegative"):
        build_movement_scenario(match_record, arrival_profile={-1: float("inf")})
