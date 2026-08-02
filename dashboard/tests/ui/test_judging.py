import pandas as pd

from dashboard.ui.judging import build_criteria_evidence, build_deliverable_evidence


def test_judging_evidence_covers_every_weight_without_self_awarded_scores():
    metrics = pd.DataFrame([{"city": "A", "strict_rankable": True}])
    comparison = pd.DataFrame([{"city": "A", "strict_rankable": True}])
    artifacts = {
        "movement_scenarios": [{"match_id": "A-1"}],
        "access_gaps": [{"match_id": "A-1", "status": "scenario"}],
        "intervention_outcomes": [{"match_id": "A-1"}],
        "investment_recommendations": [{"match_id": "A-1"}],
        "movement_validation": [{"holdout_year": 2024}],
        "source_references": [{"sha256": "hash"}],
        "walking_networks": {"A": {"route_geometry": [[0, 0], [1, 1]]}},
    }
    criteria = build_criteria_evidence(metrics, artifacts, comparison)
    assert criteria["Weight"].sum() == 100
    assert criteria["Criterion"].nunique() == 7
    assert "Score" not in criteria.columns
    assert set(criteria["Status"]) <= {"derived", "partial", "unavailable"}


def test_deliverables_make_required_track_outputs_explicit():
    metrics = pd.DataFrame([{"city": "A"}])
    comparison = pd.DataFrame([{"city": "A", "strict_rankable": False}])
    deliverables = build_deliverable_evidence(metrics, {}, comparison)
    assert set(deliverables["Deliverable"]) == {
        "Visitor movement",
        "First/last-mile gaps",
        "Compare resilience",
        "Recommend investments",
        "Sustainability outcomes",
        "Outcomes over time",
    }
    assert deliverables["Workspace"].notna().all()
