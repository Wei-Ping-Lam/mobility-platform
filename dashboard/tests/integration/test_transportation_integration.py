from __future__ import annotations

import copy
import json

import pytest

from dashboard.domain.decision_support import build_transportation_bundle
from dashboard.domain.scoring import DEFAULT_WEIGHTS, build_city_metrics
from dashboard.mobility_platform.config import project_paths
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash
from dashboard.ui.data import load_artifacts
from dashboard.ui.presentation import build_presentation, city_layer_records
from dashboard.ui.views import _before_after, _movement_chart


def _loaded():
    paths = project_paths()
    artifacts = load_artifacts(paths)
    metrics = build_city_metrics(
        artifacts["visits"],
        artifacts["weather"],
        artifacts["uhi"],
        artifacts["poi"],
        artifacts["gtfs"],
        weights=DEFAULT_WEIGHTS["rice_supplied_data"],
        include_estimates=False,
    )
    return artifacts, metrics


def test_nested_public_and_rice_artifacts_load_for_all_host_cities():
    artifacts, _ = _loaded()
    assert len(artifacts["match_events"]) == 78
    assert set(artifacts["gtfs"]) == set(HOST_CITIES)
    assert set(artifacts["walking_networks"]) == set(HOST_CITIES)
    assert set(artifacts["map_layers"]) == set(HOST_CITIES)
    assert not artifacts["uhi_points"].empty
    assert not artifacts["poi_points"].empty
    assert not artifacts["origin_flows"].empty


def test_compact_evidence_composes_match_decisions_with_repaired_event_gtfs():
    artifacts, metrics = _loaded()
    bundle = build_transportation_bundle(metrics, artifacts)
    assert len(bundle["movement_scenarios"]) == 78
    assert len(bundle["access_gaps"]) == 78
    assert len(bundle["intervention_outcomes"]) == 78 * 3
    assert bundle["investment_recommendations"]
    assert len(bundle["equation_registry"]) >= 9
    assert len(bundle["recommendation_policy"]) == 6
    assert all(row.get("equation_ids") for row in bundle["investment_recommendations"])
    valid_matches = {row["match_id"] for row in artifacts["match_events"]}
    assert all(row.get("match_id") in valid_matches for row in bundle["investment_recommendations"])
    access_by_city = {row["city"]: row for row in bundle["access_gaps"]}
    for city in ("Kansas City", "Philadelphia"):
        city_access = [row for row in bundle["access_gaps"] if row["city"] == city]
        assert city_access
        assert all(row["status"] == "scenario" for row in city_access)
        assert all(row["transit_capacity_base"] > 0 for row in city_access)
        assert artifacts["gtfs"][city]["feed_status"] == "observed"
        assert len(artifacts["gtfs"][city]["matches"]) == 6
        assert all(feed["status"] == "observed" for feed in artifacts["gtfs"][city]["feeds"])
        assert artifacts["walking_networks"][city]["network_distance_m"] is not None
    assert access_by_city["Atlanta"]["status"] == "scenario"
    assert access_by_city["Miami"]["transit_capacity_base"] == 0
    assert access_by_city["Miami"]["status"] == "partial"
    for city in ("Kansas City", "Philadelphia"):
        city_options = [
            row for row in bundle["investment_recommendations"] if row["city"] == city
        ]
        assert any(row["status"] == "scenario" and row["evidence_qualified"] for row in city_options)
        assert any(row["status"] == "partial" and not row["evidence_qualified"] for row in city_options)
    assert all(row["peak_demand_per_hour"] > 0 for row in bundle["access_gaps"])
    assert all(row["residual_passengers"] >= 0 for row in bundle["access_gaps"])
    assert any(row["residual_passengers"] > 0 for row in bundle["access_gaps"])


def test_recommendations_are_scoped_to_exact_matches_without_citywide_bleed():
    artifacts, metrics = _loaded()
    bundle = build_transportation_bundle(metrics, artifacts)
    artifacts.update(bundle)
    presentation = build_presentation(metrics, artifacts)

    presented = 0
    for decision in presentation.cities.values():
        for match in decision.matches:
            expected = [
                row
                for row in bundle["investment_recommendations"]
                if row["city"] == decision.city and row["match_id"] == match.match_id
            ]
            actual = decision.recommendation_set(match.match_id)
            assert len(actual) == len(expected)
            assert len(actual) <= 6
            presented += len(actual)
    assert presented == len(bundle["investment_recommendations"])
    first_city = sorted(presentation.cities)[0]
    first_match = presentation.city(first_city).match()
    download = json.loads(presentation.scenario_json(first_city, first_match.match_id))
    assert download["equations"]
    assert download["recommendation_policy"]
    assert download["assumption_registry"]


def test_same_package_responds_to_city_evidence():
    artifacts, metrics = _loaded()
    bundle = build_transportation_bundle(metrics, artifacts)
    operational = [
        row for row in bundle["intervention_outcomes"] if row["package"]["name"] == "Operational Package"
    ]
    first_match_by_city = {}
    for row in operational:
        first_match_by_city.setdefault(row["city"], row)
    assert len(first_match_by_city) == 11
    assert len({row["net_vmt_base"] for row in first_match_by_city.values()}) > 1
    assert len({row["gap_resolved_passengers"] for row in first_match_by_city.values()}) > 1


def test_all_real_movement_timelines_render_and_operational_spreading_conserves_flow():
    artifacts, metrics = _loaded()
    artifacts.update(build_transportation_bundle(metrics, artifacts))
    presentation = build_presentation(metrics, artifacts)
    checked = 0
    for decision in presentation.cities.values():
        for match in decision.matches:
            movement = decision.movement(match.match_id)
            figure, table = _movement_chart(movement)
            assert figure is not None and not table.empty
            assert {"timestamp_local", "arrivals_low", "arrivals_base", "arrivals_high", "departures_low", "departures_base", "departures_high"}.issubset(table)
            operational = decision.scenario_set(match.match_id)[1]
            timeline = _before_after(movement, operational)
            assert not timeline.empty
            assert timeline["Before"].sum() == pytest.approx(timeline["After"].sum())
            assert timeline["After"].max() < timeline["Before"].max()
            checked += 1
    assert checked == 78


def test_gtfs_map_adapter_matches_compact_snapshot_and_exposes_routes():
    artifacts, _ = _loaded()
    houston = artifacts["gtfs"]["Houston"]
    assert len(city_layer_records(artifacts, "Houston", "gtfs")) == len(houston["stop_points_2mi"]) > 0
    assert len(city_layer_records(artifacts, "Houston", "gtfs_routes")) == len(houston["route_shapes"]) > 0


def test_factor_provenance_is_required_and_changes_dependent_outputs():
    artifacts, metrics = _loaded()
    bundle = build_transportation_bundle(metrics, artifacts)
    digest = artifacts["factor_snapshot"]["artifact_sha256"]
    assert all(any(digest in assumption for assumption in row["assumptions"]) for row in bundle["intervention_outcomes"])

    missing = dict(artifacts)
    missing.pop("factor_snapshot")
    with pytest.raises(ValueError, match="factor snapshot"):
        build_transportation_bundle(metrics, missing)

    changed = copy.deepcopy(artifacts)
    changed["factor_snapshot"]["factors"]["shuttle_cost_per_bus_hour"]["base"] *= 1.25
    changed["factor_snapshot"]["artifact_sha256"] = artifact_hash(changed["factor_snapshot"])
    changed_bundle = build_transportation_bundle(metrics, changed)
    original = next(row for row in bundle["intervention_outcomes"] if row["package"]["name"] == "Operational Package")
    revised = next(row for row in changed_bundle["intervention_outcomes"] if row["city"] == original["city"] and row["match_id"] == original["match_id"] and row["package"]["name"] == "Operational Package")
    assert revised["cost_base"] > original["cost_base"]


def test_spatial_map_budgets_preserve_full_source_counts():
    artifacts, _ = _loaded()
    for layers in artifacts["map_layers"].values():
        assert len(layers.get("uhi", [])) <= 500
        assert len(layers.get("poi", [])) <= 500
        assert len(layers.get("origin", [])) <= 30
        for key in ("uhi", "poi", "origin"):
            rows = layers.get(key, [])
            if rows:
                assert max(row["source_total_records"] for row in rows) >= len(rows)
