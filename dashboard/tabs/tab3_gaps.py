"""Tab 3 — Gap Analysis: first/last-mile gaps, heat stress, Transit Illusion, GTFS stop density."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data import HOST_CITIES, PLOTLY_TEMPLATE


def render(metrics_df):
    st.markdown("### First/Last-Mile Gap Analysis")
    st.caption(
        "Gap Score = function of transit under-capacity, summer heat, and urban heat island intensity. "
        "Higher = greater unmet mobility need."
    )

    col_gap1, col_gap2 = st.columns([3, 2])

    with col_gap1:
        # Bubble: transit score vs gap score, sized by capacity
        fig_gap = px.scatter(
            metrics_df,
            x="transit_score", y="first_last_mile_gap",
            size="capacity", color="avg_temp_c",
            color_continuous_scale="RdYlGn_r",
            hover_name="city",
            hover_data={"venue": True, "avg_uhi": True, "capacity": ":,"},
            size_max=40,
            labels={
                "transit_score": "Transit Infrastructure Score (0–100)",
                "first_last_mile_gap": "First/Last-Mile Gap Score",
                "avg_temp_c": "Avg Summer Temp (°C)",
            },
            template=PLOTLY_TEMPLATE,
            height=400,
        )
        # Quadrant lines
        fig_gap.add_hline(y=40, line_dash="dot", line_color="#475569", annotation_text="High gap threshold")
        fig_gap.add_vline(x=60, line_dash="dot", line_color="#475569", annotation_text="Low transit threshold")

        # Quadrant labels
        fig_gap.add_annotation(x=25, y=70, text="⚠️ HIGH PRIORITY\nWeak transit + High gap",
                                showarrow=False, font=dict(size=10, color="#f87171"), align="center")
        fig_gap.add_annotation(x=85, y=20, text="✅ RESILIENT\nStrong transit + Low gap",
                                showarrow=False, font=dict(size=10, color="#4ade80"), align="center")

        fig_gap.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f"),
            yaxis=dict(gridcolor="#1e3a5f"),
        )
        st.plotly_chart(fig_gap, width='stretch')

    with col_gap2:
        st.markdown("#### Heat Stress × Visitor Density Risk")
        # Scatter: UHI vs heat_score colored by composite
        fig_heat = px.scatter(
            metrics_df,
            x="avg_uhi", y="avg_temp_c",
            size="games",
            color="composite_score",
            color_continuous_scale=["#ef4444", "#facc15", "#22c55e"],
            range_color=[30, 95],
            hover_name="city",
            size_max=25,
            labels={
                "avg_uhi": "Avg Urban Heat Island (°C above rural)",
                "avg_temp_c": "June–July Avg Temperature (°C)",
                "composite_score": "Readiness",
            },
            template=PLOTLY_TEMPLATE,
            height=280,
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f"),
            yaxis=dict(gridcolor="#1e3a5f"),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig_heat, width='stretch')

        st.markdown("#### Gap Score Rankings")
        gap_table = metrics_df[["city", "first_last_mile_gap", "transit_score", "avg_temp_c"]].sort_values(
            "first_last_mile_gap", ascending=False
        )
        for _, r in gap_table.iterrows():
            bar_pct = int(min(r["first_last_mile_gap"], 100))
            cl = "score-lo" if r["first_last_mile_gap"] > 50 else "score-md" if r["first_last_mile_gap"] > 30 else "score-hi"
            st.markdown(
                f"**{r['city']}** — <span class='{cl}'>{r['first_last_mile_gap']:.0f}</span>",
                unsafe_allow_html=True
            )
            st.progress(bar_pct)

    st.divider()
    st.markdown("#### The Transit Illusion: City Reputation vs. Venue Reality")
    st.caption(
        "Many cities are known for world-class transit — but their FIFA venues sit in "
        "suburban areas far from rail coverage. GTFS stop-count data reveals the gap between "
        "a city's transit reputation and actual match-day access."
    )

    illusion_rows = []
    for _c, _m in HOST_CITIES.items():
        _row = metrics_df[metrics_df["city"] == _c]
        if _row.empty:
            continue
        illusion_rows.append({
            "City": _c,
            "Expert Reputation": _m["transit_score"],
            "GTFS Venue Reality": int(_row["transit_score"].values[0]),
            "Gap": _m["transit_score"] - int(_row["transit_score"].values[0]),
        })
    illusion_df = pd.DataFrame(illusion_rows).sort_values("Gap", ascending=False)

    col_ill1, col_ill2 = st.columns([3, 2])
    with col_ill1:
        fig_ill = go.Figure()
        # diagonal reference line (y=x)
        fig_ill.add_trace(go.Scatter(
            x=[0, 100], y=[0, 100],
            mode="lines",
            line=dict(color="#475569", dash="dash", width=1),
            showlegend=False, hoverinfo="skip",
        ))
        fig_ill.add_annotation(
            x=80, y=83, text="y = x (reality matches reputation)",
            showarrow=False, font=dict(size=9, color="#64748b"), textangle=-38,
        )
        for _, r in illusion_df.iterrows():
            color = "#f87171" if r["Gap"] > 30 else "#facc15" if r["Gap"] > 0 else "#4ade80"
            fig_ill.add_trace(go.Scatter(
                x=[r["Expert Reputation"]], y=[r["GTFS Venue Reality"]],
                mode="markers+text",
                marker=dict(size=16, color=color, line=dict(width=1, color="white")),
                text=[r["City"]],
                textposition="top center",
                textfont=dict(size=9, color="white"),
                name=r["City"],
                showlegend=False,
                hovertemplate=(
                    f"<b>{r['City']}</b><br>"
                    f"Expert estimate: {r['Expert Reputation']}<br>"
                    f"GTFS venue reality: {r['GTFS Venue Reality']}<br>"
                    f"Gap: {r['Gap']}<extra></extra>"
                ),
            ))
        fig_ill.add_annotation(x=12, y=75, text="✅ Better than expected",
                               showarrow=False, font=dict(size=10, color="#4ade80"))
        fig_ill.add_annotation(x=80, y=12, text="⚠️ Transit Illusion Zone",
                               showarrow=False, font=dict(size=10, color="#f87171"))
        fig_ill.update_layout(
            xaxis_title="Expert Transit Reputation (0–100)",
            yaxis_title="GTFS Venue Reality Score (0–100)",
            xaxis=dict(range=[0, 105], gridcolor="#1e3a5f"),
            yaxis=dict(range=[0, 105], gridcolor="#1e3a5f"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            template=PLOTLY_TEMPLATE,
            height=380,
            margin=dict(l=0, r=0, t=10, b=0),
        )
        st.plotly_chart(fig_ill, width='stretch')

    with col_ill2:
        st.markdown("**Illusion Gap Rankings**")
        st.caption("Positive gap = venue access worse than city reputation implies")
        for _, r in illusion_df.iterrows():
            gap_val = r["Gap"]
            color_cls = "score-lo" if gap_val > 30 else "score-md" if gap_val > 10 else "score-hi"
            direction = "▼" if gap_val > 0 else "▲"
            st.markdown(
                f"**{r['City']}** — Rep: {r['Expert Reputation']} → Reality: {r['GTFS Venue Reality']} "
                f"<span class='{color_cls}'>{direction}{abs(gap_val)}</span>",
                unsafe_allow_html=True,
            )
        st.divider()
        st.markdown(
            "**Key insight:** New York/NJ (MetLife) and Boston (Gillette) are famous for "
            "transit but their venues are suburban — match-day fans are overwhelmingly car-dependent. "
            "Seattle and Atlanta are the true leaders at the venue level.",
            unsafe_allow_html=False,
        )

    st.divider()
    st.markdown("#### Transit Stop Density Around Each Venue (GTFS Live Data)")
    st.caption("Stops counted within walking distance rings of the actual stadium — sourced from each city's transit agency GTFS feed.")

    stop_df = metrics_df[["city", "stops_0_5mi", "stops_1mi", "stops_2mi",
                           "nearest_stop_mi", "transit_source", "gtfs_agencies"]].copy()
    stop_df = stop_df.sort_values("stops_1mi", ascending=False)

    stop_melt = stop_df.melt(
        id_vars=["city", "transit_source"],
        value_vars=["stops_0_5mi", "stops_1mi", "stops_2mi"],
        var_name="radius", value_name="stop_count",
    )
    stop_melt["radius"] = stop_melt["radius"].map({
        "stops_0_5mi": "Within 0.5 mi",
        "stops_1mi":   "Within 1 mi",
        "stops_2mi":   "Within 2 mi",
    })

    fig_stops = px.bar(
        stop_melt,
        x="city", y="stop_count", color="radius",
        barmode="group",
        color_discrete_map={
            "Within 0.5 mi": "#38bdf8",
            "Within 1 mi":   "#818cf8",
            "Within 2 mi":   "#c084fc",
        },
        labels={"stop_count": "Transit Stops", "city": "", "radius": ""},
        template=PLOTLY_TEMPLATE,
        height=340,
        text_auto=True,
    )
    fig_stops.update_traces(textposition="outside", textfont=dict(size=9, color="white"))
    fig_stops.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=-0.2),
        xaxis=dict(gridcolor="#1e3a5f"),
        yaxis=dict(gridcolor="#1e3a5f"),
    )
    st.plotly_chart(fig_stops, width='stretch')

    # Nearest stop callout cards
    cols = st.columns(len(metrics_df))
    for col, (_, r) in zip(cols, stop_df.iterrows()):
        dist = r["nearest_stop_mi"]
        label = "🟢" if dist < 0.25 else "🟡" if dist < 1.0 else "🔴"
        est = " *" if r["transit_source"] == "estimated" else ""
        with col:
            st.metric(
                label=r["city"] + est,
                value=f"{dist:.2f} mi" if dist < 90 else "N/A",
                delta="nearest stop",
                delta_color="off",
            )
    st.caption("\\* Estimated (GTFS not available) · Distances from venue centroid to nearest transit stop")

    st.divider()
    st.markdown("#### Detailed Gap Metrics Table")
    tbl = metrics_df[["city", "venue", "capacity", "games", "transit_score",
                       "transit_source", "stops_0_5mi", "nearest_stop_mi",
                       "first_last_mile_gap", "avg_temp_c", "avg_uhi",
                       "transit_mode"]].copy()
    tbl.columns = ["City", "Venue", "Capacity", "Games", "Transit Score",
                   "Score Source", "Stops <=0.5mi", "Nearest Stop (mi)",
                   "Gap Score", "Avg Temp °C", "Avg UHI", "Primary Transit"]
    tbl = tbl.sort_values("Gap Score", ascending=False)
    st.dataframe(
        tbl.style
           .background_gradient(subset=["Gap Score"], cmap="RdYlGn_r", vmin=0, vmax=80)
           .background_gradient(subset=["Transit Score"], cmap="RdYlGn", vmin=5, vmax=100)
           .background_gradient(subset=["Stops <=0.5mi"], cmap="Blues", vmin=0, vmax=30)
           .format({"Capacity": "{:,.0f}", "Gap Score": "{:.1f}",
                    "Avg Temp °C": "{:.1f}", "Avg UHI": "{:.2f}",
                    "Nearest Stop (mi)": "{:.3f}"}),
        width='stretch',
        hide_index=True,
    )
