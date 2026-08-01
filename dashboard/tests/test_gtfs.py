from dashboard.pipeline.gtfs.fetch import score_results


def test_observed_zero_service_is_not_missing():
    results = {
        "Dallas": {
            "stops_0_25mi": 0,
            "stops_0_5mi": 0,
            "stops_1mi": 0,
            "stops_2mi": 0,
            "route_count": 0,
            "feed_status": "observed",
        },
        "Seattle": {
            "stops_0_25mi": 10,
            "stops_0_5mi": 20,
            "stops_1mi": 30,
            "stops_2mi": 40,
            "route_count": 5,
            "feed_status": "observed",
        },
    }
    scored = score_results(results)
    assert scored["Dallas"]["gtfs_transit_score"] == 0
    assert scored["Dallas"]["score_status"] == "observed"


def test_unavailable_feed_has_no_score():
    results = {
        "Philadelphia": {
            "stops_0_25mi": 0,
            "stops_0_5mi": 0,
            "stops_1mi": 0,
            "stops_2mi": 0,
            "route_count": 0,
            "feed_status": "unavailable",
        }
    }
    scored = score_results(results)
    assert scored["Philadelphia"]["gtfs_transit_score"] is None
    assert scored["Philadelphia"]["score_status"] == "unavailable"
