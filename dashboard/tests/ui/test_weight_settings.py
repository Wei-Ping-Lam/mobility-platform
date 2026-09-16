import pytest

from dashboard.ui.portfolio import shared


@pytest.mark.parametrize("existing", [False, True])
def test_balanced_weights_use_updated_defaults(monkeypatch, existing):
    state = {"weight_profile": "balanced"}
    if existing:
        state.update(weight_gap=0.30, weight_heat=0.25, weight_access=0.25, weight_traffic=0.20)
    monkeypatch.setattr(shared.st, "session_state", state)

    weights, _ = shared.resolve_weight_settings()

    assert weights == pytest.approx({"gap": 0.30, "traffic": 0.30, "heat": 0.25, "access": 0.15})


def test_balanced_update_preserves_custom_weights(monkeypatch):
    state = dict(weight_profile="balanced", weight_gap=0.40, weight_heat=0.25, weight_access=0.15, weight_traffic=0.20)
    monkeypatch.setattr(shared.st, "session_state", state)

    weights, _ = shared.resolve_weight_settings()

    assert weights == pytest.approx({"gap": 0.40, "traffic": 0.20, "heat": 0.25, "access": 0.15})
