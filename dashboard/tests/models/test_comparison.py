from __future__ import annotations

import pandas as pd

from dashboard.domain.comparison import build_city_comparison
from dashboard.domain.scoring import DEFAULT_WEIGHTS


def _metrics() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "city": "Complete",
                "venue": "A",
                "score": 70,
                "rankable": True,
                "transit_score": 80,
                "transit_status": "observed",
                "heat_score": 60,
                "heat_status": "derived",
                "uhi_score": 65,
                "uhi_status": "derived",
                "access_score": 70,
                "access_status": "derived",
            },
            {
                "city": "Partial",
                "venue": "B",
                "score": 75,
                "rankable": False,
                "transit_score": 90,
                "transit_status": "partial",
                "heat_score": 70,
                "heat_status": "derived",
                "uhi_score": 75,
                "uhi_status": "derived",
                "access_score": 80,
                "access_status": "derived",
            },
            {
                "city": "Missing",
                "venue": "C",
                "score": 50,
                "rankable": False,
                "transit_score": None,
                "transit_status": "unavailable",
                "heat_score": 50,
                "heat_status": "derived",
                "uhi_score": 50,
                "uhi_status": "derived",
                "access_score": 50,
                "access_status": "derived",
            },
        ]
    )


def test_comparison_keeps_strict_ranking_separate_from_all_city_screening():
    frame = build_city_comparison(_metrics(), [], [], weights=DEFAULT_WEIGHTS["balanced"])
    assert len(frame) == 3
    assert frame.loc[frame["city"] == "Complete", "strict_rank"].iloc[0] == 1
    assert frame.loc[frame["city"] == "Partial", "strict_rank"].isna().all()
    assert frame["screening_score"].notna().all()
    assert set(frame["screening_order"].dropna().astype(int)) == {1, 2, 3}


def test_partial_and_missing_components_create_honest_ranges_not_silent_zeroes():
    frame = build_city_comparison(_metrics(), [], [], weights=DEFAULT_WEIGHTS["balanced"]).set_index("city")
    assert frame.loc["Complete", "screening_low"] == frame.loc["Complete", "screening_high"]
    assert frame.loc["Partial", "screening_low"] < frame.loc["Partial", "screening_high"]
    assert frame.loc["Missing", "screening_low"] < frame.loc["Missing", "screening_high"]
    assert frame.loc["Partial", "screening_confidence"] != "high"
    assert "transit" in frame.loc["Missing", "strict_exclusion_reason"]


def test_event_summary_uses_only_the_representative_match_recommendations():
    access = [
        {"city": "Complete", "match_id": "A-1", "status": "scenario", "peak_demand_per_hour": 1000, "residual_passengers": 500},
        {"city": "Complete", "match_id": "A-2", "status": "scenario", "peak_demand_per_hour": 1400, "residual_passengers": 900},
    ]
    recommendations = [
        {"city": "Complete", "match_id": "A-1", "intervention": "Wrong match", "gap_resolved_passengers": 500, "cost_per_passenger": 1},
        {"city": "Complete", "match_id": "A-2", "intervention": "Right match", "gap_resolved_passengers": 700, "cost_per_passenger": 2},
    ]
    frame = build_city_comparison(_metrics().iloc[:1], access, recommendations).iloc[0]
    assert frame["representative_match_id"] == "A-2"
    assert frame["top_intervention"] == "Right match"
    assert frame["qualified_matches"] == 2


def test_event_summary_exposes_objective_specific_choices_instead_of_one_winner():
    access = [
        {
            "city": "Complete",
            "match_id": "A-1",
            "status": "scenario",
            "capacity_qualified": True,
            "peak_demand_per_hour": 1400,
            "residual_passengers": 900,
        }
    ]
    recommendations = [
        {
            "city": "Complete",
            "match_id": "A-1",
            "intervention": "Shuttle service",
            "gap_resolved_passengers": 300,
            "cost_per_passenger": 10,
            "net_co2e_kg": 100,
            "evidence_qualified": True,
        },
        {
            "city": "Complete",
            "match_id": "A-1",
            "intervention": "Added transit frequency",
            "gap_resolved_passengers": 600,
            "cost_per_passenger": 12,
            "net_co2e_kg": 250,
            "evidence_qualified": True,
        },
    ]

    row = build_city_comparison(_metrics().iloc[:1], access, recommendations).iloc[0]

    assert row["lowest_cost_intervention"] == "Shuttle service"
    assert row["fastest_intervention"] == "Shuttle service"
    assert row["greatest_relief_intervention"] == "Added transit frequency"
    assert row["greatest_climate_intervention"] == "Added transit frequency"


def test_priority_screen_matches_a_zero_service_bottleneck() -> None:
    access = [
        {
            "city": "Complete",
            "match_id": "A-1",
            "status": "scenario",
            "capacity_qualified": True,
            "peak_demand_per_hour": 1400,
            "transit_capacity_base": 0,
            "residual_passengers": 1400,
        }
    ]
    recommendations = [
        {
            "city": "Complete",
            "match_id": "A-1",
            "intervention": "Shuttle service",
            "gap_resolved_passengers": 300,
            "cost_per_passenger": 10,
            "evidence_qualified": True,
        },
        {
            "city": "Complete",
            "match_id": "A-1",
            "intervention": "Added transit frequency",
            "gap_resolved_passengers": 600,
            "cost_per_passenger": 2,
            "evidence_qualified": False,
        },
    ]

    row = build_city_comparison(_metrics().iloc[:1], access, recommendations).iloc[0]

    assert row["top_intervention"] == "Shuttle service"
    assert row["lowest_cost_intervention"] == "Shuttle service"
    assert "No serving scheduled capacity" in row["priority_reason"]


def test_access_priority_orders_capacity_qualified_physical_gaps_for_all_cities():
    access = [
        {"city": "Complete", "match_id": "A-1", "capacity_qualified": True, "peak_demand_per_hour": 1200, "residual_passengers": 900},
        {"city": "Partial", "match_id": "B-1", "capacity_qualified": True, "peak_demand_per_hour": 1000, "residual_passengers": 400},
        {"city": "Missing", "match_id": "C-1", "capacity_qualified": True, "peak_demand_per_hour": 1100, "residual_passengers": 700},
    ]

    frame = build_city_comparison(_metrics(), access, []).set_index("city")

    assert frame.loc["Complete", "access_priority_order"] == 1
    assert frame.loc["Missing", "access_priority_order"] == 2
    assert frame.loc["Partial", "access_priority_order"] == 3
