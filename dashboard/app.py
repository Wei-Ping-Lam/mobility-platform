"""Evidence-first FIFA 2026 Host City Mobility Readiness Platform."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Make both `streamlit run dashboard/app.py` and `cd dashboard; streamlit run app.py`
# resolve the repository package consistently.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dashboard.domain.decision_support import build_transportation_bundle  # noqa: E402
from dashboard.domain.scoring import build_city_metrics  # noqa: E402
from dashboard.mobility_platform.config import project_paths  # noqa: E402
from dashboard.mobility_platform.mappings import HOST_CITIES  # noqa: E402
from dashboard.ui.data import load_artifacts  # noqa: E402
from dashboard.ui.pages.home import render_home  # noqa: E402
from dashboard.ui.pages.overview import render_decision_brief  # noqa: E402
from dashboard.ui.portfolio.shared import resolve_weight_settings  # noqa: E402
from dashboard.ui.theme import apply_theme, brand_block, sidebar_status  # noqa: E402
from dashboard.ui.workspaces import (  # noqa: E402
    active_workspace_keys,
    active_workspace_labels,
    normalize_workspace,
    workspace_is_city_scoped,
)

st.set_page_config(page_title="Mobility Readiness 2026", page_icon="🚇", layout="wide", initial_sidebar_state="expanded")
apply_theme()


@st.cache_data(show_spinner="Loading verified mobility artifacts...")
def load_dashboard_data():
    paths = project_paths()
    return paths, load_artifacts(paths)


paths, artifacts = load_dashboard_data()

city_options = sorted(HOST_CITIES)
city_context_key = "selected_city_context"
if st.session_state.get(city_context_key) not in city_options:
    st.session_state[city_context_key] = city_options[0]


def _sync_city_context() -> None:
    st.session_state[city_context_key] = st.session_state["city_focus"]

with st.sidebar:
    brand_block()
    st.markdown("<div class='sidebar-kicker'>Workspace</div>", unsafe_allow_html=True)
    mode_labels = active_workspace_labels()
    st.session_state["workspace"] = normalize_workspace(
        st.session_state.get("workspace")
    )
    mode = st.radio(
        "Workspace",
        active_workspace_keys(),
        index=0,
        format_func=mode_labels.get,
        label_visibility="collapsed",
        key="workspace",
    )
    selected_city = None
    if workspace_is_city_scoped(mode):
        st.markdown("<div class='sidebar-kicker'>City scope</div>", unsafe_allow_html=True)
        if st.session_state.get("city_focus") != st.session_state[city_context_key]:
            st.session_state["city_focus"] = st.session_state[city_context_key]
        selected_city = st.selectbox(
            "City focus",
            city_options,
            key="city_focus",
            on_change=_sync_city_context,
        )
    st.markdown("<div class='sidebar-kicker'>Data state</div>", unsafe_allow_html=True)
    if paths.data_root:
        sidebar_status(
            "Local source data detected",
            "The app still starts from compact derived artifacts; raw files are used only by the offline ETL.",
        )
    else:
        sidebar_status(
            "Cache-only preview",
            "Set MOBILITY_DATA_ROOT and run the offline ETL to rebuild complete versioned evidence.",
        )
    st.caption("Evidence statuses remain visible on every decision KPI.")

# Advanced comparison settings render inside the Overview tab (see resilience.py),
# not here - read the last-set values before this run's tabs render.
weights, include_estimates = resolve_weight_settings()

metrics = build_city_metrics(
    artifacts["visits"], artifacts["weather"], artifacts["uhi"], artifacts["poi"], artifacts["gtfs"],
    weights=weights, include_estimates=include_estimates,
)
try:
    artifacts.update(build_transportation_bundle(metrics, artifacts))
except ValueError as exc:
    st.error(
        "The transportation evidence registry failed validation. "
        "Rebuild the pinned factor artifact before using scenario results. "
        f"Details: {exc}"
    )
    st.stop()

if mode == "Overview":
    render_home(metrics, artifacts, weights)
else:
    render_decision_brief(metrics, artifacts, selected_city=selected_city, weights=weights)
