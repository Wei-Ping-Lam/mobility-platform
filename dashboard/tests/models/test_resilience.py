from __future__ import annotations

import pytest

from dashboard.models.resilience import stress_access_capacity


def test_common_stress_reduces_coverage_in_physical_units() -> None:
    result = stress_access_capacity(10_000, 6_000)

    assert result["baseline_coverage_pct"] == 60.0
    assert result["stressed_demand_pph"] == 11_000.0
    assert result["stressed_capacity_pph"] == 4_800.0
    assert result["stressed_coverage_pct"] == pytest.approx(43.636, abs=0.001)
    assert result["stressed_gap_pph"] == 6_200.0
    assert result["coverage_change_points"] < 0


def test_stress_test_is_bounded_and_fails_closed_on_invalid_inputs() -> None:
    assert stress_access_capacity(100, 200)["baseline_coverage_pct"] == 100.0
    assert stress_access_capacity(0, 0)["stressed_coverage_pct"] == 0.0
    with pytest.raises(ValueError):
        stress_access_capacity(-1, 10)
    with pytest.raises(ValueError):
        stress_access_capacity(10, 10, capacity_loss_pct=101)
