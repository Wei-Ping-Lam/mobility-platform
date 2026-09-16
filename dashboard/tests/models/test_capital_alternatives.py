import pytest

from dashboard.models.capital_alternatives import ALTERNATIVES, estimate_capital_alternative


@pytest.mark.parametrize("city", ALTERNATIVES)
def test_capital_ranges_reconcile_and_do_not_double_count_return_passengers(city):
    result = estimate_capital_alternative(city, 60000, 3)
    scope = result["concept"]
    assert 0 < result["capital_low"] < result["capital_high"]
    assert 0 <= result["passengers_low"] <= result["passengers_high"] <= 60000
    for case in ("low", "high"):
        assert result[f"capital_{case}"] == sum(result[f"{key}_{case}"] for key in ("fleet", "infrastructure", "contingency", "corridor"))
    assert result["capital_low"] == pytest.approx(scope.buses * 1_300_000 * 1.2 * 1.15 + scope.corridor_miles * 10_000_000)
    assert result["active_buses"] + result["reserve_buses"] == scope.buses
    assert result["passengers_high"] <= result["active_buses"] * result["cycles_per_bus"] * 45
    assert estimate_capital_alternative(city, 10, 3)["passengers_high"] == 10
    assert estimate_capital_alternative(city, 0, 3)["passengers_high"] == 0


@pytest.mark.parametrize("city", ["Atlanta", "Seattle", "San Francisco", "New York/NJ", "Houston"])
def test_no_high_capital_concept_without_a_curated_case(city):
    assert estimate_capital_alternative(city, 60000, 3) is None


def test_cycle_time_limits_capacity():
    result = estimate_capital_alternative("Boston", 60000, 1)
    assert result["passengers_high"] == 0


def test_reserves_and_slower_cycles_reduce_miami_capacity():
    result = estimate_capital_alternative("Miami", 60000, 3)
    assert result["active_buses"] == 50
    assert result["reserve_buses"] == 10
    assert result["slow_cycles_per_bus"] == 2
    assert result["cycles_per_bus"] == 3
    assert result["passengers_low"] == 2925
    assert result["passengers_high"] == 5737


@pytest.mark.parametrize("attendance,hours", [(float("nan"), 3), (-1, 3), (50000, 0)])
def test_invalid_inputs_are_rejected(attendance, hours):
    with pytest.raises(ValueError):
        estimate_capital_alternative("Boston", attendance, hours)
