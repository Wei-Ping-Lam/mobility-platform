import pandas as pd

from dashboard.domain.scoring import build_city_metrics, composite_score, intervention_result, normalize_weights
from dashboard.mobility_platform.contracts import EvidenceStatus, ScenarioConfig


def complete_row(gap=5, gap_status="observed"):
    return {
        "gap_score": gap,
        "gap_status": gap_status,
        "heat_score": 70,
        "heat_status": "derived",
        "access_score": 80,
        "access_status": "derived",
        "traffic_score": 60,
        "traffic_status": "derived",
    }


def test_weights_are_normalized():
    weights = normalize_weights({"gap": 2, "heat": 1, "access": 1, "traffic": 0})
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
    # No feed_status/event_window_departures and no benchmarks passed, so
    # transit_access_score falls back to transit_score alone.
    assert atlanta["transit_access_score"] == 80.0
    assert atlanta["first_last_mile_gap"] == 20.0
    assert atlanta["gap_score"] == 80.0


def test_transit_access_blends_density_frequency_and_benchmark_evidence():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {
        "Atlanta": {
            "gtfs_transit_score": 80,
            "score_status": "observed",
            "feed_status": "observed",
            "event_window_departures": 999,
        },
    }
    benchmarks = {"Atlanta": {"dedicated_service_evidence": {"tier": 100}}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={}, benchmarks=benchmarks)
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    # Atlanta is the only city with real event-window departures, so it's its
    # own normalization ceiling: frequency_score = log1p(999)/log1p(999) = 100.
    assert atlanta["frequency_score"] == 100.0
    assert atlanta["benchmark_capacity_score"] == 100.0
    # No walking_networks passed, so pedestrian is unavailable and its 15%
    # weight drops: transit_access = (0.3*80 + 0.2*100 + 0.35*100) / 0.85 = 92.9.
    assert atlanta["transit_access_score"] == 92.9
    assert atlanta["first_last_mile_gap"] == 7.1
    assert atlanta["gap_score"] == 92.9


def test_transit_access_renormalizes_when_frequency_is_missing():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    # No feed_status/event_window_departures -> frequency stays unavailable,
    # so its 20% weight is dropped rather than treated as a zero. No
    # walking_networks passed either, so pedestrian's 15% also drops.
    gtfs = {"Atlanta": {"gtfs_transit_score": 80, "score_status": "observed"}}
    benchmarks = {"Atlanta": {"dedicated_service_evidence": {"tier": 100}}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={}, benchmarks=benchmarks)
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["frequency_score"])
    assert atlanta["benchmark_capacity_score"] == 100.0
    # transit_access = (0.3*80 + 0.35*100) / (0.3 + 0.35) = 59 / 0.65 = 90.8.
    assert atlanta["transit_access_score"] == 90.8


def test_transit_access_credits_real_pedestrian_infrastructure_evidence():
    # A host with a real, working dedicated service that's geographically far
    # from the venue (so transit/frequency read near-zero) should still get
    # real credit from benchmark evidence and pedestrian infrastructure,
    # rather than being underscored purely on radius-based density/frequency.
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Dallas": {"gtfs_transit_score": 1, "score_status": "observed", "feed_status": "observed", "event_window_departures": 0}}
    benchmarks = {"Dallas": {"dedicated_service_evidence": {"tier": 100}}}
    walking_networks = {"Dallas": {"detour_ratio": 1.0, "crossing_tag_coverage_pct": 10.0}}
    metrics = build_city_metrics(
        visits, weather, uhi, poi, gtfs, parking={}, benchmarks=benchmarks, walking_networks=walking_networks
    )
    dallas = metrics.loc[metrics["city"] == "Dallas"].iloc[0]
    assert dallas["pedestrian_infrastructure_score"] == 100.0
    # transit_access = 0.3*1 + 0.2*0 + 0.35*100 + 0.15*100 = 0.3 + 0 + 35 + 15 = 50.3.
    assert dallas["transit_access_score"] == 50.3


def test_frequency_score_normalizes_log_scale_against_the_best_covered_host():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {
        "Atlanta": {"gtfs_transit_score": 50, "score_status": "observed", "feed_status": "observed", "event_window_departures": 999},
        "Seattle": {"gtfs_transit_score": 50, "score_status": "observed", "feed_status": "observed", "event_window_departures": 99},
        "Boston": {"gtfs_transit_score": 50, "score_status": "observed", "feed_status": "observed", "event_window_departures": 0},
    }
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={})
    by_city = metrics.set_index("city")
    assert by_city.loc["Atlanta", "frequency_score"] == 100.0
    # log1p(99) / log1p(999) * 100, rounded to 1 decimal.
    assert by_city.loc["Seattle", "frequency_score"] == 66.7
    # A real, observed zero (not missing data) scores 0, not unavailable.
    assert by_city.loc["Boston", "frequency_score"] == 0.0


def test_parking_score_only_counts_the_within_half_mile_ring():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {
        "Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"},
        "Seattle": {"gtfs_transit_score": 50, "score_status": "observed"},
    }
    parking = {
        # Far more 1mi/2mi facilities, but fewer within 0.5mi - would have won
        # under the old 10/5/2-weighted blend, but shouldn't now.
        "Atlanta": {"status": "derived", "facility_count_0_5mi": 10, "facility_count_1mi": 1000, "facility_count_2mi": 1000},
        "Seattle": {"status": "derived", "facility_count_0_5mi": 20, "facility_count_1mi": 5, "facility_count_2mi": 5},
    }
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking=parking)
    by_city = metrics.set_index("city")
    assert by_city.loc["Seattle", "parking_score"] == 100.0
    assert by_city.loc["Atlanta", "parking_score"] == 50.0


def test_sustainability_score_blends_parking_electrification_and_pedestrian_infrastructure():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"}}
    parking = {"Atlanta": {"status": "derived", "facility_count_0_5mi": 10}}
    benchmarks = {"Atlanta": {"sustainability_evidence": {"fleet_electrification_tier": 100}}}
    walking_networks = {"Atlanta": {"detour_ratio": 1.0, "crossing_tag_coverage_pct": 10.0}}
    metrics = build_city_metrics(
        visits, weather, uhi, poi, gtfs,
        parking=parking, benchmarks=benchmarks, walking_networks=walking_networks,
    )
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    # parking_score = 100 (only city, so it's its own ceiling); pedestrian:
    # detour component = 100/1.0 = 100, crossing component = 100 (only city,
    # its own ceiling) -> pedestrian_infrastructure_score = 100.
    assert atlanta["parking_score"] == 100.0
    assert atlanta["fleet_electrification_score"] == 100.0
    assert atlanta["pedestrian_infrastructure_score"] == 100.0
    # sustainability = 0.5*(100-100) + 0.3*100 + 0.2*100 = 0 + 30 + 20 = 50.
    assert atlanta["sustainability_score"] == 50.0
    assert atlanta["sustainability_status"] == "derived"


def test_sustainability_score_renormalizes_when_a_component_is_missing():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"}}
    benchmarks = {"Atlanta": {"sustainability_evidence": {"fleet_electrification_tier": 100}}}
    # No parking, no walking_networks passed -> only fleet electrification is available.
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={}, benchmarks=benchmarks)
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["parking_score"])
    assert pd.isna(atlanta["pedestrian_infrastructure_score"])
    assert atlanta["sustainability_score"] == 100.0


def test_sustainability_score_is_unavailable_with_no_real_inputs():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={}, benchmarks={})
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["sustainability_score"])
    assert atlanta["sustainability_status"] == "unavailable"


def test_pedestrian_infrastructure_score_falls_back_to_crossing_coverage_alone():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {
        "Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"},
        "Boston": {"gtfs_transit_score": 50, "score_status": "observed"},
    }
    # Boston has no real detour_ratio (the walking pipeline only partially
    # covers it), only crossing_tag_coverage_pct.
    walking_networks = {
        "Atlanta": {"detour_ratio": 2.0, "crossing_tag_coverage_pct": 16.0},
        "Boston": {"crossing_tag_coverage_pct": 8.0},
    }
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={}, walking_networks=walking_networks)
    by_city = metrics.set_index("city")
    # Atlanta: detour component = 100/2.0 = 50; crossing = 16/16*100 = 100 (its own ceiling).
    assert by_city.loc["Atlanta", "pedestrian_infrastructure_score"] == 75.0
    # Boston: only crossing component = 8/16*100 = 50 (Atlanta is the ceiling).
    assert by_city.loc["Boston", "pedestrian_infrastructure_score"] == 50.0


def test_benchmark_capacity_score_is_unavailable_without_dedicated_service_evidence():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 80, "score_status": "observed"}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={}, benchmarks={})
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["benchmark_capacity_score"])


def test_heat_score_blends_air_and_urban_heat_island_signals_50_50():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(
        [{"city": "Atlanta", "date": pd.Timestamp("2026-06-15"), "avg_temp_c": 30.0, "humidity": 60.0}]
    )
    uhi = pd.DataFrame([{"city": "Atlanta", "venue_p90_uhi": 4.0, "venue_points": 5}])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={})
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.notna(atlanta["heat_air_score"])
    assert pd.notna(atlanta["uhi_score"])
    # heat_score is a 50/50 blend of the two, not either alone.
    expected = round((atlanta["heat_air_score"] + atlanta["uhi_score"]) / 2, 1)
    assert atlanta["heat_score"] == expected
    assert atlanta["heat_status"] == "derived"


def test_heat_score_renormalizes_when_only_one_heat_signal_is_available():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(
        [{"city": "Atlanta", "date": pd.Timestamp("2026-06-15"), "avg_temp_c": 30.0, "humidity": 60.0}]
    )
    # No UHI data supplied at all.
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={})
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["uhi_score"])
    assert atlanta["heat_score"] == round(atlanta["heat_air_score"], 1)


def test_heat_score_is_unavailable_with_no_real_heat_inputs():
    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {"Atlanta": {"gtfs_transit_score": 50, "score_status": "observed"}}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={})
    atlanta = metrics.loc[metrics["city"] == "Atlanta"].iloc[0]
    assert pd.isna(atlanta["heat_score"])
    assert atlanta["heat_status"] == "unavailable"


def test_traffic_score_is_the_hand_curated_value_for_every_host_city():
    from dashboard.domain.action_plans import TRAFFIC_MANAGEMENT_SCORES
    from dashboard.mobility_platform.mappings import HOST_CITIES

    visits = pd.DataFrame(columns=["city", "date", "daily_visits"])
    weather = pd.DataFrame(columns=["city", "date", "avg_temp_c", "humidity"])
    uhi = pd.DataFrame(columns=["city", "venue_p90_uhi", "venue_points"])
    poi = pd.DataFrame(columns=["city", "category", "poi_count_1mi"])
    gtfs = {}
    metrics = build_city_metrics(visits, weather, uhi, poi, gtfs, parking={})
    by_city = metrics.set_index("city")
    for city in HOST_CITIES:
        assert by_city.loc[city, "traffic_score"] == float(TRAFFIC_MANAGEMENT_SCORES[city]["score"])
        assert by_city.loc[city, "traffic_status"] == "derived"
