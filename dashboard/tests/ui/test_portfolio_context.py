import pandas as pd

from dashboard.ui.portfolio.context import _furthest_stage_label, _with_parking_evidence, build_city_hourly_movement


def test_build_city_hourly_movement_averages_across_a_citys_matches() -> None:
    artifacts = {
        "movement_scenarios": [
            {
                "city": "Atlanta",
                "match_id": "M001",
                "hourly_rows": [
                    {"hours_from_kickoff": -1, "arrivals_base": 10_000, "departures_base": 0},
                    {"hours_from_kickoff": 2, "arrivals_base": 0, "departures_base": 8_000},
                ],
            },
            {
                "city": "Atlanta",
                "match_id": "M002",
                "hourly_rows": [
                    {"hours_from_kickoff": -1, "arrivals_base": 6_000, "departures_base": 0},
                    {"hours_from_kickoff": 2, "arrivals_base": 0, "departures_base": 4_000},
                ],
            },
            {
                "city": "Seattle",
                "match_id": "M003",
                "hourly_rows": [
                    {"hours_from_kickoff": -1, "arrivals_base": 5_000, "departures_base": 0},
                ],
            },
        ]
    }

    result = build_city_hourly_movement(artifacts)

    atlanta = result[result["city"] == "Atlanta"].set_index("hours_from_kickoff")
    assert atlanta.loc[-1.0, "avg_arrivals_base"] == 8_000
    assert atlanta.loc[2.0, "avg_departures_base"] == 6_000
    assert atlanta["match_count"].iloc[0] == 2

    seattle = result[result["city"] == "Seattle"]
    assert seattle["match_count"].iloc[0] == 1
    assert seattle["avg_arrivals_base"].iloc[0] == 5_000


def test_build_city_hourly_movement_handles_empty_artifacts() -> None:
    result = build_city_hourly_movement({})

    assert list(result.columns) == [
        "city",
        "hours_from_kickoff",
        "avg_arrivals_base",
        "avg_departures_base",
        "match_count",
    ]
    assert result.empty


def test_furthest_stage_label_picks_the_deepest_real_match_not_the_last_in_list():
    forecasts = [
        {"stage": "Quarter-final"},
        {"stage": "Group"},
        {"stage": "Round of 16"},
    ]
    assert _furthest_stage_label(forecasts) == "Quarterfinal"


def test_furthest_stage_label_ties_semifinal_and_bronze_final():
    assert _furthest_stage_label([{"stage": "Bronze Final"}]) == "3rd place"
    assert _furthest_stage_label([{"stage": "Semi-final"}]) == "Semifinal"


def test_furthest_stage_label_final_outranks_everything():
    forecasts = [{"stage": "Semi-final"}, {"stage": "Final"}, {"stage": "Group"}]
    assert _furthest_stage_label(forecasts) == "Final"


def test_furthest_stage_label_handles_no_forecasts():
    assert _furthest_stage_label([]) == "Not available"


def test_with_parking_evidence_attaches_real_counts_and_nulls_missing_cities():
    frame = pd.DataFrame({"city": ["Atlanta", "Seattle"]})
    parking = {
        "Atlanta": {
            "status": "derived",
            "facility_count_0_5mi": 66,
            "facility_count_1mi": 234,
            "facility_count_2mi": 710,
            "tagged_capacity_0_5mi": 1_348,
            "tagged_capacity_1mi": 4_435,
            "tagged_capacity_2mi": 8_754,
            "facilities_with_capacity_tag": 122,
            "total_facilities": 776,
        },
        "Seattle": {"status": "unavailable"},
    }

    result = _with_parking_evidence(frame, parking)

    atlanta = result[result["city"] == "Atlanta"].iloc[0]
    assert atlanta["parking_count_1mi"] == 234
    assert atlanta["parking_tagged_capacity_1mi"] == 4_435
    assert atlanta["parking_status"] == "derived"

    seattle = result[result["city"] == "Seattle"].iloc[0]
    assert pd.isna(seattle["parking_count_1mi"])
    assert seattle["parking_status"] == "unavailable"


def test_with_parking_evidence_handles_a_missing_snapshot_entirely():
    frame = pd.DataFrame({"city": ["Atlanta", "Seattle"]})

    result = _with_parking_evidence(frame, {})

    assert result["parking_count_1mi"].isna().all()
    assert (result["parking_status"] == "unavailable").all()
