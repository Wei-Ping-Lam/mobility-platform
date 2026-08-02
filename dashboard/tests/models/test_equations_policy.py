from dashboard.models.equations import EQUATIONS, equation_ids, equation_records
from dashboard.models.recommendation_policy import MEASURE_POLICIES, policy_records


def test_equation_registry_has_stable_unique_ids_and_review_fields():
    records = equation_records()
    assert len(records) == len(EQUATIONS) == len(set(equation_ids()))
    assert {"EQ-SPREAD-01", "EQ-COST-02", "EQ-PARETO-01"}.issubset(equation_ids())
    for row in records:
        assert all(row[key].strip() for key in ("equation_id", "equation", "variables", "interpretation", "evidence_limit"))


def test_every_recommendation_measure_has_explicit_policy_metadata():
    records = policy_records()
    assert len(records) == len(MEASURE_POLICIES) == 6
    for row in records:
        assert row["lead_time_band"]
        assert row["responsible_actor"]
        assert row["comparison_cost_basis"]
        assert row["evidence_rule"]
        assert row["dependencies"]
