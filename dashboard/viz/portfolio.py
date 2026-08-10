"""Decision-focused portfolio visualizations for the all-city landing page."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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


def portfolio_gap_quadrant_chart(frame: pd.DataFrame) -> go.Figure:
    """Plot transit readiness against the first/last-mile gap score, all hosts at once.

    Bubble size is venue capacity; color is average summer temperature (heat
    compounds the gap score - a hotter walk from the nearest stop matters more).
    The dotted threshold lines are illustrative reference points chosen for this
    branch's current score distribution, not an evidenced cutoff.
    """

    chart = frame.copy()
    chart["_transit"] = _numeric(chart, "transit_score")
    chart["_gap"] = _numeric(chart, "first_last_mile_gap")
    chart["_temp"] = _numeric(chart, "avg_temp_c")
    chart["_capacity"] = _numeric(chart, "capacity")
    chart = chart.dropna(subset=["_transit", "_gap"])

    max_capacity = float(chart["_capacity"].fillna(0).max())
    sizeref = (2.0 * max_capacity / (46.0**2)) if max_capacity > 0 else 1.0

    figure = go.Figure(
        go.Scatter(
            x=chart["_transit"],
            y=chart["_gap"],
            mode="markers+text",
            text=chart["city"],
            textposition="top center",
            textfont=dict(size=10, color=COLORS["ink"]),
            marker=dict(
                size=chart["_capacity"],
                sizemode="area",
                sizeref=sizeref,
                sizemin=10,
                color=chart["_temp"],
                colorscale=[[0, COLORS["teal"]], [0.5, COLORS["amber"]], [1, COLORS["coral"]]],
                colorbar=dict(title="Avg summer<br>temp (°C)", thickness=12, len=0.7),
                line=dict(width=1, color=COLORS["surface"]),
            ),
            customdata=np.column_stack([chart["_capacity"].fillna(0), chart["_temp"]]),
            hovertemplate=(
                "<b>%{text}</b><br>Transit score: %{x:.0f}/100"
                "<br>First/last-mile gap score: %{y:.0f}"
                "<br>Venue capacity: %{customdata[0]:,.0f}"
                "<br>Avg summer temp: %{customdata[1]:.1f}°C<extra></extra>"
            ),
        )
    )
    figure.add_vline(
        x=60, line_dash="dot", line_color=COLORS["muted"],
        annotation_text="Low transit threshold", annotation_font=dict(size=10, color=COLORS["muted"]),
    )
    figure.add_hline(
        y=85, line_dash="dot", line_color=COLORS["muted"],
        annotation_text="High gap threshold", annotation_position="top left",
        annotation_font=dict(size=10, color=COLORS["muted"]),
    )
    figure.add_annotation(
        xref="paper", yref="paper", x=0.02, y=0.98, xanchor="left", yanchor="top",
        text="Weak transit + high gap", showarrow=False, font=dict(size=10, color=COLORS["coral"]),
    )
    figure.add_annotation(
        xref="paper", yref="paper", x=0.98, y=0.02, xanchor="right", yanchor="bottom",
        text="Strong transit + low gap", showarrow=False, font=dict(size=10, color=COLORS["teal"]),
    )
    figure.update_xaxes(title="Transit infrastructure score (0-100)", range=[-5, 108])
    figure.update_yaxes(title="First/last-mile gap score")
    return style_figure(figure, 520, legend=False, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_stop_density_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare GTFS-observed transit-stop density around each venue, all hosts at once."""

    chart = frame.copy()
    chart["_0_5mi"] = _numeric(chart, "transit_stops_0_5mi")
    chart["_1mi"] = _numeric(chart, "gtfs_stops_1mi")
    chart["_2mi"] = _numeric(chart, "gtfs_stops_2mi")
    chart = chart.dropna(subset=["_1mi"]).sort_values("_1mi", ascending=False)

    nearest = _numeric(chart, "nearest_stop_mi")
    agencies = chart.get("gtfs_agencies", pd.Series(dtype=object)).fillna("Not available")

    figure = go.Figure()
    bands = [
        ("Within 0.5 mi", "_0_5mi", COLORS["teal"]),
        ("Within 1 mi", "_1mi", COLORS["blue"]),
        ("Within 2 mi", "_2mi", COLORS["violet"]),
    ]
    for name, column, color in bands:
        figure.add_trace(
            go.Bar(
                x=chart["city"],
                y=chart[column],
                name=name,
                marker_color=color,
                text=chart[column],
                texttemplate="%{text:,.0f}",
                textposition="outside",
                customdata=np.column_stack([nearest, agencies]),
                hovertemplate=(
                    f"<b>%{{x}}</b><br>{name}: %{{y:,.0f}} stops"
                    "<br>Nearest stop: %{customdata[0]:.2f} mi"
                    "<br>Agencies: %{customdata[1]}<extra></extra>"
                ),
            )
        )
    figure.update_layout(barmode="group", uniformtext_minsize=8, uniformtext_mode="hide")
    figure.update_yaxes(title="Transit stops (GTFS)")
    return style_figure(figure, 480, margin=dict(l=18, r=18, t=42, b=38))


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
    """Dumbbell-compare modeled arrival and departure peaks for every host.

    A connecting line highlights the arrival-to-departure swing per city,
    which a grouped bar pair (two bars from zero) makes harder to read at a
    glance than two dots joined by a line.
    """

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
    line_x: list[float | None] = []
    line_y: list[str | None] = []
    for city, arrival, departure in zip(chart["city"], chart["_arrival"], chart["_departure"]):
        line_x += [arrival, departure, None]
        line_y += [city, city, None]
    figure.add_trace(
        go.Scatter(
            x=line_x,
            y=line_y,
            mode="lines",
            line=dict(color=COLORS["slate"], width=4),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figure.add_trace(
        go.Scatter(
            x=chart["_arrival"],
            y=chart["city"],
            mode="markers",
            name="Arrival peak",
            marker=dict(color=COLORS["blue"], size=13),
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
        go.Scatter(
            x=chart["_departure"],
            y=chart["city"],
            mode="markers",
            name="Departure peak",
            marker=dict(color=COLORS["violet"], size=13),
            customdata=customdata,
            hovertemplate=(
                "<b>%{y}</b><br>Departure peak: %{x:,.0f}/hour"
                "<br>Planning range: %{customdata[4]:,.0f}–%{customdata[5]:,.0f}/hour"
                "<br>Peak time: %{customdata[6]:+.0f} h from kickoff<extra></extra>"
            ),
        )
    )
    data_min = float(min(chart["_arrival"].min(), chart["_departure"].min()))
    data_max = float(max(chart["_arrival"].max(), chart["_departure"].max()))
    pad = (data_max - data_min) * 0.08 or max(data_max * 0.05, 1.0)
    figure.update_xaxes(
        title="Modeled passengers per peak hour",
        range=[data_min - pad, data_max + pad],
    )
    return style_figure(figure, 530, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_transit_capacity_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare modeled transit demand against real scheduled capacity, per host.

    Scheduled transit is the only mode with an evidenced capacity ceiling in the
    supplied data (each host's real GTFS scheduled service). This applies each
    host's own modeled Scheduled-transit demand share to its arrival and
    departure peak volumes, then divides by that host's real scheduled
    capacity. A log axis is used because the range is wide - some venues have
    almost no nearby scheduled service, so modeled demand there reaches many
    times capacity. Hosts with zero supplied scheduled capacity have no bar;
    they're listed separately since a ratio against zero is undefined, not zero.
    """

    forecast_fields = "forecast_arrival_peak_base" in frame.columns
    prefix = "forecast_" if forecast_fields else ""
    arrival = _numeric(frame, f"{prefix}arrival_peak_base")
    departure = _numeric(frame, f"{prefix}departure_peak_base")
    share = _numeric(frame, "mode_scheduled_transit_share_pct") / 100.0
    capacity = _numeric(frame, "scheduled_transit_capacity_pph")

    chart = frame[["city"]].copy()
    chart["_arrival_demand"] = arrival * share
    chart["_departure_demand"] = departure * share
    chart["_capacity"] = capacity
    has_capacity = chart["_capacity"].notna() & (chart["_capacity"] > 0)
    no_capacity_cities = sorted(chart.loc[~has_capacity, "city"].dropna().tolist())
    chart = chart[has_capacity].copy()
    chart["_arrival_pct"] = chart["_arrival_demand"] / chart["_capacity"] * 100
    chart["_departure_pct"] = chart["_departure_demand"] / chart["_capacity"] * 100
    chart = chart.dropna(subset=["_arrival_pct", "_departure_pct"]).sort_values(
        "_departure_pct", ascending=False
    )

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=chart["city"],
            y=chart["_arrival_pct"],
            name="Arrival peak",
            marker_color=COLORS["blue"],
            customdata=chart["_arrival_demand"],
            hovertemplate=(
                "<b>%{x}</b><br>Arrival: %{y:.0f}% of scheduled transit capacity"
                "<br>Modeled transit demand: %{customdata:,.0f}/hour<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Bar(
            x=chart["city"],
            y=chart["_departure_pct"],
            name="Departure peak",
            marker_color=COLORS["violet"],
            customdata=chart["_departure_demand"],
            hovertemplate=(
                "<b>%{x}</b><br>Departure: %{y:.0f}% of scheduled transit capacity"
                "<br>Modeled transit demand: %{customdata:,.0f}/hour<extra></extra>"
            ),
        )
    )
    figure.add_hline(
        y=100, line_dash="dot", line_color=COLORS["coral"],
        annotation_text="Full scheduled capacity", annotation_position="top left",
        annotation_font=dict(size=10, color=COLORS["coral"]),
    )
    if no_capacity_cities:
        figure.add_annotation(
            xref="paper", yref="paper", x=0.5, y=1.12, showarrow=False,
            text="No scheduled capacity in the supplied data: " + ", ".join(no_capacity_cities),
            font=dict(size=10, color=COLORS["muted"]),
        )
    figure.update_layout(barmode="group")
    figure.update_yaxes(title="% of scheduled transit capacity (log scale)", type="log")
    return style_figure(figure, 530, margin=dict(l=18, r=18, t=58, b=38))


def portfolio_visitor_forecast_chart(
    frame: pd.DataFrame, view: str
) -> go.Figure:
    """Compare one auditable visitor-flow forecast dimension across all hosts."""

    if view == "Peak timing":
        return portfolio_movement_chart(frame)
    settings = {
        "Attendee Origin": (
            [
                ("Host market", "origin_host_market_share_pct", "origin_host_market_attendees_base", "teal"),
                ("Nearby U.S.", "origin_nearby_us_share_pct", "origin_nearby_us_attendees_base", "blue"),
                ("Long-distance U.S.", "origin_long_distance_us_share_pct", "origin_long_distance_us_attendees_base", "violet"),
                ("International / unobserved", "origin_international_share_pct", "origin_international_attendees_base", "amber"),
            ],
            "forecast_non_host_share_pct",
        ),
        "Transportation Mode Mix": (
            [
                ("Scheduled transit demand", "mode_scheduled_transit_share_pct", "mode_scheduled_transit_attendees_base", "teal"),
                ("Shuttle / coach demand", "mode_shuttle_coach_share_pct", "mode_shuttle_coach_attendees_base", "blue"),
                ("Private vehicle / taxi demand", "mode_private_taxi_share_pct", "mode_private_taxi_attendees_base", "coral"),
                ("Walk / bike demand", "mode_walk_bike_share_pct", "mode_walk_bike_attendees_base", "amber"),
            ],
            "mode_scheduled_transit_share_pct",
        ),
    }
    series, sort_column = settings.get(view, settings["Attendee Origin"])
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


def portfolio_custom_scenario_chart(
    outcome: Mapping[str, Any], baseline_vehicle_trips: float | None
) -> go.Figure:
    """Baseline vs. a live-evaluated custom intervention scenario, for one city.

    Baseline bars are genuinely zero here, since no intervention resolves zero
    gap, avoids zero vehicle trips, and avoids zero CO2e by definition - seeing
    "0 -> evaluated value" for a scenario the user just built with sliders is
    the point of this view. Cost is reported separately (different unit), not
    plotted here.
    """

    categories = [
        "Peak passengers\naddressed / hr",
        "Vehicle trips\navoided",
        "Net CO2e\navoided (kg)",
    ]
    gap_resolved = float(outcome.get("gap_resolved_passengers") or 0)
    custom_trips = outcome.get("venue_vehicle_trips_base")
    trips_avoided = (
        max(float(baseline_vehicle_trips) - float(custom_trips), 0.0)
        if baseline_vehicle_trips is not None and custom_trips is not None
        else 0.0
    )
    co2e_avoided = float(outcome.get("net_co2e_kg_base") or 0)
    values = [gap_resolved, trips_avoided, co2e_avoided]

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=categories,
            y=[0, 0, 0],
            name="Baseline",
            marker_color=COLORS["slate"],
            text=["0", "0", "0"],
            textposition="outside",
            hovertemplate="<b>Baseline</b><br>%{x}: 0 (no intervention)<extra></extra>",
        )
    )
    figure.add_trace(
        go.Bar(
            x=categories,
            y=values,
            name="Custom scenario",
            marker_color=COLORS["blue"],
            text=[f"{v:,.0f}" for v in values],
            textposition="outside",
            hovertemplate="<b>Custom scenario</b><br>%{x}: %{y:,.0f}<extra></extra>",
        )
    )
    figure.update_layout(barmode="group", uniformtext_minsize=9, uniformtext_mode="hide")
    figure.update_yaxes(title="Modeled benefit (mixed units - see axis groups)", rangemode="tozero")
    return style_figure(figure, 420, margin=dict(l=18, r=18, t=42, b=38))


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
