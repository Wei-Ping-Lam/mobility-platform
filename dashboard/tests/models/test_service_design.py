import pytest

from dashboard.models.service_design import event_window_cycles


@pytest.mark.parametrize("hours,cycle,expected", [(3, 0.4, 8), (2, 3, 1), (1, 3, 0), (3, 1, 3), (3, 3.75, 1)])
def test_only_completed_deliveries_count_but_empty_return_can_finish_later(hours, cycle, expected):
    assert event_window_cycles(hours, cycle) == expected


@pytest.mark.parametrize("hours,cycle", [(0, 1), (1, 0), (float("nan"), 1), (1, float("inf"))])
def test_nonfinite_or_nonpositive_durations_are_rejected(hours, cycle):
    with pytest.raises(ValueError):
        event_window_cycles(hours, cycle)
