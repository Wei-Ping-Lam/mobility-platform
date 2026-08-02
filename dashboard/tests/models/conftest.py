from __future__ import annotations

import pandas as pd
import pytest

from dashboard.models.movement import build_movement_scenario


@pytest.fixture
def match_record() -> dict[str, object]:
    return {
        "match_id": "ATL-01",
        "city": "Atlanta",
        "venue": "Mercedes-Benz Stadium",
        "kickoff_local": "2026-06-15T15:00:00-04:00",
        "stage": "group",
        "capacity": 71_000,
    }


@pytest.fixture
def movement(match_record):
    return build_movement_scenario(
        match_record,
        {"attendance_low": 60_350, "attendance_base": 67_450, "attendance_high": 71_000},
    )


@pytest.fixture
def event_service() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "mode": "rail",
                "direction": "both",
                "departures_per_hour": 8,
                "vehicle_capacity_low": 500,
                "vehicle_capacity_base": 700,
                "vehicle_capacity_high": 900,
                "service_span_after_match_min": 180,
                "status": "observed",
            }
        ]
    )


@pytest.fixture
def walk_metrics() -> dict[str, object]:
    return {
        "network_walk_distance_m": 620.0,
        "straight_line_distance_m": 500.0,
        "route_heat_exposure_c": 33.0,
        "status": "derived",
    }
