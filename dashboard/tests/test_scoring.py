import pandas as pd

from dashboard.domain.scoring import build_city_metrics, composite_score, intervention_result, normalize_weights
from dashboard.mobility_platform.contracts import EvidenceStatus, ScenarioConfig


def complete_row(gap=5, gap_status="observed"):
    return {
        "gap_score": gap,
        "gap_status": gap_status,
        "heat_score": 70,
        "heat_status": "derived",
        "uhi_score": 60,
        "uhi_status": "derived",
        "access_score": 80,
        "access_status": "derived",
    }


def test_weights_are_normalized():
    weights = normalize_weights({"gap": 2, "heat": 1, "uhi": 1, "access": 0})
    assert sum(weights.values()) == 1
    assert weights["gap"] == 0.5


def test_valid_floor_gtfs_score_remains_observed():
    score, status, coverage = composite_score(complete_row(gap=5), include_estimates=False)
    assert score is not None
    assert status == EvidenceStatus.DERIVED.value
    assert coverage == 1.0


def test_missing_gap_is_not_silently_estimated():
    row = complete_row(gap=88, gap_status="unavailable")
    score, status, coverage = composite_score(row, include_estimates=False)
    assert score is not None
    assert status == EvidenceStatus.PARTIAL.value
    assert coverage < 1.0


def test_estimates_require_opt_in():
    row = complete_row(gap=88, gap_status="estimated")
    strict_score, strict_status, _ = composite_score(row, include_estimates=False)
    estimated_score, estimated_status, _ = composite_score(row, include_estimates=True)
    assert strict_score is not None
    assert strict_status == EvidenceStatus.PARTIAL.value
    assert estimated_score is not None
    assert estimated_status == EvidenceStatus.ESTIMATED.value


def test_gap_improvement_does_not_reduce_score():
    low, _, _ = composite_score(complete_row(gap=20))
    high, _, _ = composite_score(complete_row(gap=80))
    assert high >= low


def test_zero_intervention_reproduces_zero_delta():
    row = pd.Series({"city": "Dallas", "capacity": 1000, "peak_visitors": 1000, "transit_score": 5})
    result = intervention_result(row, ScenarioConfig(city="Dallas", shuttle_buses_per_hour=0, park_ride_spaces=0, bike_stations=0, pedestrian_upgrade_pct=0))
    assert result.potential_mode_shift == 0
    assert result.vehicle_km_avoided == 0
    assert result.emissions_avoided_kg == 0


def test_partial_evidence_mrs_is_visible_but_not_rankable():
    row = complete_row(gap=88, gap_status="unavailable")
    score, status, coverage = composite_score(row, include_estimates=False)
    assert score is not None
    assert status == EvidenceStatus.PARTIAL.value
    assert coverage < 1.0


def test_city_metrics_expose_explicit_rankability_gate():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame({
        "city": ["Atlanta", "Atlanta"],
        "date": pd.to_datetime(["2024-06-01", "2024-07-01"]),
        "avg_temp_c": [30.0, 31.0],
        "max_temp_c": [35.0, 36.0],
        "min_temp_c": [24.0, 25.0],
        "humidity": [60.0, 65.0],
    })
    uhi = pd.DataFrame({"city": ["Atlanta"], "venue_p90_uhi": [5.0], "venue_points": [12]})
    poi = pd.DataFrame({"city": ["Atlanta"], "category": ["Transit"], "poi_count_1mi": [20]})
    gtfs = {"Atlanta": {"gtfs_transit_score": 5, "score_status": "observed", "total_agency_stops": 20}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs)
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    philadelphia = metrics.loc[metrics["city"] == "Philadelphia"].iloc[0]
    assert bool(atlanta["rankable"])
    assert not bool(philadelphia["rankable"])
    assert philadelphia["score_status"] in {"partial", "unavailable"}


def test_first_last_mile_gap_blends_transit_and_parking_75_25():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 80, "score_status": "observed"}}
    parking = {
        "Atlanta": {
            "status": "derived",
            "facility_count_0_5mi": 10,
            "facility_count_1mi": 20,
            "facility_count_2mi": 30,
        },
    }
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking=parking)
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    # Atlanta is the only city with parking data here, so it's the best-covered
    # host in the cohort and its parking_score normalizes to 100.
    assert atlanta["parking_score"] == 100.0
    # combined_access = 0.75*80 + 0.25*100 = 85 -> gap = 100-85 = 15, gap_score = 85.
    assert atlanta["first_last_mile_gap"] == 15.0
    assert atlanta["gap_score"] == 85.0


def test_first_last_mile_gap_falls_back_to_transit_alone_without_parking_data():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 80, "score_status": "observed"}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={})
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["parking_score"])
    assert atlanta["first_last_mile_gap"] == 20.0
    assert atlanta["gap_score"] == 80.0
