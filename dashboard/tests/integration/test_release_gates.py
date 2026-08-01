import math
from pathlib import Path

from dashboard.domain.scoring import composite_score, heat_safety_score, normalize_weights, uhi_safety_score
from dashboard.mobility_platform.contracts import EvidenceMetric, EvidenceStatus, ScenarioConfig
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


def test_application_shell_does_not_scan_raw_data():
    app = Path(__file__).parents[2] / "app.py"
    source = app.read_text(encoding="utf-8")
    assert "read_csv" not in source
    assert "Rice WC Hack" not in source
    assert "load_artifacts" in source
