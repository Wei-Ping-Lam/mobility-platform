"""Stable workspace registry for the public Streamlit shell.

Keeping navigation policy out of ``dashboard/app.py`` gives one small,
integration-owned seam for enabling or deferring whole product workspaces.
Deferred renderers remain in the repository and can be restored without
mixing their implementation into the active application shell.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkspaceSpec:
    key: str
    label: str
    city_scoped: bool = False


ACTIVE_WORKSPACES = (
    WorkspaceSpec("Overview", "Portfolio"),
    WorkspaceSpec("City Brief", "City action plan", city_scoped=True),
)

# Preserved implementation, intentionally absent from public navigation.
DEFERRED_WORKSPACES = (
    WorkspaceSpec("Explorer", "Scenario explorer", city_scoped=True),
    WorkspaceSpec("Methods & QA", "Methods"),
)

DEFAULT_WORKSPACE = ACTIVE_WORKSPACES[0].key
_ACTIVE_BY_KEY = {workspace.key: workspace for workspace in ACTIVE_WORKSPACES}


def active_workspace_keys() -> list[str]:
    return [workspace.key for workspace in ACTIVE_WORKSPACES]


def active_workspace_labels() -> dict[str, str]:
    return {workspace.key: workspace.label for workspace in ACTIVE_WORKSPACES}


def normalize_workspace(value: object) -> str:
    """Return an active workspace, clearing stale deferred session state."""

    key = str(value or "")
    return key if key in _ACTIVE_BY_KEY else DEFAULT_WORKSPACE


def workspace_is_city_scoped(key: str) -> bool:
    workspace = _ACTIVE_BY_KEY.get(key)
    return bool(workspace and workspace.city_scoped)
