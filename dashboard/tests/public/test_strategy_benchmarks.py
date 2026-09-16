from __future__ import annotations

import copy
import json

import pytest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.strategy_benchmarks import DEFAULT_OUTPUT, validate_snapshot


def _snapshot():
    return json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))


def test_checked_strategy_benchmark_is_complete_and_valid() -> None:
    snapshot = _snapshot()
    validate_snapshot(snapshot)
    assert set(snapshot["benchmarks"]) == set(HOST_CITIES)
    assert all(row["source_url"].startswith("https://") for row in snapshot["benchmarks"].values())


def test_strategy_benchmark_rejects_label_or_hash_tampering() -> None:
    snapshot = _snapshot()
    changed = copy.deepcopy(snapshot)
    changed["benchmarks"]["Atlanta"]["strategy_family"] = "Invented family"
    with pytest.raises(ValueError):
        validate_snapshot(changed)


def test_every_city_has_sourced_dedicated_service_evidence() -> None:
    # dedicated_service_evidence isn't required by validate_snapshot (it's an
    # optional supplement scoring.py reads for the transit-access blend), but
    # every host should have one, cited to a real HTTPS source, once curated.
    snapshot = _snapshot()
    for city, row in snapshot["benchmarks"].items():
        evidence = row.get("dedicated_service_evidence")
        assert isinstance(evidence, dict), city
        assert evidence["tier"] in (60, 100), city
        assert str(evidence["source_url"]).startswith("https://"), city
        assert str(evidence["basis"]).strip(), city
        assert str(evidence["publisher"]).strip(), city


def test_boston_evidence_distinguishes_existing_bus_connection_from_train_service() -> None:
    evidence = _snapshot()["benchmarks"]["Boston"]["dedicated_service_evidence"]
    assert "Rhode Island Convention Center" in evidence["basis"]
    assert "direct express-bus connection, not a direct stadium train" in evidence["basis"]
    assert "$80" in evidence["basis"] and "$95" in evidence["basis"]
    assert evidence["publisher"] == "Boston 26 Host Committee"
    assert evidence["source_url"].startswith("https://bostonfwc26.com/")


def test_sf_detour_evidence_does_not_claim_a_universal_distance_penalty() -> None:
    evidence = _snapshot()["benchmarks"]["San Francisco"]["sustainability_evidence"]
    basis = evidence["pedestrian_infrastructure_basis"]
    assert "Cyclists are directed via" in basis
    assert "pedestrians via Mission College Boulevard" in basis
    assert "not every stadium trip" in basis
    assert "two-mile" not in basis
    assert evidence["pedestrian_infrastructure_publisher"] == "City of Santa Clara"


def test_every_city_has_sourced_fleet_electrification_evidence() -> None:
    # sustainability_evidence isn't required by validate_snapshot either (an
    # optional supplement scoring.py reads for the sustainability score), but
    # every host should have one, cited to a real HTTPS source, once curated.
    snapshot = _snapshot()
    for city, row in snapshot["benchmarks"].items():
        evidence = row.get("sustainability_evidence")
        assert isinstance(evidence, dict), city
        assert evidence["fleet_electrification_tier"] in (30, 60, 100), city
        assert str(evidence["source_url"]).startswith("https://"), city
        assert str(evidence["fleet_electrification_basis"]).strip(), city
        assert str(evidence["publisher"]).strip(), city


def test_every_city_has_sourced_pedestrian_infrastructure_evidence() -> None:
    # A real, sourced walkability/shade/sidewalk fact for the "Pedestrian
    # infrastructure" line in Mobility summary - not an OSM-derived metric.
    snapshot = _snapshot()
    for city, row in snapshot["benchmarks"].items():
        evidence = row.get("sustainability_evidence")
        assert isinstance(evidence, dict), city
        assert str(evidence["pedestrian_infrastructure_source_url"]).startswith("https://"), city
        assert str(evidence["pedestrian_infrastructure_basis"]).strip(), city
        assert str(evidence["pedestrian_infrastructure_publisher"]).strip(), city


def test_every_city_has_sourced_congestion_management_evidence() -> None:
    # congestion_management_evidence isn't required by validate_snapshot either
    # (an optional supplement the City action plan's Traffic management
    # solution tab reads directly), but every host should have at least one
    # real, cited road-closure/congestion-control hotspot.
    snapshot = _snapshot()
    for city, row in snapshot["benchmarks"].items():
        evidence = row.get("congestion_management_evidence")
        assert isinstance(evidence, dict), city
        hotspots = evidence.get("hotspots")
        assert isinstance(hotspots, list) and hotspots, city
        for hotspot in hotspots:
            assert str(hotspot["source_url"]).startswith("https://"), city
            assert str(hotspot["location"]).strip(), city
            assert str(hotspot["control"]).strip(), city
            assert str(hotspot["publisher"]).strip(), city
