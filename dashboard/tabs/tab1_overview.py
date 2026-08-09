"""Tab 1 — City Overview: map of all host cities + rankings + score radar."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from data import PLOTLY_TEMPLATE, MAP_STYLE, score_class


def render(metrics_df):
    st.markdown("### Mobility Readiness by Host City")

    city_options = ["All Cities"] + sorted(metrics_df["city"].tolist())
    focus_city = st.selectbox("Focus City", city_options, index=0, key="tab1_focus_city")
    display_df = (
        metrics_df[metrics_df["city"] == focus_city]
        if focus_city != "All Cities"
        else metrics_df
    )

    col_map, col_detail = st.columns([2, 1])

    with col_map:
        st.caption("Bubble size = matches hosted · Color = composite readiness score")

        fig_map = px.scatter_mapbox(
            display_df,
            lat="lat", lon="lon",
            size="games",
            color="composite_score",
            color_continuous_scale=["#ef4444", "#facc15", "#22c55e"],
            range_color=[30, 95],
            size_max=28,
            hover_name="city",
            hover_data={
                "venue": True,
                "composite_score": ":.1f",
                "transit_score": True,
                "games": True,
                "lat": False, "lon": False,
            },
            zoom=3.0,
            center={"lat": 38.5, "lon": -96},
            mapbox_style=MAP_STYLE,
            height=480,
        )
        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=0, b=0),
            coloraxis_colorbar=dict(
                title="Readiness",
                tickvals=[30, 50, 70, 90],
                ticktext=["30 Low", "50", "70", "90 High"],
                thickness=12,
                len=0.7,
            ),
        )
        # Add city labels
        fig_map.add_trace(go.Scattermapbox(
            lat=display_df["lat"],
            lon=display_df["lon"],
            mode="text",
            text=display_df["city"],
            textfont=dict(size=10, color="white"),
            textposition="top center",
            hoverinfo="skip",
            showlegend=False,
        ))
        st.plotly_chart(fig_map, width='stretch')

    with col_detail:
        st.markdown("### City Rankings")
        for _, row in display_df.iterrows():
            sc = row["composite_score"]
            cl = score_class(sc)
            icon = "🟢" if sc >= 70 else "🟡" if sc >= 50 else "🔴"
            st.markdown(
                f"{icon} **{row['city']}**  "
                f"<span class='{cl}'>{sc:.0f}</span>/100 · "
                f"{row['games']} games · {row['deepest_round']}",
                unsafe_allow_html=True,
            )
            st.progress(int(sc), text=None)

        st.divider()
        st.markdown("#### Score Breakdown")
        if focus_city != "All Cities":
            row = metrics_df[metrics_df["city"] == focus_city].iloc[0]
        else:
            row = metrics_df.iloc[0]  # top city

        radar_fig = go.Figure(go.Scatterpolar(
            r=[row["transit_score"], row["heat_score"],
               row["uhi_score"], row["accessibility_score"], row["transit_score"]],
            theta=["Transit", "Heat Safety", "Low UHI", "Accessibility", "Transit"],
            fill="toself",
            fillcolor="rgba(56,189,248,0.15)",
            line=dict(color="#38bdf8", width=2),
            name=row["city"],
        ))
        radar_fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e3a5f"),
                angularaxis=dict(gridcolor="#1e3a5f"),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            template=PLOTLY_TEMPLATE,
            showlegend=False,
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(radar_fig, width='stretch')
        st.caption(f"Profile for **{row['city']}** · Venue: {row['venue']}")
