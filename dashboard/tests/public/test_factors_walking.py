from pathlib import Path

import pytest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.loaders import load_factor_registry, load_walking_snapshot
from dashboard.pipeline.public.walking import validate_walking_city


def test_factor_registry_ranges_and_primary_sources_are_ui_ready():
    registry = load_factor_registry(Path("data/snapshots/factors/planning_factors.json"))
    assert {"epa", "fta_ntd", "fta_ccd", "fhwa", "scenario_assumptions"} == set(registry["sources"])
    for source_id, source in registry["sources"].items():
        if source_id != "scenario_assumptions":
            assert source["url"].startswith("https://")
        assert len(source["sha256"]) == 64
    assert len(registry["factors"]) == 20
    for factor in registry["factors"].values():
        assert factor["low"] <= factor["base"] <= factor["high"]
        assert factor["source_ids"]


def test_graph_derived_walking_snapshot_covers_all_cities_without_ada_claims():
    snapshot = load_walking_snapshot(Path("data/snapshots/osm/walking_networks.json"))
    assert set(snapshot["cities"]) == set(HOST_CITIES)
    assert snapshot["status"] == "derived"
    assert snapshot["snapshot_kind"] == "osm_walking_networks"
    for row in snapshot["cities"].values():
        assert row["snapshot_kind"] != "fixture"
        assert len(row["source"]["sha256"]) == 64
        assert row["accessibility_status"] == "not_measured"
        assert len(row["isochrones"]) == 2
        if row["route_geometry"]:
            assert row["network_distance_m"] >= row["straight_distance_m"]
            assert len(row["route_geometry"]["coordinates"]) >= 2
        else:
            assert row["status"] == "partial"


def test_network_distance_invariant_fails_closed():
    with pytest.raises(ValueError, match="invariant"):
        validate_walking_city(
            {
                "city": "Atlanta",
                "straight_distance_m": 500,
                "network_distance_m": 400,
                "detour_ratio": 0.8,
                "sidewalk_tag_coverage_pct": 50,
                "crossing_tag_coverage_pct": 50,
            }
        )
