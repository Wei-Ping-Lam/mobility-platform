"""Tab 6 — Legacy & Scalability: 10-yr ROI, platform reuse, roadmap, environmental scoreboard."""

import streamlit as st
import pandas as pd
import plotly.express as px

from data import HOST_CITIES, PLOTLY_TEMPLATE


def render(metrics_df):
    st.markdown("### Beyond FIFA 2026: Legacy, Scalability & Long-Term Impact")
    st.caption(
        "Transit investments made for FIFA 2026 generate compounding returns for cities, "
        "residents, and future mega-events. This tab quantifies the 10-year legacy value."
    )

    # ── Long-term ROI projection ──────────────────────────────────────────────
    st.markdown("#### 10-Year Transit Investment ROI Projection")
    st.caption(
        "Projects annual economic return of FIFA-driven transit upgrades "
        "assuming 15% ridership growth in year 1, 3% annual growth thereafter, "
        "and $0.80 economic return per passenger-mile."
    )

    legacy_city = st.selectbox(
        "Select city for legacy analysis",
        list(HOST_CITIES.keys()),
        key="legacy_city",
    )
    lc_row = metrics_df[metrics_df["city"] == legacy_city].iloc[0]
    lc_transit = lc_row["transit_score"]
    lc_gap = lc_row["first_last_mile_gap"]
    lc_games = lc_row["games"]

    # Assume city implements full recommended intervention package
    base_capex = (
        max(0, 50 - lc_row["stops_0_5mi"]) * 45000   # bike stations needed
        + max(0, 70 - lc_transit) * 30000              # transit upgrade proxy
        + int(lc_gap) * 15000                          # gap closure cost
    )
    base_capex = max(500000, min(base_capex, 50_000_000))

    # Annual returns: FIFA year (yr 1) + ongoing years
    # Year 1: boosted by FIFA tourism
    annual_returns = []
    ridership_base = lc_row["capacity"] * 0.92 * lc_games * (lc_transit / 100) * 1.15
    ridership = ridership_base
    for yr in range(1, 11):
        wc_bonus = ridership * 0.80 * 25 if yr == 1 else 0  # FIFA year bonus: extra 25 miles avg trip
        annual_rev = ridership * 0.80 * 12 + wc_bonus       # $0.80 × avg 12 miles/trip
        co2_val = ridership * 12 * 0.21 / 1000 * 50         # kg CO₂ → tonnes × $50/tonne
        annual_returns.append({
            "Year": f"20{'26' if yr == 1 else str(25 + yr)}",
            "Economic Return ($M)": round((annual_rev + co2_val) / 1e6, 1),
            "Phase": "FIFA 2026" if yr == 1 else "Post-Event Legacy",
        })
        ridership = ridership * 1.03

    cumulative = 0
    payback_yr = None
    for i, yr_data in enumerate(annual_returns):
        cumulative += yr_data["Economic Return ($M)"] * 1e6
        if cumulative >= base_capex and payback_yr is None:
            payback_yr = i + 1

    roi_df = pd.DataFrame(annual_returns)
    fig_roi = px.bar(
        roi_df, x="Year", y="Economic Return ($M)",
        color="Phase",
        color_discrete_map={"FIFA 2026": "#facc15", "Post-Event Legacy": "#22c55e"},
        text="Economic Return ($M)",
        template=PLOTLY_TEMPLATE,
        height=340,
    )
    fig_roi.update_traces(texttemplate="%{text:.1f}M", textposition="outside", textfont_color="white")
    fig_roi.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(gridcolor="#1e3a5f"),
        legend=dict(orientation="h", y=-0.2),
    )
    if payback_yr:
        _pb_label = annual_returns[payback_yr - 1]["Year"]
        fig_roi.add_shape(
            type="line", xref="x", yref="paper",
            x0=_pb_label, x1=_pb_label, y0=0, y1=1,
            line=dict(color="#38bdf8", dash="dot", width=2),
        )
        fig_roi.add_annotation(
            x=_pb_label, y=1, yref="paper",
            text=f"Payback (yr {payback_yr})",
            showarrow=False, yanchor="bottom",
            font=dict(color="#38bdf8", size=11),
        )
    col_roi_left, col_roi_right = st.columns([3, 1])
    with col_roi_left:
        st.plotly_chart(fig_roi, width='stretch')
    with col_roi_right:
        st.metric("Estimated Capex", f"${base_capex/1e6:.1f}M")
        ten_yr = round(roi_df["Economic Return ($M)"].sum(), 0)
        st.metric("10-Year Return", f"${ten_yr:.0f}M")
        st.metric("Payback Period", f"{payback_yr} years" if payback_yr else ">10 years")
        st.metric("10-Year ROI", f"{round((ten_yr*1e6 / base_capex - 1)*100, 0):.0f}%")

    # ── Platform reuse framework ──────────────────────────────────────────────
    st.divider()
    st.markdown("#### Platform Reuse: Next Mega-Events")
    st.caption(
        "This mobility readiness framework is event-agnostic. "
        "The same GTFS + UHI + foot-traffic methodology applies directly to future events."
    )

    reuse_events = [
        {"Event": "Super Bowl LXI (2027)", "City": "New Orleans", "Venue Cap": "73,208",
         "Key Gap": "Suburban Superdome location; limited transit", "Platform Adaptation": "Swap GTFS feed, update climate data"},
        {"Event": "LA28 Summer Olympics (2028)", "City": "Los Angeles", "Venue Cap": "Multi-venue",
         "Key Gap": "Sprawling network; 15+ venues", "Platform Adaptation": "Multi-venue mode; modal split by event"},
        {"Event": "FIFA Women's World Cup 2027", "City": "TBD (US host)", "Venue Cap": "~60,000",
         "Key Gap": "Smaller venues, crowd management", "Platform Adaptation": "Capacity and schedule data update"},
        {"Event": "NCAA Final Four 2028", "City": "TBD", "Venue Cap": "~70,000",
         "Key Gap": "Short event window (3 days)", "Platform Adaptation": "Short-horizon demand model"},
    ]
    reuse_df = pd.DataFrame(reuse_events)
    st.dataframe(reuse_df, width='stretch', hide_index=True)

    # ── Implementation roadmap ────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Implementation Roadmap")

    roadmap_data = {
        "Phase": ["Phase 1 · Immediate\n(Now → Mar 2026)", "Phase 2 · Event Operations\n(Jun–Jul 2026)", "Phase 3 · Legacy\n(Aug 2026 → )"],
        "Duration": ["9 months", "6 weeks", "Ongoing"],
        "Actions": [
            "Deploy shuttle contracts · Launch bike-share expansions · Install pedestrian shade · Publish real-time mobility API",
            "Operate dynamic shuttle frequencies · Monitor crowd density · Activate heat-risk alerts · Manage P&R lots",
            "Maintain elevated transit frequency · Convert event infrastructure to permanent use · Publish open data for city planners",
        ],
        "Implementing Partners": [
            "Transit agencies (MARTA, DART, MBTA…) · FIFA Host City Liaisons · City DOTs",
            "Event Operations teams · Transit agency dispatchers · City emergency management",
            "City planning departments · USDOT · Transit agencies · Open data portals",
        ],
        "Success Metric": [
            "Shuttle contracts signed; bike-share stations installed",
            "Transit modal split ≥ 30% per match; heat-incident rate < 0.1%",
            "Ridership 15% above pre-FIFA baseline by 2027",
        ],
    }
    roadmap_df = pd.DataFrame(roadmap_data)
    for _, phase_row in roadmap_df.iterrows():
        with st.expander(phase_row["Phase"]):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Actions**\n\n{phase_row['Actions']}")
            with c2:
                st.markdown(f"**Partners**\n\n{phase_row['Implementing Partners']}")
            with c3:
                st.markdown(f"**Success Metric**\n\n{phase_row['Success Metric']}")

    # ── Environmental sustainability scoreboard ───────────────────────────────
    st.divider()
    st.markdown("#### Environmental & Social Impact Scoreboard (Full Tournament)")

    total_peak_v = metrics_df["peak_visitors"].sum() * metrics_df["games"].mean()
    # If all gaps addressed: assume 25% modal shift to transit
    cars_displaced = int(total_peak_v * 0.25)
    co2_tournament = round(cars_displaced * 30 * 0.21 / 1000, 0)   # 30 km avg trip, 0.21 kg/km
    co2_value_total = round(co2_tournament * 50, 0)
    heat_risk_total = metrics_df["heat_risk_visitors"].sum()

    env_cols = st.columns(4)
    env_metrics = [
        ("Cars Displaced\n(if gaps closed)", f"{cars_displaced:,}", "per match day"),
        ("CO₂ Saved\n(full tournament)", f"{co2_tournament:,.0f} t", "tonnes CO₂"),
        ("Carbon Value", f"${co2_value_total:,.0f}", "@ $50/tonne"),
        ("Heat-Risk Visitors\nAddressed", f"{heat_risk_total:,}", "across 11 cities"),
    ]
    for col, (label, val, sub) in zip(env_cols, env_metrics):
        with col:
            st.markdown(
                f"""<div class="kpi-card">
                <div class="kpi-val" style="font-size:1.6rem">{val}</div>
                <div class="kpi-sub">{label}<br><span style="color:#4ade80">{sub}</span></div>
                </div>""",
                unsafe_allow_html=True,
            )
