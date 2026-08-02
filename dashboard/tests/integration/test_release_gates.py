import json
import math
from pathlib import Path

import pandas as pd

from dashboard.domain.scoring import (
    build_city_metrics,
    composite_score,
    heat_safety_score,
    normalize_weights,
    uhi_safety_score,
)
from dashboard.mobility_platform.contracts import (
    CONTRACT_VERSION,
    AccessGapResult,
    EvidenceMetric,
    EvidenceStatus,
    InterventionPackage,
    MatchEvent,
    MovementScenario,
    ScenarioConfig,
    SourceReference,
)
from dashboard.mobility_platform.mappings import HOST_CITIES


def test_all_host_cities_have_unique_venue_coordinates():
    assert len(HOST_CITIES) == 11
    coordinates = {(meta["lat"], meta["lon"]) for meta in HOST_CITIES.values()}
    assert len(coordinates) == len(HOST_CITIES)


def test_weights_and_scores_stay_in_release_bounds():
    weights = normalize_weights()
    assert math.isclose(sum(weights.values()), 1.0)
    row = {
        "transit_score": 0, "transit_status": "observed",
        "heat_score": 100, "heat_status": "derived",
        "uhi_score": 0, "uhi_status": "derived",
        "access_score": 100, "access_status": "derived",
    }
    score, _, coverage = composite_score(row)
    assert score is not None and 0 <= score <= 100
    assert math.isclose(coverage, 1.0)


def test_heat_and_uhi_increases_never_improve_safety():
    assert heat_safety_score(35) <= heat_safety_score(30)
    assert uhi_safety_score(8) <= uhi_safety_score(4)


def test_scenario_inputs_cannot_create_negative_physical_outputs():
    try:
        ScenarioConfig(city="Atlanta", shuttle_buses_per_hour=-1)
    except ValueError:
        pass
    else:
        raise AssertionError("negative scenario capacity must be rejected")


def test_evidence_metric_serializes_required_provenance_fields():
    metric = EvidenceMetric(
        value=5,
        unit="score",
        status=EvidenceStatus.OBSERVED,
        source="fixture",
        coverage_start="2024-01-01",
        coverage_end="2024-12-31",
        sample_size=10,
        uncertainty_low=None,
        uncertainty_high=None,
        assumptions=("fixture assumption",),
    ).to_dict()
    assert {"value", "unit", "status", "source", "coverage_start", "coverage_end", "sample_size", "uncertainty_low", "uncertainty_high", "assumptions"}.issubset(metric)


def test_contract_0_3_fixture_round_trips():
    fixture_path = Path(__file__).parents[1] / "fixtures" / "contract_0_3.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    source = SourceReference(**{**fixture["source"], "status": EvidenceStatus(fixture["source"]["status"])})
    match = MatchEvent(**fixture["match"], source=source)
    movement = MovementScenario(
        **{
            **fixture["movement"],
            "status": EvidenceStatus(fixture["movement"]["status"]),
            "hourly_rows": tuple(fixture["movement"]["hourly_rows"]),
        }
    )
    access = AccessGapResult(
        **{**fixture["access_gap"], "status": EvidenceStatus(fixture["access_gap"]["status"])}
    )
    assert CONTRACT_VERSION == "0.3.0"
    assert match.to_dict()["source"]["publisher"] == "FIFA"
    assert movement.to_dict()["status"] == "scenario"
    assert access.to_dict()["residual_passengers"] == 10000


def test_intervention_package_rejects_invalid_values():
    try:
        InterventionPackage(name="invalid", arrival_spreading_pct=101)
    except ValueError:
        pass
    else:
        raise AssertionError("arrival spreading above 100% must be rejected")


def test_application_shell_does_not_scan_raw_data():
    app = Path(__file__).parents[2] / "app.py"
    source = app.read_text(encoding="utf-8")
    assert "read_csv" not in source
    assert "Rice WC Hack" not in source
    assert "load_artifacts" in source


def test_supplied_metric_sources_name_the_rice_collection():
    weather = pd.DataFrame({
        "city": ["Atlanta"],
        "date": pd.to_datetime(["2024-06-01"]),
        "avg_temp_c": [30.0],
        "max_temp_c": [35.0],
        "min_temp_c": [24.0],
        "humidity": [60.0],
        "evidence_status": ["derived"],
    })
    uhi = pd.DataFrame({"city": ["Atlanta"], "venue_p90_uhi": [5.0], "venue_points": [12], "evidence_status": ["derived"]})
    poi = pd.DataFrame({"city": ["Atlanta"], "category": ["Transit"], "poi_count_1mi": [20], "evidence_status": ["derived"]})
    metrics = build_city_metrics(pd.DataFrame(), weather, uhi, poi, {})
    evidence = json.loads(metrics.loc[metrics["city"] == "Atlanta", "evidence_json"].iloc[0])
    assert evidence["heat"]["source"].startswith("Rice WC Hack / daily-weather-rice")
    assert evidence["uhi"]["source"].startswith("Rice WC Hack / urban-heat-index-rice")
    assert evidence["access"]["source"].startswith("Rice WC Hack / core-poi-geometry-rice")
