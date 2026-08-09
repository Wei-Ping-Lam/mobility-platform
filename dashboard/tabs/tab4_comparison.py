"""Tab 4 — City Comparison: radar, ranking bar, component heatmap across all cities."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data import PLOTLY_TEMPLATE


def render(metrics_df):
    st.markdown("### Multi-City Mobility Comparison")

    col_radar, col_bar = st.columns([1, 1])

    with col_radar:
        st.markdown("#### Radar: All Cities Across 4 Dimensions")
        categories = ["Transit Score", "Heat Safety", "Low UHI", "Accessibility"]
        radar_fig = go.Figure()
        colors = px.colors.qualitative.Plotly

        for i, (_, row) in enumerate(metrics_df.iterrows()):
            vals = [row["transit_score"], row["heat_score"],
                    row["uhi_score"], row["accessibility_score"]]
            vals_closed = vals + [vals[0]]
            cats_closed = categories + [categories[0]]
            radar_fig.add_trace(go.Scatterpolar(
                r=vals_closed,
                theta=cats_closed,
                mode="lines+markers",
                name=row["city"],
                line=dict(color=colors[i % len(colors)], width=1.5),
                marker=dict(size=4),
                opacity=0.8,
            ))

        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e3a5f", tickfont=dict(size=9)),
                angularaxis=dict(gridcolor="#1e3a5f"),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            template=PLOTLY_TEMPLATE,
            legend=dict(font=dict(size=9), orientation="v", x=1.05),
            height=440,
            margin=dict(l=40, r=120, t=20, b=20),
        )
        st.plotly_chart(radar_fig, width='stretch')

    with col_bar:
        st.markdown("#### Composite Readiness Score")
        fig_bar = px.bar(
            metrics_df.sort_values("composite_score"),
            x="composite_score", y="city",
            orientation="h",
            color="composite_score",
            color_continuous_scale=["#ef4444", "#facc15", "#22c55e"],
            range_color=[30, 95],
            text="composite_score",
            labels={"composite_score": "Score", "city": ""},
            template=PLOTLY_TEMPLATE,
            height=420,
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside", textfont_color="white")
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            coloraxis_showscale=False,
            margin=dict(l=0, r=40, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f", range=[0, 105]),
            yaxis=dict(gridcolor="#1e3a5f"),
        )
        st.plotly_chart(fig_bar, width='stretch')

    st.divider()
    st.markdown("#### Component Breakdown Heatmap")

    heat_data = metrics_df.set_index("city")[
        ["transit_score", "heat_score", "uhi_score", "accessibility_score", "composite_score"]
    ].rename(columns={
        "transit_score": "Transit", "heat_score": "Heat Safety",
        "uhi_score": "Low UHI", "accessibility_score": "Venue Access",
        "composite_score": "COMPOSITE",
    })

    fig_hm = px.imshow(
        heat_data.T,
        color_continuous_scale="RdYlGn",
        zmin=0, zmax=100,
        text_auto=".0f",
        aspect="auto",
        template=PLOTLY_TEMPLATE,
        height=280,
    )
    fig_hm.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(tickangle=-30),
    )
    st.plotly_chart(fig_hm, width='stretch')
