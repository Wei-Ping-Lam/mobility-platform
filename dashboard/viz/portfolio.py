"""Decision-focused portfolio visualizations for the all-city landing page."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.viz.style import COLORS, READINESS_SCALE, style_figure

READINESS_COMPONENTS = {
    "Transit proximity": "transit_score",
    "Heat safety": "heat_score",
    "Urban heat safety": "uhi_score",
    "Venue support": "access_score",
}


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column), errors="coerce")


def portfolio_access_chart(frame: pd.DataFrame) -> go.Figure:
    """Show scheduled passenger capacity and the remaining peak access gap together."""

    chart = frame.copy()
    chart["_demand"] = _numeric(chart, "peak_demand_pph")
    chart["_gap"] = _numeric(chart, "capacity_qualified_gap_pph").clip(lower=0)
    chart["_scheduled"] = (chart["_demand"] - chart["_gap"]).clip(lower=0)
    chart["_coverage"] = np.where(
        chart["_demand"] > 0,
        chart["_scheduled"] / chart["_demand"] * 100,
        np.nan,
    )
    chart = chart.dropna(subset=["_demand", "_gap"]).sort_values(["_gap", "city"])
    coverage_labels = chart["_coverage"].map(lambda value: f"{value:.0f}% covered" if pd.notna(value) else "Not available")
    customdata = np.column_stack(
        [
            chart["representative_match_id"].fillna("Not available"),
            chart["_demand"],
            chart["_scheduled"],
            chart["_gap"],
            chart["_coverage"],
        ]
    )

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["_scheduled"],
            orientation="h",
            name="Scheduled transit capacity",
            marker_color=COLORS["teal"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Representative match: %{customdata[0]}"
                "<br>Modeled peak movement: %{customdata[1]:,.0f}/hour"
                "<br>Scheduled transit capacity: %{customdata[2]:,.0f}/hour"
                "<br>Scheduled coverage: %{customdata[4]:.1f}%<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["_gap"],
            orientation="h",
            name="Remaining peak gap",
            marker_color=COLORS["coral"],
            text=coverage_labels,
            textposition="inside",
            insidetextanchor="middle",
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Representative match: %{customdata[0]}"
                "<br>Modeled peak movement: %{customdata[1]:,.0f}/hour"
                "<br>Remaining peak gap: %{customdata[3]:,.0f}/hour"
                "<br>Scheduled coverage: %{customdata[4]:.1f}%<extra></extra>"
            ),
        )
    )
    figure.update_layout(barmode="stack", uniformtext_minsize=9, uniformtext_mode="hide")
    figure.update_xaxes(title="Passengers per representative peak hour", rangemode="tozero")
    return style_figure(figure, 510, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_resilience_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare scheduled coverage before and after a common access stress."""

    chart = frame.copy()
    chart["_baseline"] = _numeric(chart, "scheduled_coverage_pct")
    chart["_stress"] = _numeric(chart, "stress_coverage_pct")
    chart = chart.dropna(subset=["_baseline", "_stress"]).sort_values(
        ["_stress", "city"]
    )
    customdata = np.column_stack(
        [
            chart["representative_match_id"].fillna("Not available"),
            _numeric(chart, "stress_gap_pph"),
        ]
    )
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["_baseline"],
            orientation="h",
            name="Baseline scheduled coverage",
            marker_color=COLORS["teal_light"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Representative match: %{customdata[0]}"
                "<br>Baseline scheduled coverage: %{x:.1f}%<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["_stress"],
            orientation="h",
            name="Coverage after common stress",
            marker_color=COLORS["coral"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Coverage after stress: %{x:.1f}%"
                "<br>Remaining stressed gap: %{customdata[1]:,.0f}/hour<extra></extra>"
            ),
        )
    )
    figure.update_layout(barmode="group")
    figure.update_xaxes(title="Scheduled coverage of modeled peak movement", range=[0, 105])
    return style_figure(figure, 520, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_movement_chart(frame: pd.DataFrame) -> go.Figure:
    """Separate modeled arrival and departure peaks for every host."""

    chart = frame.copy()
    forecast_fields = "forecast_arrival_peak_base" in chart.columns
    prefix = "forecast_" if forecast_fields else ""
    match_column = (
        "forecast_anchor_match_id"
        if "forecast_anchor_match_id" in chart.columns
        else "representative_match_id"
    )
    chart["_arrival"] = _numeric(chart, f"{prefix}arrival_peak_base")
    chart["_departure"] = _numeric(chart, f"{prefix}departure_peak_base")
    chart = chart.dropna(subset=["_arrival", "_departure"]).sort_values(
        ["_departure", "city"]
    )
    customdata = np.column_stack(
        [
            chart[match_column].fillna("Not available"),
            _numeric(chart, f"{prefix}arrival_peak_low"),
            _numeric(chart, f"{prefix}arrival_peak_high"),
            _numeric(chart, f"{prefix}arrival_peak_offset_hours"),
            _numeric(chart, f"{prefix}departure_peak_low"),
            _numeric(chart, f"{prefix}departure_peak_high"),
            _numeric(chart, f"{prefix}departure_peak_offset_hours"),
        ]
    )
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["_arrival"],
            orientation="h",
            name="Arrival peak",
            marker_color=COLORS["blue"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Peak forecast match: %{customdata[0]}"
                "<br>Arrival peak: %{x:,.0f}/hour"
                "<br>Planning range: %{customdata[1]:,.0f}–%{customdata[2]:,.0f}/hour"
                "<br>Peak time: %{customdata[3]:+.0f} h from kickoff<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Bar(
            y=chart["city"],
            x=chart["_departure"],
            orientation="h",
            name="Departure peak",
            marker_color=COLORS["violet"],
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Departure peak: %{x:,.0f}/hour"
                "<br>Planning range: %{customdata[4]:,.0f}–%{customdata[5]:,.0f}/hour"
                "<br>Peak time: %{customdata[6]:+.0f} h from kickoff<extra></extra>"
            ),
        )
    )
    figure.update_layout(barmode="group")
    figure.update_xaxes(title="Modeled passengers per peak hour", rangemode="tozero")
    return style_figure(figure, 530, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_visitor_forecast_chart(
    frame: pd.DataFrame, view: str
) -> go.Figure:
    """Compare one auditable visitor-flow forecast dimension across all hosts."""

    if view == "Peak timing":
        return portfolio_movement_chart(frame)
    settings = {
        "Origin mix": (
            [
                ("Host market", "origin_host_market_share_pct", "origin_host_market_attendees_base", "teal"),
                ("Nearby U.S.", "origin_nearby_us_share_pct", "origin_nearby_us_attendees_base", "blue"),
                ("Long-distance U.S.", "origin_long_distance_us_share_pct", "origin_long_distance_us_attendees_base", "violet"),
                ("International / unobserved", "origin_international_share_pct", "origin_international_attendees_base", "amber"),
            ],
            "forecast_non_host_share_pct",
        ),
        "Mode mix": (
            [
                ("Scheduled transit demand", "mode_scheduled_transit_share_pct", "mode_scheduled_transit_attendees_base", "teal"),
                ("Shuttle / coach demand", "mode_shuttle_coach_share_pct", "mode_shuttle_coach_attendees_base", "blue"),
                ("Private vehicle / taxi demand", "mode_private_taxi_share_pct", "mode_private_taxi_attendees_base", "coral"),
                ("Walk / bike demand", "mode_walk_bike_share_pct", "mode_walk_bike_attendees_base", "amber"),
            ],
            "mode_scheduled_transit_share_pct",
        ),
    }
    series, sort_column = settings.get(view, settings["Origin mix"])
    chart = frame.copy()
    chart["_sort"] = _numeric(chart, sort_column)
    chart = chart.dropna(subset=["_sort"]).sort_values(["_sort", "city"])
    figure = go.Figure()
    for name, share_column, count_column, color in series:
        share = _numeric(chart, share_column)
        counts = _numeric(chart, count_column)
        labels = share.map(
            lambda value: f"{value:.0f}%" if pd.notna(value) and value >= 7 else ""
        )
        figure.add_trace(
            go.Bar(
                y=chart["city"],
                x=share,
                orientation="h",
                name=name,
                marker_color=COLORS[color],
                text=labels,
                textposition="inside",
                insidetextanchor="middle",
                customdata=np.column_stack(
                    [
                        _numeric(chart, "forecast_match_count"),
                        counts,
                        _numeric(chart, "forecast_attendance_base"),
                    ]
                ),
                hovertemplate=(
                    "<b>%{y}</b><br>Hosted matches: %{customdata[0]:,.0f}"
                    f"<br>{name}: %{{customdata[1]:,.0f}} attendees"
                    "<br>Share of base attendance: %{x:.1f}%"
                    "<br>Base tournament attendance: %{customdata[2]:,.0f}<extra></extra>"
                ),
            )
        )
    figure.update_layout(
        barmode="stack",
        uniformtext_minsize=9,
        uniformtext_mode="hide",
    )
    figure.update_xaxes(
        title="Share of base attendance scenario",
        range=[0, 100],
        ticksuffix="%",
    )
    return style_figure(figure, 540, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_actions_chart(frame: pd.DataFrame) -> go.Figure:
    """Show the physical benefit and named priority screen for each host."""

    chart = frame.copy()
    chart["_resolved"] = _numeric(chart, "top_gap_resolved")
    chart = chart.dropna(subset=["_resolved"]).sort_values(["_resolved", "city"])
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_resolved"],
            orientation="h",
            marker_color=COLORS["teal"],
            text=chart["top_intervention"].fillna("No qualified screen"),
            textposition="inside",
            customdata=np.column_stack(
                [
                    chart["representative_match_id"].fillna("Not available"),
                    chart["top_intervention"].fillna("No qualified screen"),
                    chart["top_scope"].fillna("Not defined"),
                    _numeric(chart, "top_cost_base"),
                    chart["top_lead_time"].fillna("Not defined"),
                    chart["top_evidence_quality"].fillna("unavailable"),
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Representative match: %{customdata[0]}"
                "<br>Priority screen: %{customdata[1]}"
                "<br>Scope: %{customdata[2]}"
                "<br>Peak demand addressed: %{x:,.0f}/hour"
                "<br>Total planning cost: $%{customdata[3]:,.0f}"
                "<br>Lead time: %{customdata[4]}"
                "<br>Evidence quality: %{customdata[5]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_xaxes(title="Modeled peak passengers addressed per hour", rangemode="tozero")
    return style_figure(figure, 520, legend=False, margin=dict(l=18, r=18, t=28, b=38))


def portfolio_outcome_chart(frame: pd.DataFrame, outcome: str) -> go.Figure:
    """Compare one explicit outcome from each city's priority single measure."""

    choices = {
        "Access": ("top_gap_resolved", "Peak passengers addressed per hour", "teal"),
        "Traffic": ("top_vehicle_trips_avoided", "Modeled venue-area vehicle trips avoided", "blue"),
        "CO2e": ("top_net_co2e_kg", "Modeled net CO2e avoided (kg)", "violet"),
    }
    column, axis_title, color = choices.get(outcome, choices["Access"])
    chart = frame.copy()
    chart["_value"] = _numeric(chart, column)
    chart = chart.dropna(subset=["_value"]).sort_values(["_value", "city"])
    colors = chart["_value"].map(
        lambda value: COLORS[color] if value >= 0 else COLORS["coral"]
    )
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_value"],
            orientation="h",
            marker_color=colors,
            text=chart["_value"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            customdata=np.column_stack(
                [
                    chart["top_intervention"].fillna("No qualified screen"),
                    chart["representative_match_id"].fillna("Not available"),
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Priority screen: %{customdata[0]}"
                "<br>Representative match: %{customdata[1]}"
                "<br>" + axis_title + ": %{x:,.0f}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_xaxes(title=axis_title, zeroline=True, zerolinecolor=COLORS["line"])
    return style_figure(figure, 520, legend=False, margin=dict(l=18, r=58, t=28, b=38))


def portfolio_traffic_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare baseline venue-area vehicle trips without implying roadway congestion."""

    chart = frame.copy()
    chart["_low"] = _numeric(chart, "baseline_vehicle_trips_low")
    chart["_base"] = _numeric(chart, "baseline_vehicle_trips_base")
    chart["_high"] = _numeric(chart, "baseline_vehicle_trips_high")
    chart = chart.dropna(subset=["_base"]).sort_values(["_base", "city"])
    upper = (chart["_high"] - chart["_base"]).clip(lower=0).fillna(0)
    lower = (chart["_base"] - chart["_low"]).clip(lower=0).fillna(0)
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_base"],
            orientation="h",
            marker_color=COLORS["blue"],
            text=chart["_base"],
            texttemplate="%{text:,.0f}",
            textposition="outside",
            error_x=dict(
                type="data",
                array=upper,
                arrayminus=lower,
                color=COLORS["slate"],
                thickness=1.2,
                width=3,
            ),
            customdata=np.column_stack(
                [
                    chart["representative_match_id"].fillna("Not available"),
                    chart["_low"],
                    chart["_high"],
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Representative match: %{customdata[0]}"
                "<br>Base vehicle trips: %{x:,.0f}"
                "<br>Input-case range: %{customdata[1]:,.0f}–%{customdata[2]:,.0f}"
                "<br>Venue-area trips, not roadway congestion<extra></extra>"
            ),
            showlegend=False,
        )
    )
    maximum = float(chart["_high"].max()) if not chart.empty and chart["_high"].notna().any() else 1.0
    figure.update_xaxes(title="Modeled venue-area vehicle trips", range=[0, maximum * 1.12])
    return style_figure(figure, 510, legend=False, margin=dict(l=18, r=50, t=28, b=38))


def portfolio_climate_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare base-case net CO2e avoided by each city's common qualified measure."""

    chart = frame.copy()
    chart["_co2e"] = _numeric(chart, "top_net_co2e_kg")
    chart = chart.dropna(subset=["_co2e"]).sort_values(["_co2e", "city"])
    colors = chart["_co2e"].map(lambda value: COLORS["teal"] if value >= 0 else COLORS["coral"])
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_co2e"],
            orientation="h",
            marker_color=colors,
            text=chart["_co2e"],
            texttemplate="%{text:,.0f} kg",
            textposition="outside",
            customdata=np.column_stack(
                [
                    chart["representative_match_id"].fillna("Not available"),
                    chart["lowest_cost_intervention"].fillna("Not available"),
                    chart["top_scope"].fillna("Not defined"),
                    chart["top_evidence_quality"].fillna("unavailable"),
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Representative match: %{customdata[0]}"
                "<br>Qualified single measure: %{customdata[1]}"
                "<br>Proposed scale: %{customdata[2]}"
                "<br>Base-case net CO2e avoided: %{x:,.0f} kg"
                "<br>Evidence quality: %{customdata[3]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    minimum = min(float(chart["_co2e"].min()), 0.0) if not chart.empty else 0.0
    maximum = max(float(chart["_co2e"].max()), 1.0) if not chart.empty else 1.0
    figure.update_xaxes(
        title="Modeled net CO2e avoided (kg, base case)",
        range=[minimum * 1.12, maximum * 1.25],
        zeroline=True,
        zerolinecolor=COLORS["line"],
    )
    return style_figure(figure, 510, legend=False, margin=dict(l=18, r=58, t=28, b=38))


def readiness_ranking_chart(frame: pd.DataFrame) -> go.Figure:
    """Rank cities by the weighted readiness index used on the current screen."""

    chart = frame.copy()
    chart["_score"] = _numeric(chart, "strict_score")
    chart = chart.dropna(subset=["_score"]).sort_values(["_score", "city"])
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_score"],
            orientation="h",
            marker=dict(color=chart["_score"], colorscale=READINESS_SCALE, cmin=0, cmax=100),
            text=chart["_score"],
            texttemplate="%{text:.1f}",
            textposition="outside",
            customdata=np.column_stack(
                [
                    chart["strict_rank"].fillna("Not ranked"),
                    chart["screening_confidence"].fillna("unavailable"),
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Readiness score: %{x:.1f}/100"
                "<br>Readiness rank: %{customdata[0]}"
                "<br>Evidence confidence: %{customdata[1]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_xaxes(title="Weighted readiness score (0–100)", range=[0, 105])
    return style_figure(figure, 480, legend=False, margin=dict(l=18, r=42, t=22, b=38))


def readiness_components_chart(metrics: pd.DataFrame, city_order: list[str]) -> go.Figure:
    """Expose the four normalized criteria behind the readiness score."""

    chart = metrics.copy()
    chart = chart.set_index("city").reindex(city_order)
    values = np.column_stack([_numeric(chart, column) for column in READINESS_COMPONENTS.values()])
    evidence = np.column_stack(
        [chart.get(column.replace("_score", "_status"), pd.Series("unavailable", index=chart.index)).fillna("unavailable")
         for column in READINESS_COMPONENTS.values()]
    )
    figure = go.Figure(
        go.Heatmap(
            z=values,
            x=["Transit<br>proximity", "Heat<br>safety", "Urban heat<br>safety", "Venue<br>support"],
            y=chart.index.tolist(),
            zmin=0,
            zmax=100,
            colorscale=READINESS_SCALE,
            text=np.where(pd.isna(values), "—", np.round(values).astype(object)),
            texttemplate="%{text}",
            customdata=evidence,
            colorbar=dict(
                title=dict(text="Score", side="top"),
                orientation="h",
                x=.5,
                xanchor="center",
                y=1.08,
                yanchor="bottom",
                thickness=9,
                len=.58,
                outlinewidth=0,
            ),
            hovertemplate=(
                "<b>%{y}</b><br>%{x}: %{z:.1f}/100"
                "<br>Evidence status: %{customdata}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title=None, side="bottom", tickangle=0)
    figure.update_yaxes(title=None, showticklabels=True)
    return style_figure(figure, 500, legend=False, margin=dict(l=18, r=18, t=58, b=38))
