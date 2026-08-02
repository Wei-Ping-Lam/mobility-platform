"""Accessible portfolio visualizations for the all-city landing page."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.viz.style import COLORS, READINESS_SCALE, style_figure, style_map

LENS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "Mobility readiness": {
        "column": "strict_score",
        "label": "Evidence-qualified Mobility Readiness Score (0-100)",
        "short_label": "Readiness score",
        "format": ".1f",
        "higher_is_better": True,
        "context": "Higher indicates stronger relative readiness under the selected evidence weights.",
    },
    "Peak access gap": {
        "column": "capacity_qualified_gap_pph",
        "label": "Peak access gap (passengers/hour)",
        "short_label": "Peak access gap",
        "format": ",.0f",
        "higher_is_better": False,
        "context": "Lower is better; this is a scheduled-capacity gap, not measured roadway congestion.",
    },
    "Traffic pressure": {
        "column": "package_vehicle_trips_base",
        "label": "Venue-area vehicle-trip pressure after package",
        "short_label": "Vehicle-trip pressure",
        "format": ",.0f",
        "higher_is_better": False,
        "context": "Lower is better; this is a planning proxy, not observed traffic or congestion.",
    },
    "Net CO2e avoided": {
        "column": "package_net_co2e_base",
        "label": "Package net CO2e avoided (kg)",
        "short_label": "Net CO2e avoided",
        "format": ",.0f",
        "higher_is_better": True,
        "context": "Higher modeled avoidance is better; results are planning ranges, not measured emissions.",
    },
    "Investment efficiency": {
        "column": "package_cost_per_passenger",
        "label": "Package cost per peak passenger addressed ($)",
        "short_label": "Cost per passenger addressed",
        "format": ",.0f",
        "higher_is_better": False,
        "context": "Lower is more cost-efficient, but cost alone does not determine the preferred investment.",
    },
}


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column), errors="coerce")


def portfolio_map(frame: pd.DataFrame, lens: str, selected_cities: list[str]) -> go.Figure:
    """Map every city with one explicit, switchable outcome lens."""

    definition = LENS_DEFINITIONS[lens]
    chart = frame.dropna(subset=["lat", "lon"]).copy()
    values = _numeric(chart, definition["column"])
    magnitude = values.abs().fillna(0)
    maximum = max(float(magnitude.max()), 1.0)
    sizes = 13 + 17 * np.sqrt(magnitude / maximum)
    selected = chart["city"].isin(selected_cities)
    sizes = sizes + selected.astype(int) * 7
    colorscales: dict[str, list[list[Any]] | str] = {
        "Mobility readiness": READINESS_SCALE,
        "Peak access gap": [[0.0, "#f7e5df"], [1.0, COLORS["coral"]]],
        "Traffic pressure": [[0.0, "#e4edf5"], [1.0, COLORS["blue"]]],
        "Net CO2e avoided": "RdBu",
        "Investment efficiency": [[0.0, "#f8ead5"], [1.0, COLORS["amber"]]],
    }
    figure = go.Figure(
        go.Scattermap(
            lat=chart["lat"],
            lon=chart["lon"],
            mode="markers",
            marker=dict(
                size=sizes,
                color=values,
                colorscale=colorscales[lens],
                showscale=True,
                colorbar=dict(
                    title=dict(text=definition["short_label"], side="top"),
                    orientation="h",
                    x=.5,
                    xanchor="center",
                    y=.02,
                    yanchor="bottom",
                    thickness=10,
                    len=.58,
                    bgcolor="rgba(255,255,255,.9)",
                    outlinewidth=0,
                ),
                opacity=.9,
            ),
            customdata=np.column_stack(
                [
                    chart["city"],
                    chart["representative_match_id"].fillna("Not available"),
                    values,
                    chart["qualified_interventions"].fillna("No qualified option"),
                    chart["screening_confidence"].fillna("unavailable"),
                    selected.map({True: "Selected for comparison", False: "Available to compare"}),
                ]
            ),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Representative match: %{customdata[1]}"
                f"<br>{definition['label']}: %{{customdata[2]:{definition['format']}}}"
                "<br>Qualified option set: %{customdata[3]}<br>Evidence: %{customdata[4]}"
                "<br>%{customdata[5]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    return style_map(figure, 510, zoom=3.0, lat=38.5, lon=-96)


def outcome_ranking_chart(frame: pd.DataFrame, lens: str) -> go.Figure:
    """Rank every visible city for one plainly defined outcome."""

    definition = LENS_DEFINITIONS[lens]
    chart = frame.copy()
    chart["_value"] = _numeric(chart, definition["column"])
    chart = chart.dropna(subset=["_value"])
    ascending = bool(definition["higher_is_better"])
    chart = chart.sort_values(["_value", "city"], ascending=[ascending, True])
    favorable = COLORS["teal"] if definition["higher_is_better"] else COLORS["blue"]
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_value"],
            orientation="h",
            marker_color=favorable,
            text=chart["_value"],
            texttemplate=f"%{{text:{definition['format']}}}",
            textposition="outside",
            customdata=np.column_stack(
                [
                    chart["strict_rank"].fillna("Not ranked"),
                    chart["screening_confidence"].fillna("unavailable"),
                    chart["qualified_interventions"].fillna("No qualified option"),
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b>"
                f"<br>{definition['label']}: %{{x:{definition['format']}}}"
                "<br>Strict readiness rank: %{customdata[0]}"
                "<br>Evidence confidence: %{customdata[1]}"
                "<br>Qualified options: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_xaxes(title=definition["label"], rangemode="tozero")
    return style_figure(figure, max(430, 46 * len(chart)), legend=False)


def demand_gap_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare peak demand and scheduled-capacity gap for selected cities."""

    chart = frame.sort_values("capacity_qualified_gap_pph", ascending=True)
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["peak_demand_pph"],
            orientation="h",
            name="Peak movement demand",
            marker_color=COLORS["blue"],
        )
    )
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["capacity_qualified_gap_pph"],
            orientation="h",
            name="Scheduled-capacity gap",
            marker_color=COLORS["coral"],
        )
    )
    figure.update_layout(barmode="group")
    figure.update_xaxes(title="Passengers per hour")
    return style_figure(figure, max(300, 76 * len(chart)))


def package_tradeoff_chart(frame: pd.DataFrame) -> go.Figure:
    """Keep cost, passenger benefit, and climate outcome visually separate."""

    chart = frame.dropna(subset=["package_cost_per_passenger", "package_gap_resolved"]).copy()
    climate = _numeric(chart, "package_net_co2e_base").fillna(0)
    figure = go.Figure()
    if chart.empty:
        figure.add_annotation(
            text="Baseline has no intervention cost or peak-gap benefit to compare.",
            x=.5,
            y=.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            font=dict(color=COLORS["muted"], size=13),
        )
    for index, row in chart.reset_index(drop=True).iterrows():
        figure.add_trace(
            go.Scatter(
                x=[row["package_cost_per_passenger"]],
                y=[row["package_gap_resolved"]],
                mode="markers+text",
                text=[row["city"]],
                textposition="top center",
                marker=dict(
                    size=16 + 18 * abs(float(climate.iloc[index])) / max(float(climate.abs().max()), 1),
                    color=COLORS["teal"] if float(climate.iloc[index]) >= 0 else COLORS["coral"],
                    opacity=.82,
                ),
                name=str(row["city"]),
                customdata=[[row["package_name"], climate.iloc[index], row["package_status"]]],
                hovertemplate=(
                    "<b>%{text}</b><br>Package: %{customdata[0]}<br>Cost per peak passenger addressed: $%{x:,.0f}"
                    "<br>Peak gap addressed: %{y:,.0f}<br>Net CO2e avoided: %{customdata[1]:,.0f} kg"
                    "<br>Evidence: %{customdata[2]}<extra></extra>"
                ),
            )
        )
    figure.update_xaxes(title="Planning cost per peak passenger addressed", tickprefix="$")
    figure.update_yaxes(title="Peak passenger gap addressed")
    return style_figure(figure, 350, legend=False)
