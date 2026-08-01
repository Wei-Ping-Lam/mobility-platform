import io
import zipfile

from dashboard.pipeline.gtfs.fetch import extract_feed, score_results


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


def test_gtfs_snapshot_extracts_calendar_and_event_window_departures():
    files = {
        "stops.txt": "stop_id,stop_lat,stop_lon\nS1,33.75,-84.40\n",
        "routes.txt": "route_id\nR1\n",
        "trips.txt": "route_id,service_id,trip_id\nR1,S1,T1\n",
        "stop_times.txt": "trip_id,departure_time\nT1,12:00:00\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nS1,1,1,1,1,1,1,1,20260101,20261231\n",
    }
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    result = extract_feed(payload.getvalue())
    assert result["calendar_validity"] == "valid"
    assert result["event_window_departures"] == 1
    assert result["service_span"] == {"start_date": "2026-01-01", "end_date": "2026-12-31"}
