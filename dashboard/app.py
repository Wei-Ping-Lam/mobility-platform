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

from dashboard.domain.scoring import DEFAULT_WEIGHTS, build_city_metrics, normalize_weights  # noqa: E402
from dashboard.mobility_platform.config import project_paths  # noqa: E402
from dashboard.mobility_platform.mappings import HOST_CITIES  # noqa: E402
from dashboard.mobility_platform.sources import RICE_COLLECTION  # noqa: E402
from dashboard.ui.data import load_artifacts  # noqa: E402
from dashboard.ui.theme import apply_theme, brand_block, sidebar_status  # noqa: E402
from dashboard.ui.views import render_executive, render_explorer, render_methods  # noqa: E402

st.set_page_config(page_title="Mobility Readiness 2026", page_icon="🚇", layout="wide", initial_sidebar_state="expanded")
apply_theme()


@st.cache_data(show_spinner="Loading verified mobility artifacts...")
def load_dashboard_data():
    paths = project_paths()
    return paths, load_artifacts(paths)


paths, artifacts = load_dashboard_data()

with st.sidebar:
    brand_block()
    st.markdown("<div class='sidebar-kicker'>Workspace</div>", unsafe_allow_html=True)
    mode_labels = {
        "Executive": "City overview",
        "Explorer": "City explorer",
        "Methods & QA": "Methods & QA",
    }
    mode = st.radio(
        "Workspace",
        list(mode_labels),
        index=0,
        format_func=mode_labels.get,
        label_visibility="collapsed",
    )
    st.markdown("<div class='sidebar-kicker'>Scope and scoring</div>", unsafe_allow_html=True)
    selected_city = st.selectbox("City focus", ["All cities"] + sorted(HOST_CITIES), index=0)
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
        index=profile_options.index("rice_supplied_data"),
        format_func=profile_labels.get,
    )
    weights = dict(DEFAULT_WEIGHTS[profile])
    with st.expander("Tune score weights"):
        weights = {
            "transit": st.slider("Transit", 0.0, 1.0, float(weights["transit"]), 0.05),
            "heat": st.slider("Heat safety", 0.0, 1.0, float(weights["heat"]), 0.05),
            "uhi": st.slider("UHI safety", 0.0, 1.0, float(weights["uhi"]), 0.05),
            "access": st.slider("Venue support", 0.0, 1.0, float(weights["access"]), 0.05),
        }
    weights = normalize_weights(weights)
    if profile == "rice_supplied_data":
        st.caption(f"This lens uses only {RICE_COLLECTION} weather, UHI, and venue-support evidence; it does not score transit service.")
    include_estimates = st.checkbox(
        "Include estimated values",
        value=False,
        help="Strict mode excludes estimated components from rankings. Enable this only for sensitivity exploration.",
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

metrics = build_city_metrics(
    artifacts["visits"], artifacts["weather"], artifacts["uhi"], artifacts["poi"], artifacts["gtfs"],
    weights=weights, include_estimates=include_estimates,
)

if selected_city != "All cities" and selected_city in metrics["city"].values:
    selected_metrics = metrics[metrics["city"] == selected_city].copy()
else:
    selected_metrics = metrics

if mode == "Executive":
    render_executive(selected_metrics, artifacts, supplied_data_lens=weights["transit"] == 0)
elif mode == "Explorer":
    render_explorer(metrics, artifacts, selected_city if selected_city != "All cities" else metrics.iloc[0]["city"], weights, include_estimates)
else:
    render_methods(metrics, artifacts)
