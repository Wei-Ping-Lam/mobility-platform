"""
FIFA 2026 Host City Mobility Readiness Platform
Track 1: Transportation & Access
Rice World Cup Hackathon 2026

This file is the thin orchestrator: page config, styling, data loading, the
KPI header, and tab dispatch. Each tab's content lives in its own module
under tabs/ so team members can work on separate tabs without touching this
file or each other's.
"""

import streamlit as st

from data import (
    load_store_visits,
    load_store_visits_by_category,
    load_uhi,
    load_spend_origins,
    build_city_metrics,
    apply_weights,
    kpi_html,
    DEFAULT_WEIGHTS,
)
from tabs import (
    tab1_overview,
    tab2_demand,
    tab3_gaps,
    tab4_comparison,
    tab5_planner,
    tab6_legacy,
)

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="FIFA 2026 Mobility Readiness",
    page_icon="⚽",
    layout="wide",
)

# ── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body, [data-testid="stAppViewContainer"] { background: #07111f; }
h1,h2,h3,h4 { color: #ffffff !important; letter-spacing: -0.02em; }
p, li, label { color: #c9d8e8; }
.kpi-row { display: flex; gap: 12px; margin-bottom: 24px; }
.kpi-card {
    flex: 1;
    background: linear-gradient(145deg, #0f2136, #0a1929);
    border: 1px solid #1e4a7a;
    border-radius: 14px;
    padding: 18px 20px;
    text-align: center;
}
.kpi-val  { font-size: 2.1rem; font-weight: 800; color: #38bdf8; line-height: 1; }
.kpi-sub  { font-size: 0.72rem; color: #7fb3d3; text-transform: uppercase;
            letter-spacing: 0.1em; margin-top: 6px; }
.score-hi { color: #4ade80; font-weight: 700; }
.score-md { color: #facc15; font-weight: 700; }
.score-lo { color: #f87171; font-weight: 700; }
.city-pill {
    display: inline-block;
    background: #0f3460; color: #60a5fa;
    border-radius: 20px; padding: 3px 12px;
    font-size: 0.8rem; font-weight: 600;
    margin: 2px;
}
.stTabs [data-baseweb="tab-list"] { background: #0d1f33; border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"]      { color: #7fb3d3; border-radius: 8px; }
.stTabs [aria-selected="true"]    { background: #1e4a7a !important; color: #ffffff !important; }
.stDataFrame { border-radius: 10px; overflow: hidden; }
div[data-testid="metric-container"] { background: #0f2136; border-radius: 10px; padding: 8px 12px; }
</style>
""", unsafe_allow_html=True)

# ─ Load data ─────────────────────────────────────────────────────────────────
visits_df      = load_store_visits()
visits_cat_df  = load_store_visits_by_category()
uhi_df         = load_uhi()
origins_df     = load_spend_origins()

# Use a stable hash so cache is only busted when raw data changes
_vh = str(len(visits_df))
_uh = str(len(uhi_df))
metrics_df = build_city_metrics(_vh, _uh)

# ─ Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<h1 style='text-align:center;font-size:2.2rem;'>⚽ FIFA 2026 Host City Mobility Readiness Platform</h1>",
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align:center;color:#7fb3d3;margin-top:-10px;'>"
    "Predicting visitor movement · Identifying first/last-mile gaps · "
    "Comparing transit resilience across all 11 US host cities</p>",
    unsafe_allow_html=True,
)

# ─ Readiness score weights (was sidebar sliders; now an inline expander) ────
with st.expander("⚙️ Adjust Readiness Score Weights", expanded=False):
    wc1, wc2, wc3, wc4 = st.columns(4)
    with wc1:
        w_transit = st.slider("Transit Infrastructure", 0.10, 0.60, DEFAULT_WEIGHTS["transit"], 0.05)
    with wc2:
        w_heat = st.slider("Heat/Climate", 0.05, 0.40, DEFAULT_WEIGHTS["heat"], 0.05)
    with wc3:
        w_uhi = st.slider("Urban Heat Island", 0.05, 0.30, DEFAULT_WEIGHTS["uhi"], 0.05)
    with wc4:
        w_access = st.slider("Venue Accessibility", 0.10, 0.50, DEFAULT_WEIGHTS["access"], 0.05)

    total_w = w_transit + w_heat + w_uhi + w_access
    if abs(total_w - 1.0) > 0.01:
        st.caption(f"⚠ Weights sum to {total_w:.2f}; normalizing to 1.0")
    st.caption("Data: Veraset/SafeGraph · Urban Heat Index · Weather observations · Rice University World Cup Hackathon 2026")

metrics_df, transit_weight_ratio = apply_weights(metrics_df, {
    "transit": w_transit, "heat": w_heat, "uhi": w_uhi, "access": w_access,
})

st.divider()

# ─ Top KPIs ──────────────────────────────────────────────────────────────────
us_games         = metrics_df["games"].sum()   # 78 — US-hosted matches
avg_readiness    = metrics_df["composite_score"].mean()
total_econ_b     = metrics_df["economic_impact_m"].sum() / 1000
total_heat_risk  = metrics_df["heat_risk_visitors"].sum()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.markdown(kpi_html("11", "US Host Cities"), unsafe_allow_html=True)
with col2:
    st.markdown(kpi_html(f"{us_games}", "US-Hosted Matches"), unsafe_allow_html=True)
with col3:
    st.markdown(kpi_html(f"${total_econ_b:.1f}B", "Projected Economic Impact"), unsafe_allow_html=True)
with col4:
    st.markdown(kpi_html(f"{total_heat_risk:,}", "Visitors at Heat Risk"), unsafe_allow_html=True)
with col5:
    st.markdown(kpi_html(f"{avg_readiness:.0f}/100", "Avg Mobility Readiness"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─ Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺️ City Overview",
    "📈 Visitor Demand",
    "⚠️ Gap Analysis",
    "📊 City Comparison",
    "🔧 Intervention Planner",
    "🌱 Legacy & Scalability",
])

with tab1:
    tab1_overview.render(metrics_df)

with tab2:
    tab2_demand.render(metrics_df, visits_df, visits_cat_df, origins_df)

with tab3:
    tab3_gaps.render(metrics_df)

with tab4:
    tab4_comparison.render(metrics_df)

with tab5:
    tab5_planner.render(metrics_df, transit_weight_ratio)

with tab6:
    tab6_legacy.render(metrics_df)
