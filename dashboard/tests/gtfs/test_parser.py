import io
import zipfile

import pandas as pd
import requests

from dashboard.pipeline.gtfs.config import GtfsFeedSource
from dashboard.pipeline.gtfs.fetch import count_near_venue, extract_feed, fetch_city, score_results, unavailable_fixture
from dashboard.pipeline.public.loaders import load_gtfs_snapshot


def _feed(files):
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return payload.getvalue()


def test_parser_covers_calendar_exceptions_frequency_and_optional_files():
    files = {
        "stops.txt": "stop_id,stop_lat,stop_lon\nS1,33.7554,-84.4009\n",
        "routes.txt": "route_id,route_type\nR1,3\n",
        "trips.txt": "route_id,service_id,trip_id,shape_id\nR1,WK,T1,SH1\nR1,ADD,T2,SH1\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,18:00:00,18:00:00,S1,1\nT2,19:00:00,19:00:00,S1,1\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWK,1,1,1,1,1,0,0,20260101,20261231\n",
        "calendar_dates.txt": "service_id,date,exception_type\nADD,20260612,1\n",
        "frequencies.txt": "trip_id,start_time,end_time,headway_secs\nT1,17:00:00,21:00:00,1800\n",
        "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\nSH1,33.75,-84.40,1\n",
        "transfers.txt": "from_stop_id,to_stop_id,transfer_type\nS1,S1,0\n",
        "pathways.txt": "pathway_id,from_stop_id,to_stop_id,pathway_mode,is_bidirectional\nP1,S1,S1,1,1\n",
    }
    event = {"match_id": "M004", "kickoff_local": "2026-06-12T18:00:00-04:00"}
    result = extract_feed(_feed(files), {"lat": 33.7554, "lon": -84.4009}, [event])
    assert result["calendar_validity"] == "valid"
    assert result["event_window_departures"] > 0
    assert result["venue_stop_count"] == 1
    assert result["optional_files"] == {
        "frequencies.txt": True,
        "shapes.txt": True,
        "transfers.txt": True,
        "pathways.txt": True,
    }
    assert result["capacity"]["low"] <= result["capacity"]["base"] <= result["capacity"]["high"]
    match = result["event_departures_by_match"][0]
    assert match["calendar_valid"] is True
    assert match["departures"] > 0
    assert match["capacity_low"] <= match["capacity_base"] <= match["capacity_high"]
    assert result["mode_departures"]["bus"] > 0


def test_nested_archive_uses_exact_stops_member_and_not_route_stops():
    inner = _feed(
        {
            "route_stops.txt": "route_id,direction_id,stop_id,route_stop_sort_order\nR1,0,S1,1\n",
            "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,Venue stop,33.7554,-84.4009\n",
            "routes.txt": "route_id,route_type\nR1,3\n",
            "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,18:00:00,18:00:00,S1,1\n",
            "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWK,1,1,1,1,1,1,1,20260101,20261231\n",
        }
    )
    payload = _feed({"google_bus.zip": inner})
    event = {"match_id": "M004", "kickoff_local": "2026-06-12T18:00:00-04:00"}

    result = extract_feed(payload, {"lat": 33.7554, "lon": -84.4009}, [event])

    assert {"stop_id", "stop_lat", "stop_lon"}.issubset(result["stops"].columns)
    assert result["venue_stop_count"] == 1
    assert result["event_departures_by_match"][0]["departures"] == 1


def test_numeric_trip_ids_retain_event_route_labels_for_walking_targets():
    payload = _feed(
        {
            "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\n130,Venue stop,25.943,-80.213\n",
            "routes.txt": "route_id,route_short_name,route_type\n7,Route 7,3\n",
            "trips.txt": "route_id,service_id,trip_id\n7,1,1001\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n1001,18:00:00,18:00:00,130,1\n",
            "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n1,1,1,1,1,1,1,1,20260101,20261231\n",
        }
    )
    event = {"match_id": "M013", "kickoff_local": "2026-06-15T18:00:00-04:00"}

    result = extract_feed(payload, {"lat": 25.943, "lon": -80.213}, [event])

    assert result["stop_routes"]["130"] == ["Route 7"]


def test_walking_route_uses_two_mile_stops_while_capacity_uses_half_mile():
    payload = _feed(
        {
            "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nS1,One mile stop,33.7699,-84.4009\n",
            "routes.txt": "route_id,route_short_name,route_type\nR1,Route 1,3\n",
            "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,18:00:00,18:00:00,S1,1\n",
            "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWK,1,1,1,1,1,1,1,20260101,20261231\n",
        }
    )
    event = {"match_id": "M004", "kickoff_local": "2026-06-12T18:00:00-04:00"}

    result = extract_feed(payload, {"lat": 33.7554, "lon": -84.4009}, [event])

    assert result["venue_stop_count"] == 0
    assert result["event_departures_by_match"][0]["departures"] == 0
    assert result["stop_routes"]["S1"] == ["Route 1"]


def test_pinned_sources_assign_non_overlapping_event_windows(monkeypatch):
    payload = _feed(
        {
            "stops.txt": "stop_id,stop_lat,stop_lon\nS1,33.7554,-84.4009\n",
            "routes.txt": "route_id,route_type\nR1,3\n",
            "trips.txt": "route_id,service_id,trip_id\nR1,WK,T1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,18:00:00,18:00:00,S1,1\n",
            "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWK,1,1,1,1,1,1,1,20260101,20261231\n",
        }
    )

    class Response:
        content = payload

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: Response())
    digest = __import__("hashlib").sha256(payload).hexdigest()
    feeds = [
        GtfsFeedSource("Fixture", "https://example.invalid/first.zip", expected_sha256=digest, valid_to="2026-06-12"),
        GtfsFeedSource("Fixture", "https://example.invalid/second.zip", expected_sha256=digest, valid_from="2026-06-13"),
    ]
    events = [
        {"match_id": "M1", "kickoff_local": "2026-06-12T18:00:00-04:00"},
        {"match_id": "M2", "kickoff_local": "2026-06-13T18:00:00-04:00"},
    ]

    result = fetch_city("Atlanta", feeds, events)

    assert result["feed_status"] == "observed"
    assert result["matches"]["M1"]["event_window_departures"] == 1
    assert result["matches"]["M2"]["event_window_departures"] == 1
    assert [feed["assigned_match_ids"] for feed in result["feeds"]] == [["M1"], ["M2"]]


def test_hash_policy_and_feed_failure_never_fall_back():
    fixture = unavailable_fixture()
    assert len(fixture) == 11
    assert all(row["gtfs_transit_score"] is None for row in fixture.values())
    result = score_results(
        {
            "Philadelphia": {
                "feed_status": "observed",
                "feeds": [{"status": "observed", "sha256": None}],
                "stops_0_25mi": 20,
                "route_count": 10,
            }
        }
    )["Philadelphia"]
    assert result["feed_status"] == "unavailable"
    assert result["gtfs_transit_score"] is None
    assert result["score_status"] == "unavailable"


def test_checked_gtfs_snapshot_preserves_evidence_gates():
    snapshot = load_gtfs_snapshot("data/snapshots/gtfs/gtfs_venue_access.json")
    if snapshot["fixture"]:
        assert snapshot["status"] == "unavailable"
    for city in snapshot["cities"].values():
        if city["score_status"] == "observed":
            assert city["calendar_validity"] == "valid"
            assert all(len(feed["sha256"]) == 64 for feed in city["feeds"])
        if city["feed_status"] == "unavailable":
            assert city["gtfs_transit_score"] is None


def test_python_38_refresh_paths_do_not_require_dictionary_union(monkeypatch):
    empty = count_near_venue(pd.DataFrame(), {"lat": 0.0, "lon": 0.0})
    assert empty["nearest_stop_mi"] is None
    assert empty["stops_5mi"] == 0

    def fail_request(*args, **kwargs):
        raise requests.RequestException("fixture failure")

    monkeypatch.setattr(requests, "get", fail_request)
    result = fetch_city("Atlanta", [GtfsFeedSource("Fixture", "https://example.invalid/feed.zip")], [])
    assert result["feed_status"] == "unavailable"
    assert result["feeds"][0]["sha256"] is None
