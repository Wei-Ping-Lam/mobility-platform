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
from dashboard.mobility_platform.contracts import ScenarioConfig
from dashboard.mobility_platform.sources import GTFS_SOURCE, RICE_COLLECTION, rice_source
from dashboard.models.demand import scenario_band, seasonal_baseline, validation_metrics
from dashboard.models.economics import economic_impact_range
from dashboard.ui.theme import (
    callout,
    evidence_row,
    metric_card,
    page_header,
    priority_card,
    section_header,
)
from dashboard.viz.style import (
    COLORS,
    READINESS_SCALE,
    SERIES_COLORS,
    STATUS_COLORS,
    discrete_status_scale,
    style_figure,
    style_map,
)


def _safe(value: Any, suffix: str = "") -> str:
    if value is None or (isinstance(value, (float, np.floating)) and not np.isfinite(value)):
        return "Not available"
    if isinstance(value, (float, np.floating)):
        return f"{value:,.1f}{suffix}"
    return f"{value:,}{suffix}" if isinstance(value, (int, np.integer)) else f"{value}{suffix}"


def _metric_grid(items: list[tuple[str, str, str | None, str | None, str]]) -> None:
    columns = st.columns(len(items))
    for column, (value, label, status, note, accent) in zip(columns, items):
        with column:
            st.markdown(
                metric_card(value, label, status, note=note, accent=accent),
                unsafe_allow_html=True,
            )


def _recommendation(row: pd.Series) -> tuple[str, str, str]:
    dimensions = [
        ("Transit", row.get("transit_score"), row.get("transit_status")),
        ("Heat", row.get("heat_score"), row.get("heat_status")),
        ("Urban heat", row.get("uhi_score"), row.get("uhi_status")),
        ("Venue support", row.get("access_score"), row.get("access_status")),
    ]
    missing = [name for name, _, status in dimensions if status == "unavailable"]
    if missing:
        names = ", ".join(missing)
        return (
            "Close the evidence gap",
            f"Complete or refresh {names.lower()} evidence before using this city in the strict ranking.",
            "partial",
        )
    available = [(name, float(value)) for name, value, _ in dimensions if value is not None and pd.notna(value)]
    if not available:
        return "Build the evidence baseline", "No eligible readiness component is available for a defensible priority.", "unavailable"
    weakest = min(available, key=lambda item: item[1])[0]
    actions = {
        "Transit": ("Strengthen event transit", "Test added service frequency, venue shuttles, and timed transfers against event demand."),
        "Heat": ("Protect hot travel windows", "Prioritize shade, water, cooling, and shorter transfer waits during peak arrival periods."),
        "Urban heat": ("Create a cooler venue corridor", "Target shade and surface-cooling investments along the highest-volume walking approaches."),
        "Venue support": ("Repair the first/last mile", "Focus safe walking, accessible crossings, bike parking, and wayfinding near the venue."),
    }
    title, body = actions[weakest]
    return title, body, str(row.get("score_status", "derived"))


def _executive_map(metrics: pd.DataFrame) -> go.Figure:
    scored = metrics[metrics["rankable"].fillna(False)].copy()
    incomplete = metrics[~metrics["rankable"].fillna(False)].copy()
    if scored.empty:
        figure = go.Figure()
    else:
        figure = px.scatter_mapbox(
            scored,
            lat="lat",
            lon="lon",
            size="games",
            size_max=25,
            color="score",
            color_continuous_scale=READINESS_SCALE,
            range_color=[0, 100],
            hover_name="city",
            hover_data={
                "venue": True,
                "score_status": True,
                "score": ":.1f",
                "data_coverage": ":.0%",
                "games": True,
                "lat": False,
                "lon": False,
            },
            zoom=3.0,
            center={"lat": 38.5, "lon": -96},
        )
        figure.update_traces(name="Rankable city", showlegend=True)
    if not incomplete.empty:
        figure.add_trace(
            go.Scattermapbox(
                lat=incomplete["lat"],
                lon=incomplete["lon"],
                mode="markers",
                marker=dict(
                    size=(incomplete["games"].clip(lower=1) * 4).tolist(),
                    color=COLORS["slate"],
                    opacity=.85,
                    symbol="square",
                ),
                text=incomplete["city"],
                customdata=incomplete[["venue", "score_status", "data_coverage"]],
                hovertemplate=(
                    "%{text}<br>%{customdata[0]}<br>Evidence: %{customdata[1]}"
                    "<br>Coverage: %{customdata[2]:.0%}<extra></extra>"
                ),
                name="Incomplete evidence (square)",
                showlegend=True,
            )
        )
    figure.update_layout(
        coloraxis_colorbar=dict(
            title="Readiness",
            thickness=10,
            len=.55,
            y=.72,
            tickfont=dict(color=COLORS["muted"], size=10),
            title_font=dict(color=COLORS["muted"], size=10),
            outlinewidth=0,
        )
    )
    return style_map(figure, 525, zoom=3.0, lat=38.5, lon=-96)


def render_executive(metrics: pd.DataFrame, artifacts: dict[str, Any], *, supplied_data_lens: bool = False) -> None:
    rankable_mask = metrics["rankable"].fillna(False).astype(bool)
    rankable = metrics[rankable_mask].copy()
    incomplete = metrics[~rankable_mask].copy()
    mean_coverage = float(metrics["data_coverage"].mean()) if not metrics.empty else 0.0
    page_header(
        "Executive decision view",
        "Host City Mobility Readiness",
        "Compare venue access, climate exposure, transit evidence, and intervention priorities without hiding incomplete data.",
        (
            f"{len(metrics)} cities in view",
            "Evidence-gated ranking",
            f"{RICE_COLLECTION} source collection",
        ),
    )
    _metric_grid(
        [
            (str(len(metrics)), "Host cities", None, "Current selection", "teal"),
            (str(len(rankable)), "Strictly rankable", "observed" if len(rankable) else "partial", "All core evidence eligible", "blue"),
            (_safe(metrics["games"].sum()), "Scheduled matches", None, "Across cities in view", "violet"),
            (_safe(mean_coverage * 100, "%"), "Mean evidence coverage", "derived", "Weighted required components", "amber"),
        ]
    )
    if supplied_data_lens:
        callout(
            "info",
            "Rice supplied-data lens is active",
            "The ranking uses supplied weather, urban-heat, and venue-support evidence. Transit stays visible but has zero weight; use a transit-weighted profile after pinned GTFS evidence is available for a complete mobility-readiness comparison.",
        )
    if not incomplete.empty:
        callout(
            "warning",
            f"{len(incomplete)} cities remain outside the strict ranking",
            "They stay visible on the map and in the decision table. Open Methods & QA to see the exact missing component for each city.",
        )

    section_header(
        "National readiness picture",
        "Circle markers are rankable; square markers have incomplete core evidence. Marker size reflects scheduled matches.",
        "Compare",
    )
    map_column, table_column = st.columns([1.5, 1], gap="large")
    with map_column:
        st.plotly_chart(_executive_map(metrics), use_container_width=True, config={"displayModeBar": False})
        st.caption("Venue coordinates are stadium-specific. Readiness color is withheld when a city is not rankable.")
    with table_column:
        display = metrics[
            ["city", "score", "rankable", "score_status", "data_coverage", "first_last_mile_gap", "transit_score"]
        ].copy()
        display["Rankability"] = np.where(display["rankable"], "Rankable", "Partial evidence")
        display["Coverage"] = (pd.to_numeric(display["data_coverage"], errors="coerce") * 100).round(0)
        display["MRS"] = pd.to_numeric(display["score"], errors="coerce").round(1)
        display["Gap"] = pd.to_numeric(display["first_last_mile_gap"], errors="coerce").round(1)
        display["Transit"] = pd.to_numeric(display["transit_score"], errors="coerce").round(1)
        display = display.sort_values(["rankable", "score"], ascending=[False, False], na_position="last")
        display = display[["city", "MRS", "Rankability", "Coverage", "Gap", "Transit"]]
        display.columns = ["City", "MRS", "Rankability", "Coverage (%)", "Gap", "Transit"]
        st.dataframe(display, hide_index=True, use_container_width=True, height=415)
        callout(
            "info",
            "How to use the table",
            "MRS is the weighted score over eligible evidence. Partial scores remain visible for auditability, but do not enter the strict ranking.",
        )

    if not rankable.empty:
        section_header(
            "Readiness among evidence-eligible cities",
            "Scores are shown only for cities that pass the strict evidence gate; coverage remains visible in hover details.",
            "Ranking",
        )
        ranking = rankable.sort_values("score", ascending=True)
        figure = go.Figure(
            go.Bar(
                x=ranking["score"],
                y=ranking["city"],
                orientation="h",
                marker=dict(color=COLORS["teal"], line=dict(width=0)),
                text=ranking["score"].map(lambda value: f"{value:.1f}"),
                textposition="outside",
                customdata=ranking[["data_coverage", "venue"]],
                hovertemplate=(
                    "%{y}<br>MRS: %{x:.1f}<br>Coverage: %{customdata[0]:.0%}"
                    "<br>%{customdata[1]}<extra></extra>"
                ),
            )
        )
        figure.update_xaxes(range=[0, 105], title="Mobility Readiness Score (0-100)")
        st.plotly_chart(style_figure(figure, max(300, 52 * len(ranking)), legend=False), use_container_width=True, config={"displayModeBar": False})

    section_header(
        "What to act on next",
        "These are transparent rule-based priorities based on the weakest available component or the first missing evidence dimension; they are not causal impact estimates.",
        "Decision queue",
    )
    queue = metrics.copy()
    queue["_gap"] = pd.to_numeric(queue["first_last_mile_gap"], errors="coerce").fillna(-1)
    queue = queue.sort_values(["rankable", "_gap", "data_coverage"], ascending=[False, False, True]).head(3)
    columns = st.columns(max(1, len(queue)))
    for column, (_, row) in zip(columns, queue.iterrows()):
        title, body, status = _recommendation(row)
        with column:
            st.markdown(priority_card(str(row["city"]), title, body, status), unsafe_allow_html=True)


def _demand_chart(visits: pd.DataFrame, city: str, demand_status: str) -> tuple[go.Figure | None, pd.DataFrame]:
    series = seasonal_baseline(visits, city)
    if series.empty:
        return None, series
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=series["date"],
            y=series["actual"],
            name="Allocated mobility proxy" if demand_status == "partial" else "Rice WC Hack mobility proxy",
            line=dict(color=SERIES_COLORS["observed"], width=1.25),
            opacity=.58,
            hovertemplate="%{x|%b %d, %Y}<br>Observed proxy: %{y:,.0f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scatter(
            x=series["date"],
            y=series["baseline"],
            name="Seasonal baseline",
            line=dict(color=SERIES_COLORS["baseline"], width=2.5),
            hovertemplate="%{x|%b %d, %Y}<br>Baseline: %{y:,.0f}<extra></extra>",
        )
    )
    scenario = scenario_band(visits, city)
    if not scenario.empty and {"date", "low", "high"}.issubset(scenario.columns):
        figure.add_trace(
            go.Scatter(
                x=scenario["date"],
                y=scenario["low"],
                name="Scenario low",
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=scenario["date"],
                y=scenario["high"],
                name="Low-high event scenario",
                fill="tonexty",
                fillcolor=SERIES_COLORS["scenario_fill"],
                line=dict(color=SERIES_COLORS["scenario"], width=1.8, dash="dash"),
                hovertemplate="%{x|%b %d, %Y}<br>Scenario high: %{y:,.0f}<extra></extra>",
            )
        )
    figure.update_xaxes(title=None)
    figure.update_yaxes(title="Daily visits proxy")
    return style_figure(figure, 410), series


def _access_map(row: pd.Series, stop_points: list[dict[str, Any]]) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scattermapbox(
            lat=[point["lat"] for point in stop_points],
            lon=[point["lon"] for point in stop_points],
            mode="markers",
            marker=dict(size=8, color=COLORS["blue"], opacity=.76),
            name="GTFS stops",
            hovertemplate="Transit stop<br>%{lat:.4f}, %{lon:.4f}<extra></extra>",
        )
    )
    figure.add_trace(
        go.Scattermapbox(
            lat=[row["lat"]],
            lon=[row["lon"]],
            mode="markers",
            marker=dict(size=19, color=COLORS["amber"]),
            name="Venue",
            text=[row["venue"]],
            hovertemplate="%{text}<br>%{lat:.4f}, %{lon:.4f}<extra></extra>",
        )
    )
    return style_map(figure, 440, zoom=11, lat=float(row["lat"]), lon=float(row["lon"]))


def _relationship_chart(metrics: pd.DataFrame) -> tuple[go.Figure | None, pd.DataFrame]:
    chart = metrics[["city", "transit_score", "first_last_mile_gap", "heat_index_c_p90", "score_status"]].copy()
    chart = chart.dropna(subset=["transit_score", "first_last_mile_gap"])
    if chart.empty:
        return None, chart
    figure = px.scatter(
        chart,
        x="transit_score",
        y="first_last_mile_gap",
        color="score_status",
        symbol="score_status",
        text="city",
        hover_name="city",
        hover_data={"heat_index_c_p90": ":.1f", "score_status": True},
        labels={
            "transit_score": "Transit evidence score",
            "first_last_mile_gap": "First/last-mile gap",
            "heat_index_c_p90": "P90 heat index (C)",
            "score_status": "Evidence status",
        },
        color_discrete_map=STATUS_COLORS,
    )
    figure.update_traces(textposition="top center", marker=dict(size=11, line=dict(color="#ffffff", width=1.5)))
    return style_figure(figure, 390), chart


def render_explorer(
    metrics: pd.DataFrame,
    artifacts: dict[str, Any],
    selected_city: str,
    weights: dict[str, float],
    include_estimates: bool,
) -> None:
    city = selected_city if selected_city in metrics["city"].values else str(metrics.iloc[0]["city"])
    row = metrics[metrics["city"] == city].iloc[0]
    page_header(
        "City explorer",
        f"{city} / {row['venue']}",
        "Explore mobility demand, access evidence, and intervention tradeoffs. Retail mobility is never presented as stadium attendance.",
        (
            f"{int(row['games'])} scheduled matches",
            f"Venue capacity {int(row['capacity']):,}",
            f"{RICE_COLLECTION} supplied data",
        ),
    )
    if include_estimates:
        callout("warning", "Estimated components are enabled", "Estimated values remain labeled and are included only because the sidebar opt-in is active.")
    if not bool(row["rankable"]):
        callout(
            "warning",
            "Partial score - not rankable",
            "This city's partial MRS is visible for auditability but is excluded from the strict ranking until all weighted core evidence is eligible.",
        )
    if row.get("demand_status") == "partial":
        callout(
            "warning",
            "Demand series uses an explicit equal allocation",
            f"Rice WC Hack / store-visits-rice reports the combined market '{row.get('demand_source_market')}'. The city series is a transparent allocation, not an independently observed city total.",
        )

    _metric_grid(
        [
            (_safe(row["score"]), "Mobility readiness", str(row["score_status"]), "Weighted eligible evidence", "teal"),
            (_safe(row["transit_score"]), "Transit evidence", str(row["transit_status"]), "Pinned venue GTFS", "blue"),
            (_safe(row["heat_score"]), "Heat safety", str(row["heat_status"]), "June-July event window", "amber"),
            (_safe(row["first_last_mile_gap"]), "First/last-mile gap", "derived" if pd.notna(row["first_last_mile_gap"]) else "unavailable", "Higher means more pressure", "coral"),
            (_safe(row["nearest_stop_mi"], " mi"), "Nearest transit stop", str(row["transit_status"]), "Straight-line venue distance", "violet"),
        ]
    )

    demand_tab, scenario_tab, evidence_tab = st.tabs(["Demand & access", "Intervention scenario", "Evidence details"])
    with demand_tab:
        section_header(
            "Demand baseline and event range",
            "Observed store-visit mobility is shown separately from the seasonal baseline and the explicit low-high event scenario.",
            "Movement",
        )
        figure, series = _demand_chart(artifacts["visits"], city, str(row.get("demand_status", "unavailable")))
        if figure is None:
            callout("info", "Demand artifact unavailable", "Run the offline ETL to enable the historical baseline and event scenario.")
        else:
            st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
            st.caption("The event range is a scenario band, not a probability interval. Validation against seasonal-naive holdouts is reported in Methods & QA.")
            with st.expander("Accessible table: demand baseline"):
                st.dataframe(series[["date", "actual", "baseline"]], hide_index=True, use_container_width=True)

        section_header(
            "Commercial activity mix and customer origins",
            "These Rice measures provide movement context; neither category visits nor customer-home counts represent ticketed spectators.",
            "Context",
        )
        activity_column, origin_column = st.columns(2, gap="large")
        category_frame = artifacts.get("visits_category", pd.DataFrame())
        category_frame = category_frame[category_frame.get("city", pd.Series(dtype=str)) == city].copy()
        if not category_frame.empty:
            category_frame["date"] = pd.to_datetime(category_frame["date"], errors="coerce")
            category_frame = category_frame[category_frame["date"].dt.year.between(2022, 2024)]
            category_table = (
                category_frame.groupby("category", as_index=False)["daily_visits"].sum()
                .nlargest(8, "daily_visits")
                .sort_values("daily_visits")
            )
        else:
            category_table = pd.DataFrame(columns=["category", "daily_visits"])
        with activity_column:
            st.markdown("##### Leading activity categories")
            if category_table.empty:
                callout("info", "Category context unavailable", "Run the full Rice ETL to build category-level mobility summaries.")
            else:
                category_figure = px.bar(
                    category_table,
                    x="daily_visits",
                    y="category",
                    orientation="h",
                    color_discrete_sequence=[COLORS["teal"]],
                    labels={"daily_visits": "Store-visit proxy (2022-2024)", "category": ""},
                )
                category_figure.update_layout(margin=dict(l=10, r=18, t=10, b=25))
                st.plotly_chart(style_figure(category_figure, 360, legend=False), use_container_width=True, config={"displayModeBar": False})
                with st.expander("Accessible table: activity categories"):
                    st.dataframe(
                        category_table.rename(columns={"category": "Category", "daily_visits": "Store-visit proxy"}),
                        hide_index=True,
                        use_container_width=True,
                    )

        origins = artifacts.get("origins", pd.DataFrame())
        origins = origins[origins.get("city", pd.Series(dtype=str)) == city].copy()
        if not origins.empty:
            origins["count"] = pd.to_numeric(origins["count"], errors="coerce")
            origin_table = origins[origins["home_state"] != "Unknown"].nlargest(8, "count").sort_values("count")
        else:
            origin_table = pd.DataFrame(columns=["home_state", "count"])
        with origin_column:
            st.markdown("##### Leading customer-home states")
            if origin_table.empty:
                callout("info", "Origin context unavailable", "Run the full Rice ETL to build customer-origin summaries.")
            else:
                origin_figure = px.bar(
                    origin_table,
                    x="count",
                    y="home_state",
                    orientation="h",
                    color_discrete_sequence=[COLORS["blue"]],
                    labels={"count": "Customer-origin count", "home_state": "State"},
                )
                origin_figure.update_layout(margin=dict(l=10, r=18, t=10, b=25))
                st.plotly_chart(style_figure(origin_figure, 360, legend=False), use_container_width=True, config={"displayModeBar": False})
                with st.expander("Accessible table: customer origins"):
                    st.dataframe(
                        origin_table[["home_state", "count"]].rename(columns={"home_state": "State", "count": "Customer-origin count"}),
                        hide_index=True,
                        use_container_width=True,
                    )
        st.caption(f"Sources: {rice_source('store-visits-rice', 'category activity')} and {rice_source('spend-patterns-rice', 'customer-home summaries')}.")

        section_header(
            "Venue access layer",
            "The venue and stops within two miles come from the pinned GTFS snapshot. Aggregate heat and POI evidence remains in the Evidence details tab.",
            "Map",
        )
        gtfs_row = artifacts.get("gtfs", {}).get(city, {})
        stop_points = gtfs_row.get("stop_points_2mi", [])
        if stop_points:
            st.plotly_chart(_access_map(row, stop_points), use_container_width=True, config={"displayModeBar": False})
            st.caption("Blue markers are scheduled transit stops; the amber marker is the venue. Distances are spatial proxies, not audited walking routes.")
        else:
            callout(
                "info",
                "Stop coordinates are not available",
                "The pinned snapshot does not contain a displayable two-mile stop layer for this city. Feed status and aggregate counts remain auditable in Methods & QA.",
            )

        section_header(
            "Cross-city transit and climate context",
            "Marker color and shape both encode evidence status. City labels provide a non-color identification channel.",
            "Context",
        )
        relationship, chart_table = _relationship_chart(metrics)
        if relationship is None:
            callout("info", "Comparison unavailable", "No cities currently have both transit and first/last-mile gap evidence.")
        else:
            st.plotly_chart(relationship, use_container_width=True, config={"displayModeBar": False})
            with st.expander("Accessible table: transit and climate"):
                st.dataframe(
                    chart_table.rename(
                        columns={
                            "city": "City",
                            "transit_score": "Transit evidence",
                            "first_last_mile_gap": "First/last-mile gap",
                            "heat_index_c_p90": "P90 heat index (C)",
                            "score_status": "Evidence status",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                )

    with scenario_tab:
        section_header(
            "Build an intervention package",
            "Adjust service and access assumptions, then compare modeled traffic-pressure and emissions proxies with a zero-intervention baseline.",
            "Scenario",
        )
        controls, outputs = st.columns([.82, 1.18], gap="large")
        with controls:
            st.markdown("##### Package assumptions")
            shuttle = st.slider("Shuttle buses per hour", 0, 60, 10, 5, key="scenario_shuttle")
            hours = st.slider("Shuttle operating hours", 1.0, 12.0, 6.0, 0.5, key="scenario_hours")
            park = st.slider("Park-and-ride spaces", 0, 20000, 2000, 1000, key="scenario_park")
            bike = st.slider("Bike-share stations", 0, 50, 5, 5, key="scenario_bike")
            pedestrian = st.slider("Pedestrian and cooling upgrade (%)", 0, 100, 20, 10, key="scenario_ped")
            st.caption("Uptake, occupancy, bus capacity, trip distance, emissions, and unit costs use the transparent defaults in the scenario contract.")

        scenario_config = ScenarioConfig(
            city=city,
            shuttle_buses_per_hour=shuttle,
            shuttle_hours=hours,
            park_ride_spaces=park,
            bike_stations=bike,
            pedestrian_upgrade_pct=pedestrian,
        )
        baseline_config = ScenarioConfig(
            city=city,
            shuttle_buses_per_hour=0,
            shuttle_hours=hours,
            park_ride_spaces=0,
            bike_stations=0,
            pedestrian_upgrade_pct=0,
        )
        result = intervention_result(row, scenario_config)
        baseline_result = intervention_result(row, baseline_config)
        with outputs:
            _metric_grid(
                [
                    (_safe(result.potential_mode_shift), "Potential mode shift", "scenario", "Passenger capacity proxy", "teal"),
                    (_safe(result.residual_vehicle_trips), "Residual vehicle pressure", "scenario", "Not measured congestion", "coral"),
                ]
            )
            _metric_grid(
                [
                    (_safe(result.emissions_avoided_kg / 1000, " t"), "Potential emissions avoided", "scenario", "Range proxy", "blue"),
                    (f"${result.capital_cost + result.operating_cost_per_match:,.0f}", "Modeled package cost", "scenario", "Capital plus one match operation", "violet"),
                ]
            )

        comparison = pd.DataFrame(
            {
                "Measure": ["Potential mode shift", "Residual vehicle pressure"],
                "Zero intervention": [baseline_result.potential_mode_shift, baseline_result.residual_vehicle_trips],
                "Selected package": [result.potential_mode_shift, result.residual_vehicle_trips],
            }
        )
        long_comparison = comparison.melt(id_vars="Measure", var_name="Scenario", value_name="People / trips proxy")
        comparison_figure = px.bar(
            long_comparison,
            x="Measure",
            y="People / trips proxy",
            color="Scenario",
            barmode="group",
            text_auto=",.0f",
            color_discrete_map={"Zero intervention": COLORS["slate"], "Selected package": COLORS["teal"]},
        )
        comparison_figure.update_traces(textposition="outside", cliponaxis=False)
        st.plotly_chart(style_figure(comparison_figure, 355), use_container_width=True, config={"displayModeBar": False})
        callout(
            "info",
            "Interpret as capacity and pressure proxies",
            "These outputs do not claim measured roadway congestion, observed mode shift, or a calibrated emissions forecast.",
        )
        full_comparison = pd.DataFrame(
            {
                "Measure": ["Potential mode shift", "Residual vehicle trips", "Vehicle-km avoided", "Emissions avoided (kg)"],
                "Zero intervention": [
                    baseline_result.potential_mode_shift,
                    baseline_result.residual_vehicle_trips,
                    baseline_result.vehicle_km_avoided,
                    baseline_result.emissions_avoided_kg,
                ],
                "Selected package": [
                    result.potential_mode_shift,
                    result.residual_vehicle_trips,
                    result.vehicle_km_avoided,
                    result.emissions_avoided_kg,
                ],
            }
        )
        with st.expander("Accessible table: zero intervention vs selected package"):
            st.dataframe(full_comparison, hide_index=True, use_container_width=True)

        economic = economic_impact_range(artifacts.get("brand_spend", pd.DataFrame()), city)
        section_header(
            "Economic activity context",
            "Commercial activity remains a low-high scenario and is not presented as causal impact or venue attendance.",
            "Co-benefit",
        )
        if economic.get("status") == "scenario":
            _metric_grid(
                [
                    (
                        f"${economic['low']:,.0f} to ${economic['high']:,.0f}",
                        "Incremental spend range",
                        "scenario",
                        "Commercial activity sensitivity",
                        "amber",
                    )
                ]
            )
        else:
            callout("info", "Economic artifact unavailable", "No city-level commercial activity scenario can be shown for this city.")
        st.download_button(
            "Download this scenario (JSON)",
            json.dumps(result.to_dict(), indent=2),
            file_name=f"{city.lower().replace(' ', '-')}-scenario.json",
            mime="application/json",
            key="scenario_download",
        )

    with evidence_tab:
        section_header(
            "Evidence ledger",
            "Every readiness component retains a status and source. Color is always paired with a written evidence label.",
            "Audit",
        )
        evidence = [
            ("Demand context", str(row.get("demand_status", "unavailable")), rice_source("store-visits-rice", "daily market mobility")),
            ("Transit", str(row["transit_status"]), GTFS_SOURCE),
            (
                "Heat safety",
                str(row["heat_status"]),
                rice_source(
                    "daily-weather-rice",
                    f"station {row.get('weather_station')} ({float(row.get('weather_station_distance_mi')):.1f} mi from venue)"
                    if row.get("weather_station_distance_mi") is not None and pd.notna(row.get("weather_station_distance_mi"))
                    else "host-area station unavailable",
                ),
            ),
            ("Urban heat", str(row["uhi_status"]), rice_source("urban-heat-index-rice", "venue buffer")),
            ("Venue support", str(row["access_status"]), rice_source("core-poi-geometry-rice", "one-mile venue buffer")),
        ]
        ledger_html = "".join(evidence_row(name, status, source) for name, status, source in evidence)
        st.markdown(f"<div class='evidence-list'>{ledger_html}</div>", unsafe_allow_html=True)
        evidence_table = pd.DataFrame(
            {
                "Component": ["Transit", "Heat safety", "Urban heat", "Venue support"],
                "Score": [row["transit_score"], row["heat_score"], row["uhi_score"], row["access_score"]],
                "Status": [row["transit_status"], row["heat_status"], row["uhi_status"], row["access_status"]],
                "Weight": [weights["transit"], weights["heat"], weights["uhi"], weights["access"]],
            }
        )
        evidence_table["Score"] = pd.to_numeric(evidence_table["Score"], errors="coerce").round(1)
        evidence_table["Weight"] = (evidence_table["Weight"] * 100).round(0).astype(int).astype(str) + "%"
        st.dataframe(evidence_table, hide_index=True, use_container_width=True)

        weight_chart = pd.DataFrame(
            {"Component": ["Transit", "Heat safety", "Urban heat", "Venue support"], "Weight": [weights["transit"], weights["heat"], weights["uhi"], weights["access"]]}
        )
        weight_chart["Weight (%)"] = weight_chart["Weight"] * 100
        weight_figure = px.bar(
            weight_chart.sort_values("Weight (%)"),
            x="Weight (%)",
            y="Component",
            orientation="h",
            color_discrete_sequence=[COLORS["blue"]],
            text="Weight (%)",
        )
        weight_figure.update_traces(texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
        weight_figure.update_xaxes(range=[0, max(45, float(weight_chart["Weight (%)"].max()) + 8)])
        st.plotly_chart(style_figure(weight_figure, 300, legend=False), use_container_width=True, config={"displayModeBar": False})
        st.caption("The chart reflects the normalized profile currently selected in the sidebar.")


def _coverage_heatmap(metrics: pd.DataFrame) -> go.Figure:
    dimensions = {
        "Transit": "transit_status",
        "Heat": "heat_status",
        "Urban heat": "uhi_status",
        "Venue support": "access_status",
    }
    status_order = ["unavailable", "partial", "estimated", "derived", "observed"]
    colorscale, mapping = discrete_status_scale(status_order)
    status_matrix = metrics[list(dimensions.values())].applymap(lambda value: value if value in mapping else "unavailable")
    z = status_matrix.applymap(mapping.get).to_numpy()
    text = status_matrix.applymap(lambda value: str(value).upper()).to_numpy()
    figure = go.Figure(
        go.Heatmap(
            z=z,
            x=list(dimensions),
            y=metrics["city"],
            text=text,
            customdata=status_matrix.to_numpy(),
            texttemplate="%{text}",
            textfont=dict(color="#ffffff", size=10),
            colorscale=colorscale,
            zmin=0,
            zmax=len(status_order) - 1,
            showscale=False,
            xgap=4,
            ygap=4,
            hovertemplate="%{y}<br>%{x}: %{customdata}<extra></extra>",
        )
    )
    figure.update_xaxes(side="top", title=None)
    figure.update_yaxes(title=None, autorange="reversed")
    return style_figure(figure, max(390, 35 * len(metrics)), legend=False, margin=dict(l=105, r=20, t=55, b=20))


def render_methods(metrics: pd.DataFrame, artifacts: dict[str, Any]) -> None:
    manifest = artifacts.get("manifest", {})
    page_header(
        "Methods and quality assurance",
        "Audit every headline number",
        "Inspect coverage, provenance, transformations, scoring rules, assumptions, and validation before using the platform for a decision.",
        (
            f"{RICE_COLLECTION} canonical source",
            "Explicit missingness",
            "Downloadable evidence",
        ),
    )
    if manifest.get("status") == "unavailable":
        callout(
            "error",
            "Offline ETL manifest unavailable",
            "The dashboard is using compatibility artifacts. Rankings are not fully auditable until the versioned ETL is run.",
        )
    elif artifacts.get("legacy_mode"):
        callout("warning", "Legacy compatibility mode", "Run the full ETL to produce versioned artifacts, hashes, and complete quality reports.")
    else:
        callout("success", "Versioned artifacts loaded", f"Manifest generated {manifest.get('generated_at_utc', 'at an unknown time')}.")

    coverage_tab, provenance_tab, model_tab, download_tab = st.tabs(
        ["Coverage", "Provenance & transit", "Model & assumptions", "Downloads"]
    )
    with coverage_tab:
        section_header(
            "Evidence eligibility by city",
            "Each cell contains a written status in addition to its color. The table below is the accessible equivalent.",
            "Coverage",
        )
        st.plotly_chart(_coverage_heatmap(metrics), use_container_width=True, config={"displayModeBar": False})
        coverage = metrics[
            ["city", "rankable", "score_status", "data_coverage", "transit_status", "heat_status", "uhi_status", "access_status"]
        ].copy()
        coverage["data_coverage"] = (coverage["data_coverage"] * 100).round(0).astype(int).astype(str) + "%"
        coverage.columns = ["City", "Rankable", "Score status", "Coverage", "Transit", "Heat", "Urban heat", "Venue support"]
        st.dataframe(coverage, hide_index=True, use_container_width=True)

    with provenance_tab:
        section_header(
            "Dataset manifest",
            f"Every supplied-data artifact resolves to its exact dataset under {RICE_COLLECTION}. Version, coverage, hashes, row counts, and quality outcomes are pipeline-generated.",
            "Sources",
        )
        datasets = manifest.get("datasets", [])
        if datasets:
            st.dataframe(pd.DataFrame(datasets), hide_index=True, use_container_width=True)
        else:
            callout("info", "No manifest entries", "Build the full derived artifact set to populate source-level provenance.")

        section_header(
            "Pinned GTFS snapshot",
            "A floor score remains an observed floor score. Missing or failed feeds remain unavailable and never silently fall back to expert judgment.",
            "Transit",
        )
        gtfs_rows = []
        for city, value in sorted(artifacts.get("gtfs", {}).items()):
            gtfs_rows.append(
                {
                    "City": city,
                    "Feed status": value.get("feed_status", "unavailable"),
                    "Score status": value.get("score_status", "unavailable"),
                    "Stops": value.get("total_agency_stops"),
                    "Routes": value.get("route_count"),
                    "Event departures": value.get("event_window_departures"),
                    "Calendar": value.get("calendar_validity"),
                    "Nearest stop (mi)": value.get("nearest_stop_mi"),
                }
            )
        if gtfs_rows:
            st.dataframe(pd.DataFrame(gtfs_rows), hide_index=True, use_container_width=True)
        else:
            callout("info", "No pinned GTFS snapshot", "Run the explicit refresh command to create a versioned snapshot.")

    with model_tab:
        section_header(
            "Mobility Readiness Score",
            "The score is a weighted average over available evidence-eligible components. Rankability is a separate, stricter gate.",
            "Definition",
        )
        st.code("MRS = weighted average of Transit + Heat Safety + UHI Safety + Venue Support")
        callout(
            "info",
            "Score is not the same as rankability",
            "A partial MRS stays visible, but rankable remains false until every non-zero-weight core dimension is eligible. Estimates require explicit opt-in.",
        )
        profile_table = pd.DataFrame(DEFAULT_WEIGHTS).T.reset_index(names="Profile")
        profile_table.columns = ["Profile", "Transit", "Heat", "Urban heat", "Venue support"]
        st.dataframe(profile_table, hide_index=True, use_container_width=True)

        with st.expander("Assumption register", expanded=True):
            st.markdown(
                "- Peak visitors are modeled as 95% of venue capacity.\n"
                "- Demand uplift is a 1.5x / 3.0x / 4.5x low, base, and high scenario.\n"
                "- Combined source markets use equal allocation and remain partial.\n"
                "- Shuttle capacity, uptake, occupancy, trip distance, and emissions factors are editable scenario assumptions.\n"
                "- Commercial uplift is a 2% / 5% / 10% scenario, not causal attribution.\n"
                "- Traffic results are pressure proxies, not measured congestion."
            )

        section_header(
            "Demand validation",
            "MAE and WAPE use rolling 2023 and 2024 holdouts and are compared with a seasonal-naive baseline.",
            "Backtest",
        )
        validation = validation_metrics(artifacts["visits"])
        if validation.empty:
            callout("info", "Validation unavailable", "Build the full visit artifact before interpreting the event demand model as anything beyond a scenario.")
        else:
            st.dataframe(validation, hide_index=True, use_container_width=True)
            if "outperforms_seasonal_naive" in validation and bool(validation["outperforms_seasonal_naive"].all()):
                callout("success", "Baseline clears the comparator", "It outperforms the seasonal-naive baseline on every reported holdout.")
            else:
                callout("warning", "Treat demand as a scenario model", "The baseline does not consistently beat the seasonal-naive comparator.")

    with download_tab:
        section_header(
            "Reproduce the displayed values",
            "Downloads expose the current weighted city metrics and the source manifest used by this session.",
            "Export",
        )
        city_download, manifest_download = st.columns(2)
        with city_download:
            st.download_button(
                "Download city metrics (CSV)",
                metrics.to_csv(index=False),
                file_name="city_metrics.csv",
                mime="text/csv",
                key="metrics_download",
                use_container_width=True,
            )
        with manifest_download:
            st.download_button(
                "Download manifest (JSON)",
                json.dumps(manifest, indent=2, default=str),
                file_name="manifest.json",
                mime="application/json",
                key="manifest_download",
                use_container_width=True,
            )
        callout(
            "info",
            "Not measured",
            "The platform does not measure stadium attendance, roadway congestion, observed mode shift, causal economic impact, or audited pedestrian accessibility.",
        )
