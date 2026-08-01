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

from dashboard.domain.scoring import DEFAULT_WEIGHTS, build_city_metrics, normalize_weights
from dashboard.mobility_platform.config import project_paths
from dashboard.ui.data import load_artifacts
from dashboard.ui.theme import apply_theme
from dashboard.ui.views import render_executive, render_explorer, render_methods


st.set_page_config(page_title="FIFA Mobility Readiness", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")
apply_theme()


@st.cache_data(show_spinner="Loading derived mobility artifacts…")
def load_dashboard_data():
    paths = project_paths()
    return paths, load_artifacts(paths)


paths, artifacts = load_dashboard_data()

with st.sidebar:
    st.markdown("## ⚽ FIFA Mobility Readiness")
    st.caption("Evidence-first host-city access analysis")
    mode = st.radio("View", ["Executive", "Explorer", "Methods & QA"], index=0)
    st.divider()
    selected_city = st.selectbox("Focus city", ["All cities"] + sorted(artifacts["gtfs"].keys() or []), index=0)
    profile = st.selectbox("Weight profile", list(DEFAULT_WEIGHTS), index=0)
    weights = dict(DEFAULT_WEIGHTS[profile])
    with st.expander("Custom weights"):
        weights = {
            "transit": st.slider("Transit", 0.0, 1.0, float(weights["transit"]), 0.05),
            "heat": st.slider("Heat safety", 0.0, 1.0, float(weights["heat"]), 0.05),
            "uhi": st.slider("UHI safety", 0.0, 1.0, float(weights["uhi"]), 0.05),
            "access": st.slider("Venue support", 0.0, 1.0, float(weights["access"]), 0.05),
        }
    weights = normalize_weights(weights)
    include_estimates = st.checkbox("Include estimated values", value=False, help="Strict mode excludes estimated components from rankings.")
    st.divider()
    if paths.data_root:
        st.caption(f"Raw data root detected: `{paths.data_root.name}`")
    else:
        st.warning("Raw data root not detected. Run the offline ETL with MOBILITY_DATA_ROOT.")
    st.caption("Raw datasets are never loaded by the dashboard startup path.")

metrics = build_city_metrics(
    artifacts["visits"], artifacts["weather"], artifacts["uhi"], artifacts["poi"], artifacts["gtfs"],
    weights=weights, include_estimates=include_estimates,
)

if selected_city != "All cities" and selected_city in metrics["city"].values:
    selected_metrics = metrics[metrics["city"] == selected_city].copy()
else:
    selected_metrics = metrics

if mode == "Executive":
    render_executive(selected_metrics, artifacts)
elif mode == "Explorer":
    render_explorer(metrics, artifacts, selected_city if selected_city != "All cities" else metrics.iloc[0]["city"], weights, include_estimates)
else:
    render_methods(metrics, artifacts)
