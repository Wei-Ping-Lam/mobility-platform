"""Tab 2 — Visitor Demand: foot-traffic forecast, category surge, origins, economic impact."""

import streamlit as st
import pandas as pd
import plotly.express as px

from data import (
    HOST_CITIES,
    PLOTLY_TEMPLATE,
    FIFA_RELEVANT_CATEGORIES,
    compute_category_surge,
    demand_time_series,
)

DEFAULT_CITY = "Dallas"


def render(metrics_df, visits_df, visits_cat_df, origins_df):
    st.markdown("### Visitor Demand Prediction & World Cup Surge Forecast")
    st.caption(
        "**Data note:** Daily visits = mobile-device-derived foot traffic to retail and commercial locations "
        "(restaurants, entertainment, services) across the metro market area — sourced from Veraset/SafeGraph. "
        "This is a proxy for overall city mobility demand, not stadium attendance. "
        "World Cup surge multipliers are **category-specific**: derived by blending published FIFA economic-impact "
        "benchmarks (US Travel Assoc. 2019; Baade & Matheson 2016; FIFA 2022/2018 LOC Reports) with each "
        "category's historical p90/median variability from the actual store-visits dataset."
    )

    col_ts, col_peak = st.columns([3, 1])

    with col_ts:
        if visits_df.empty:
            st.warning("Store visit data not loaded. Check data path and retry.")
        else:
            ts_city = st.selectbox("Select city for time-series view", list(HOST_CITIES.keys()),
                                   index=list(HOST_CITIES.keys()).index(DEFAULT_CITY),
                                   key="ts_city")
            ts_meta = HOST_CITIES[ts_city]
            fig_ts = demand_time_series(visits_df, ts_city, ts_meta)
            if fig_ts:
                st.plotly_chart(fig_ts, width='stretch')
            else:
                st.info("No visit data found for this market in the loaded partitions.")

    with col_peak:
        st.markdown("#### Peak Match Day Estimates")
        st.caption("Capacity × 1.25 surge factor")
        for _, row in metrics_df.sort_values("capacity", ascending=False).iterrows():
            st.metric(
                label=row["city"],
                value=f"{row['peak_visitors']:,}",
                delta=f"{row['games']} matches",
            )

    st.divider()
    st.markdown("#### Category-Specific World Cup Demand Surge")
    st.caption(
        "Multiplier = FIFA category benchmark × local variability adjustment (p90/median from store-visits data). "
        "Only FIFA-relevant categories shown (benchmark > 1.2×). "
        "Sources: [A] US Travel Assoc. 2019 · [B] Baade & Matheson, J. Sports Econ. 2016 · "
        "[C] FIFA 2022 LOC Report · [D] FIFA 2018 Economic Impact Assessment"
    )

    surge_city = st.selectbox(
        "Select city for category breakdown",
        list(HOST_CITIES.keys()),
        index=list(HOST_CITIES.keys()).index(DEFAULT_CITY),
        key="surge_city",
    )
    surge_mk = HOST_CITIES[surge_city]["market_key"]
    surge_df = compute_category_surge(visits_cat_df, surge_mk)

    if not surge_df.empty:
        surge_show = surge_df[surge_df["Category"].isin(FIFA_RELEVANT_CATEGORIES)].copy()
        if surge_show.empty:
            surge_show = surge_df.head(8)

        col_surge1, col_surge2 = st.columns([3, 2])

        with col_surge1:
            surge_melt = surge_show.melt(
                id_vars="Category",
                value_vars=["Baseline Visits/Day", "Projected Visits/Day"],
                var_name="Scenario", value_name="Daily Visits",
            )
            surge_melt["Category"] = surge_melt["Category"].str.replace(
                " and ", " & ", regex=False
            )
            fig_surge = px.bar(
                surge_melt,
                x="Daily Visits", y="Category",
                color="Scenario",
                barmode="group",
                orientation="h",
                color_discrete_map={
                    "Baseline Visits/Day":   "#475569",
                    "Projected Visits/Day":  "#38bdf8",
                },
                labels={"Daily Visits": "Daily Visits", "Category": ""},
                template=PLOTLY_TEMPLATE,
                height=max(280, len(surge_show) * 55),
            )
            fig_surge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", y=-0.15),
                xaxis=dict(gridcolor="#1e3a5f"),
                yaxis=dict(gridcolor="#1e3a5f"),
            )
            st.plotly_chart(fig_surge, width="stretch")

        with col_surge2:
            st.markdown("**Multiplier breakdown**")
            tbl_cols = ["Category", "FIFA Benchmark", "Hist. Variability",
                        "Projected Multiplier", "Source"]
            tbl = surge_show[tbl_cols].copy()
            tbl["Category"] = tbl["Category"].str.replace(" and ", " & ", regex=False)
            tbl["Projected Multiplier"] = tbl["Projected Multiplier"].apply(
                lambda x: f"{x:.2f}×"
            )
            tbl["FIFA Benchmark"] = tbl["FIFA Benchmark"].apply(lambda x: f"{x:.1f}×")
            tbl["Hist. Variability"] = tbl["Hist. Variability"].apply(
                lambda x: f"{x:.2f}×"
            )
            st.dataframe(tbl, hide_index=True, width="stretch")
    else:
        st.info("Category data not available for this market in the loaded partitions.")

    st.divider()
    st.markdown("#### Visitor Origin Intelligence")
    st.caption(
        "Home-state origins of consumers visiting each market — sourced from Veraset/SafeGraph spend-pattern mobility data. "
        "Reveals existing fan corridors and informs intercity transport planning."
    )

    if not origins_df.empty:
        col_orig1, col_orig2 = st.columns([1, 2])
        with col_orig1:
            # Market name mapping from spend dataset to HOST_CITIES
            market_map = {
                "San Francisco Bay Area": "San Francisco",
                "New York/New Jersey": "New York/NJ",
                "Los Angeles": "Los Angeles",
                "Dallas": "Dallas",
                "Houston": "Houston",
                "Atlanta": "Atlanta",
                "Miami": "Miami",
                "Seattle": "Seattle",
                "Boston": "Boston",
                "Kansas City": "Kansas City",
                "Philadelphia": "Philadelphia",
            }
            available_markets = [m for m in origins_df["market"].unique() if m in market_map]
            origin_market = st.selectbox(
                "Select market",
                available_markets,
                key="origin_market",
            )
        with col_orig2:
            mkt_data = (
                origins_df[origins_df["market"] == origin_market]
                .sort_values("count", ascending=False)
                .head(12)
            )
            fig_orig = px.bar(
                mkt_data,
                x="count", y="home_state",
                orientation="h",
                color="count",
                color_continuous_scale=["#1e4a7a", "#38bdf8"],
                labels={"count": "Visitor Count", "home_state": "Home State"},
                template=PLOTLY_TEMPLATE,
                height=320,
            )
            fig_orig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(gridcolor="#1e3a5f"),
                yaxis=dict(gridcolor="#1e3a5f"),
            )
            st.plotly_chart(fig_orig, width='stretch')
    else:
        st.info("Visitor origin data not loaded — check spend-patterns-rice/ data path.")

    # Economic impact by city
    st.divider()
    st.markdown("#### Projected Economic Impact by Host City")
    st.caption("Estimate: venue capacity × 95% attendance × $280/visitor/match-day × 1.42 regional multiplier (sports economics benchmark)")
    econ_df = metrics_df[["city", "economic_impact_m", "games"]].sort_values("economic_impact_m", ascending=False).copy()
    econ_df["impact_label"] = econ_df["economic_impact_m"].apply(lambda x: f"${x:,.0f}M")
    fig_econ = px.bar(
        econ_df, x="city", y="economic_impact_m",
        color="economic_impact_m",
        color_continuous_scale=["#1e4a7a", "#22c55e"],
        text="impact_label",
        labels={"economic_impact_m": "Impact ($M)", "city": ""},
        template=PLOTLY_TEMPLATE,
        height=320,
    )
    fig_econ.update_traces(textposition="outside", textfont_color="white")
    fig_econ.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=10, b=0),
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(title="Economic Impact ($M)", gridcolor="#1e3a5f"),
    )
    st.plotly_chart(fig_econ, width='stretch')
