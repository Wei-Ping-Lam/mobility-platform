from __future__ import annotations

from dashboard.domain.decision_support import build_transportation_bundle
from dashboard.domain.scoring import DEFAULT_WEIGHTS, build_city_metrics
from dashboard.mobility_platform.config import project_paths
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.ui.data import load_artifacts


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


def test_compact_evidence_composes_match_decisions_without_promoting_missing_gtfs():
    artifacts, metrics = _loaded()
    bundle = build_transportation_bundle(metrics, artifacts)
    assert len(bundle["movement_scenarios"]) == 78
    assert len(bundle["access_gaps"]) == 78
    assert len(bundle["intervention_outcomes"]) == 78 * 3
    assert bundle["investment_recommendations"]
    assert {row["status"] for row in bundle["access_gaps"]} == {"unavailable"}
    assert {row["status"] for row in bundle["investment_recommendations"]} == {"partial"}
    assert all(row["peak_demand_per_hour"] > 0 for row in bundle["access_gaps"])
    assert all(row["residual_passengers"] > 0 for row in bundle["access_gaps"])


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
