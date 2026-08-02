import io
import zipfile

from dashboard.pipeline.gtfs.fetch import extract_feed, score_results, unavailable_fixture
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
    assert result["mode_departures"]["bus"] > 0


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


def test_checked_gtfs_fixture_is_explicitly_unavailable():
    snapshot = load_gtfs_snapshot("data/snapshots/gtfs/gtfs_venue_access.json")
    assert snapshot["fixture"] is True
    assert snapshot["status"] == "unavailable"
    assert all(city["score_status"] == "unavailable" for city in snapshot["cities"].values())
