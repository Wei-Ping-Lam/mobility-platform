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
from dashboard.domain.scoring import DEFAULT_WEIGHTS, build_city_metrics, normalize_weights  # noqa: E402
from dashboard.mobility_platform.config import project_paths  # noqa: E402
from dashboard.mobility_platform.mappings import HOST_CITIES  # noqa: E402
from dashboard.mobility_platform.sources import RICE_COLLECTION  # noqa: E402
from dashboard.ui.data import load_artifacts  # noqa: E402
from dashboard.ui.pages.home import render_home  # noqa: E402
from dashboard.ui.pages.overview import render_decision_brief  # noqa: E402
from dashboard.ui.theme import apply_theme, brand_block, sidebar_status  # noqa: E402
from dashboard.ui.views import render_explorer, render_methods  # noqa: E402

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
    mode_labels = {
        "Overview": "Portfolio",
        "City Brief": "City action plan",
        "Explorer": "Scenario explorer",
        "Methods & QA": "Methods",
    }
    mode = st.radio(
        "Workspace",
        list(mode_labels),
        index=0,
        format_func=mode_labels.get,
        label_visibility="collapsed",
        key="workspace",
    )
    selected_city = None
    if mode in {"City Brief", "Explorer"}:
        st.markdown("<div class='sidebar-kicker'>City scope</div>", unsafe_allow_html=True)
        if st.session_state.get("city_focus") != st.session_state[city_context_key]:
            st.session_state["city_focus"] = st.session_state[city_context_key]
        selected_city = st.selectbox(
            "City focus",
            city_options,
            key="city_focus",
            on_change=_sync_city_context,
        )
    with st.expander("Advanced comparison settings", expanded=False):
        profile_labels = {
            "balanced": "Balanced mobility",
            "transit_access": "Transit and access",
            "heat_resilience": "Heat resilience",
            "sustainability": "Sustainability",
            "rice_supplied_data": "Rice supplied-data lens",
        }
        profile_options = list(DEFAULT_WEIGHTS)
        profile = st.selectbox(
            "Weight profile",
            profile_options,
            index=profile_options.index("balanced"),
            format_func=profile_labels.get,
        )
        weights = dict(DEFAULT_WEIGHTS[profile])
        st.caption("Readiness gives the high-level orientation; task-specific evidence below should drive decisions.")
        st.markdown("##### Tune score weights")
        weights = {
            "transit": st.slider("Transit", 0.0, 1.0, float(weights["transit"]), 0.05),
            "heat": st.slider("Heat safety", 0.0, 1.0, float(weights["heat"]), 0.05),
            "uhi": st.slider("UHI safety", 0.0, 1.0, float(weights["uhi"]), 0.05),
            "access": st.slider("Venue support", 0.0, 1.0, float(weights["access"]), 0.05),
        }
        if profile == "rice_supplied_data":
            st.caption(f"This lens uses only {RICE_COLLECTION} weather, UHI, and venue-support evidence; it does not score transit service.")
        include_estimates = st.checkbox(
            "Include estimated values",
            value=False,
            help="Strict mode excludes estimated components from rankings. Enable this only for sensitivity exploration.",
        )
    weights = normalize_weights(weights)
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
elif mode == "City Brief":
    render_decision_brief(metrics, artifacts, selected_city=selected_city, weights=weights)
elif mode == "Explorer":
    render_explorer(metrics, artifacts, selected_city or str(metrics.iloc[0]["city"]), weights, include_estimates)
else:
    render_methods(metrics, artifacts)
