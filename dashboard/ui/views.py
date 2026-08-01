"""Executive, Explorer, and Methods/QA Streamlit views."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.scoring import DEFAULT_WEIGHTS, intervention_result
from dashboard.models.demand import scenario_band, seasonal_baseline, validation_metrics
from dashboard.mobility_platform.contracts import ScenarioConfig
from .theme import metric_card, status_label


TEMPLATE = "plotly_dark"


def _chart_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        template=TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=12, r=12, t=32, b=12),
        legend=dict(orientation="h", y=-0.2),
    )
    return fig


def _safe(value: Any, suffix: str = "") -> str:
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return "N/A"
    if isinstance(value, float):
        return f"{value:,.1f}{suffix}"
    return f"{value:,}{suffix}" if isinstance(value, (int, np.integer)) else f"{value}{suffix}"


def render_executive(metrics: pd.DataFrame, artifacts: dict[str, Any]) -> None:
    st.markdown("<div class='eyebrow'>Decision view · evidence first</div>", unsafe_allow_html=True)
    st.title("Host City Mobility Readiness")
    st.caption("A transparent comparison of venue access, heat exposure, transit evidence, and scenario pressure for FIFA 2026.")
    rankable = metrics[metrics["score"].notna()].copy()
    unavailable = metrics[metrics["score"].isna()].copy()
    cols = st.columns(4)
    values = [
        (str(len(metrics)), "Host cities"),
        (str(len(rankable)), "Rankable with observed evidence"),
        (_safe(metrics["games"].sum()), "Scheduled matches"),
        (_safe(metrics["data_coverage"].mean() * 100, "%"), "Mean evidence coverage"),
    ]
    for col, (value, label) in zip(cols, values):
        with col:
            st.markdown(metric_card(value, label), unsafe_allow_html=True)

    if unavailable.any(axis=None):
        st.warning("Strict evidence mode excludes cities with incomplete core evidence from the ranking. Open Methods & QA for the exact gaps.")

    col_map, col_table = st.columns([1.45, 1])
    with col_map:
        st.markdown("#### Venue-level readiness map")
        map_df = metrics.copy()
        map_df["display_score"] = map_df["score"].fillna(0)
        fig = px.scatter_mapbox(
            map_df,
            lat="lat", lon="lon", size="games", color="display_score",
            color_continuous_scale=["#ef6b73", "#ffd166", "#63e6a2"], range_color=[0, 100],
            hover_name="city", hover_data={"venue": True, "score_status": True, "display_score": ":.1f", "lat": False, "lon": False},
            zoom=3.0, center={"lat": 38.5, "lon": -96}, mapbox_style="carto-darkmatter", height=520,
        )
        fig.update_layout(coloraxis_colorbar_title="Readiness", margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Markers use actual stadium coordinates. Unrankable cities remain visible but are not assigned a readiness color.")
    with col_table:
        st.markdown("#### Priority view")
        display = metrics[["city", "score", "score_status", "first_last_mile_gap", "transit_score", "heat_score"]].copy()
        display.columns = ["City", "Score", "Status", "Gap", "Transit", "Heat safety"]
        display["Score"] = display["Score"].round(1)
        display["Gap"] = display["Gap"].round(1)
        st.dataframe(display, hide_index=True, use_container_width=True)
        st.markdown("#### How to read this")
        st.markdown("A score is rankable only when the required dimensions have observed or derived evidence. Estimated values are never silently mixed into the default ranking.")

    if not rankable.empty:
        st.markdown("#### Strongest observed evidence gaps")
        gap = rankable.sort_values("first_last_mile_gap", ascending=False).head(3)
        cols = st.columns(len(gap))
        for col, (_, row) in zip(cols, gap.iterrows()):
            with col:
                st.markdown(metric_card(_safe(row["first_last_mile_gap"]), f"{row['city']} gap score", row["score_status"]), unsafe_allow_html=True)


def render_explorer(metrics: pd.DataFrame, artifacts: dict[str, Any], selected_city: str, weights: dict[str, float], include_estimates: bool) -> None:
    st.markdown("<div class='eyebrow'>Explore · scenario builder</div>", unsafe_allow_html=True)
    city = selected_city if selected_city in metrics["city"].values else metrics.iloc[0]["city"]
    row = metrics[metrics["city"] == city].iloc[0]
    st.title(f"{city}: {row['venue']}")
    st.caption("Observed evidence is separated from modeled scenarios. Store visits describe general mobility demand, not stadium attendance.")

    cols = st.columns(5)
    metric_values = [
        (_safe(row["score"]), "Readiness", row["score_status"]),
        (_safe(row["transit_score"]), "Transit evidence", row["transit_status"]),
        (_safe(row["heat_score"]), "Heat safety", row["heat_status"]),
        (_safe(row["first_last_mile_gap"]), "Gap score", "derived" if row["first_last_mile_gap"] is not None else "unavailable"),
        (_safe(row["nearest_stop_mi"], " mi"), "Nearest stop", row["transit_status"]),
    ]
    for col, (value, label, status) in zip(cols, metric_values):
        with col:
            st.markdown(metric_card(value, label, status), unsafe_allow_html=True)

    col_left, col_right = st.columns([1.1, 1])
    with col_left:
        st.markdown("#### Demand baseline and event range")
        visits = artifacts["visits"]
        series = seasonal_baseline(visits, city)
        if series.empty:
            st.info("Demand artifact unavailable. Run the offline ETL to enable the baseline.")
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=series["date"], y=series["actual"], name="Observed proxy", line=dict(color="#70c8f7", width=1)))
            fig.add_trace(go.Scatter(x=series["date"], y=series["baseline"], name="Seasonal baseline", line=dict(color="#b8a1ff", width=2)))
            scenario = scenario_band(visits, city)
            if not scenario.empty:
                fig.add_trace(go.Scatter(x=scenario["date"], y=scenario["high"], name="Scenario high", line=dict(color="#ffd166", dash="dot")))
                fig.add_trace(go.Scatter(x=scenario["date"], y=scenario["low"], name="Scenario low", fill="tonexty", fillcolor="rgba(255,209,102,.14)", line=dict(color="rgba(0,0,0,0)")))
            st.plotly_chart(_chart_layout(fig, 390), use_container_width=True)
            st.caption("The World Cup range is a scenario band. It is not a calibrated probability interval unless the Methods view reports successful holdout calibration.")
    with col_right:
        st.markdown("#### Evidence ledger")
        evidence = [
            ("Transit", row["transit_status"], "Pinned GTFS venue snapshot"),
            ("Heat", row["heat_status"], "Host-station weather event window"),
            ("UHI", row["uhi_status"], "Venue-buffer urban heat summary"),
            ("Venue support", row["access_status"], "POI density within one mile"),
        ]
        for label, status, source in evidence:
            st.markdown(f"**{label}** · {status_label(str(status))}<br><span class='muted'>{source}</span>", unsafe_allow_html=True)
        st.divider()
        st.markdown("#### Scenario controls")
        shuttle = st.slider("Shuttle buses/hour", 0, 60, 10, 5, key="scenario_shuttle")
        hours = st.slider("Shuttle operating hours", 1.0, 12.0, 6.0, 0.5, key="scenario_hours")
        park = st.slider("Park-and-ride spaces", 0, 20000, 2000, 1000, key="scenario_park")
        bike = st.slider("Bike-share stations", 0, 50, 5, 5, key="scenario_bike")
        pedestrian = st.slider("Pedestrian/cooling upgrade (%)", 0, 100, 20, 10, key="scenario_ped")
        result = intervention_result(row, ScenarioConfig(city=city, shuttle_buses_per_hour=shuttle, shuttle_hours=hours, park_ride_spaces=park, bike_stations=bike, pedestrian_upgrade_pct=pedestrian))
        st.metric("Potential mode shift", f"{result.potential_mode_shift:,}", "scenario proxy")
        st.metric("Emissions avoided", f"{result.emissions_avoided_kg / 1000:,.1f} t", "scenario proxy")
        st.metric("Capital cost", f"${result.capital_cost:,.0f}")
        st.download_button("Download scenario JSON", json.dumps(result.to_dict(), indent=2), file_name=f"{city.lower().replace(' ', '-')}-scenario.json", mime="application/json")

    st.markdown("#### Transit and climate relationship")
    chart_df = metrics[["city", "transit_score", "first_last_mile_gap", "heat_index_c_p90", "score_status"]].copy()
    chart_df = chart_df.dropna(subset=["transit_score", "first_last_mile_gap"])
    if chart_df.empty:
        st.info("No complete transit/gap evidence is available for this comparison.")
    else:
        fig = px.scatter(chart_df, x="transit_score", y="first_last_mile_gap", size="heat_index_c_p90", color="score_status", hover_name="city", labels={"transit_score": "Transit evidence score", "first_last_mile_gap": "First/last-mile gap", "heat_index_c_p90": "P90 heat index (°C)"}, color_discrete_map={"derived": "#70c8f7", "observed": "#63e6a2"})
        st.plotly_chart(_chart_layout(fig, 360), use_container_width=True)


def render_methods(metrics: pd.DataFrame, artifacts: dict[str, Any]) -> None:
    st.markdown("<div class='eyebrow'>Methods · provenance and QA</div>", unsafe_allow_html=True)
    st.title("Methods, data quality, and assumptions")
    manifest = artifacts.get("manifest", {})
    if manifest.get("status") == "unavailable":
        st.error("No offline ETL manifest is available. The dashboard is using compatibility artifacts only; rankings are not fully auditable until the ETL is run.")
    elif artifacts.get("legacy_mode"):
        st.warning("Legacy cache compatibility mode is active. Run the full ETL to produce versioned, complete artifacts.")
    else:
        st.success(f"Artifact manifest generated {manifest.get('generated_at_utc', 'unknown')}.")

    st.markdown("#### Coverage by city")
    coverage = metrics[["city", "score_status", "data_coverage", "transit_status", "heat_status", "uhi_status", "access_status"]].copy()
    coverage["data_coverage"] = (coverage["data_coverage"] * 100).round(0).astype(int).astype(str) + "%"
    st.dataframe(coverage, hide_index=True, use_container_width=True)

    st.markdown("#### Dataset manifest")
    datasets = manifest.get("datasets", [])
    if datasets:
        st.dataframe(pd.DataFrame(datasets), hide_index=True, use_container_width=True)
    else:
        st.info("No dataset manifest entries are available.")

    st.markdown("#### Score definition")
    st.code("MRS = weighted average of Transit, Heat Safety, UHI Safety, and Venue Support; only evidence-eligible components are included.")
    st.markdown("- Observed and derived values may participate in the strict ranking.\n- Estimated values require explicit opt-in.\n- Scenario outputs are not observations.\n- Traffic pressure is not measured roadway congestion.")

    st.markdown("#### Demand validation")
    validation = validation_metrics(artifacts["visits"])
    if validation.empty:
        st.info("Holdout validation is unavailable until the full visit artifact is built.")
    else:
        st.dataframe(validation, hide_index=True, use_container_width=True)
        st.caption("WAPE and MAE are calculated on 2024 holdout dates against a 2022–2023 seasonal baseline.")

    st.markdown("#### Downloads")
    st.download_button("Download city metrics CSV", metrics.to_csv(index=False), file_name="city_metrics.csv", mime="text/csv")
    st.download_button("Download manifest JSON", json.dumps(manifest, indent=2, default=str), file_name="manifest.json", mime="application/json")
