import copy

import plotly.graph_objects as go
import pytest

from dashboard.pipeline.public.common import artifact_hash, read_json
from dashboard.pipeline.public.road_closures import OUTPUT, road_segment, validate_snapshot
from dashboard.viz.strategy_overlap import ROAD_CLOSURE_RED, add_road_controls


def test_checked_overlay_has_bounded_sourced_road_geometry():
    snapshot = read_json(OUTPUT)
    validate_snapshot(snapshot)
    assert set(snapshot["cities"]) == {"Dallas", "Miami", "San Francisco"}
    for rows in snapshot["cities"].values():
        for row in rows:
            assert row["from"] and row["to"] and row["timing"] and row["osm_way_ids"]
            assert len(row["coordinates"]) > 2


def test_unknown_controls_and_bad_hash_are_rejected():
    snapshot = read_json(OUTPUT)
    snapshot["cities"]["Dallas"][0]["type"] = "congestion"
    with pytest.raises(ValueError):
        validate_snapshot(snapshot)
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    with pytest.raises(ValueError):
        validate_snapshot(snapshot)


def test_only_actual_vehicle_closures_are_red_and_unknown_controls_are_not_drawn():
    snapshot = read_json(OUTPUT)
    rows = snapshot["cities"]["Dallas"] + snapshot["cities"]["Miami"]
    pedestrian_ban = {**copy.deepcopy(rows[0]), "type": "pedestrian_ban"}
    figure = go.Figure()
    add_road_controls(figure, rows + [pedestrian_ban])
    assert len(figure.data) == 3
    assert [trace.line.color == ROAD_CLOSURE_RED for trace in figure.data] == [True, True, False]
    assert [trace.showlegend for trace in figure.data] == [True, False, True]
    assert all(trace.connectgaps is False for trace in figure.data)
    assert "not live status" in figure.data[0].text[0]


def test_geometry_stops_at_named_intersections_and_never_draws_a_fallback_line():
    nodes = {"a": [0, 0], "b": [1, 0], "c": [2, 0], "d": [3, 0], "e": [1, 1], "f": [2, 1]}
    ways = [
        {"id": "1", "name": "Main Street", "nodes": ["a", "b", "c", "d"]},
        {"id": "2", "name": "First Street", "nodes": ["b", "e"]},
        {"id": "3", "name": "Second Street", "nodes": ["c", "f"]},
    ]
    coordinates, ids = road_segment(nodes, ways, "Main Street", "First Street", "Second Street")
    assert coordinates == [[1, 0], [2, 0]] and ids == ["1"]
    with pytest.raises(ValueError):
        road_segment(nodes, ways, "Main Street", "Unknown Street", "Second Street")
