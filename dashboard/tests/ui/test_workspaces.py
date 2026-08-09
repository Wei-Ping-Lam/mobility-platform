from dashboard.ui.workspaces import (
    ACTIVE_WORKSPACES,
    DEFERRED_WORKSPACES,
    active_workspace_keys,
    active_workspace_labels,
    normalize_workspace,
    workspace_is_city_scoped,
)


def test_public_workspace_registry_exposes_only_current_decision_surfaces() -> None:
    assert active_workspace_keys() == ["Overview", "City Brief"]
    assert active_workspace_labels() == {
        "Overview": "Portfolio",
        "City Brief": "City action plan",
    }
    assert {workspace.key for workspace in ACTIVE_WORKSPACES}.isdisjoint(
        workspace.key for workspace in DEFERRED_WORKSPACES
    )


def test_deferred_or_unknown_session_state_returns_to_portfolio() -> None:
    assert normalize_workspace("Explorer") == "Overview"
    assert normalize_workspace("Methods & QA") == "Overview"
    assert normalize_workspace("unknown") == "Overview"
    assert normalize_workspace("City Brief") == "City Brief"
    assert workspace_is_city_scoped("City Brief")
    assert not workspace_is_city_scoped("Overview")
