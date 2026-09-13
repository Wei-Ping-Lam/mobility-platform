"""Decision-focused portfolio visualizations for the all-city landing page."""

from __future__ import annotations

from html import escape
from textwrap import shorten, wrap

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from dashboard.viz.style import COLORS, READINESS_SCALE, style_figure, style_map

READINESS_COMPONENTS = {
    "First/last-mile access": "gap_score",
    "Traffic management": "traffic_score",
    "Heat safety": "heat_score",
    "Venue support": "access_score",
}


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column), errors="coerce")


def portfolio_sustainability_access_chart(frame: pd.DataFrame) -> go.Figure:
    """Plot sustainability score against the first/last-mile access score, all hosts at once.

    Sustainability (100 - parking density, 50%; real fleet electrification,
    30%; real pedestrian-infrastructure evidence, 20%) is a deliberately
    separate signal from access - a city can score well on one and poorly on
    the other (e.g. Atlanta's downtown venue has both strong transit and
    abundant nearby parking, so it scores near the top on access but near the
    bottom on sustainability). The access score blends a transit-access score
    (real GTFS transit-stop density, real GTFS event-window departure
    frequency, and real published/benchmark dedicated-service evidence) with
    real parking-facility density (75/25, transit access weighted more
    heavily as more reliable evidence; falls back to whichever components are
    available for a city); it does not factor in heat. Bubble size is venue
    capacity; color is average summer temperature - shown for context only,
    since it feeds neither score.
    """

    chart = frame.copy()
    chart["_sustainability"] = _numeric(chart, "sustainability_score")
    chart["_access"] = _numeric(chart, "gap_score")
    chart["_temp"] = _numeric(chart, "avg_temp_c")
    chart["_capacity"] = _numeric(chart, "capacity")
    chart = chart.dropna(subset=["_sustainability", "_access"])

    max_capacity = float(chart["_capacity"].fillna(0).max())
    sizeref = (2.0 * max_capacity / (46.0**2)) if max_capacity > 0 else 1.0

    figure = go.Figure(
        go.Scatter(
            x=chart["_sustainability"],
            y=chart["_access"],
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
                "<b>%{text}</b><br>Sustainability score: %{x:.0f}/100"
                "<br>First/last-mile access score: %{y:.0f}/100"
                "<br>Venue capacity: %{customdata[0]:,.0f}"
                "<br>Avg summer temp: %{customdata[1]:.1f}°C<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title="Sustainability score (0-100)", range=[-5, 108])
    figure.update_yaxes(title="First/last-mile access score")
    return style_figure(figure, 520, legend=False, margin=dict(l=18, r=18, t=42, b=38))


def portfolio_access_density_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare GTFS transit-stop density and OSM parking-facility density around each venue, together.

    One grouped bar chart, six bars per city: the three transit-stop rings
    (solid color) sit on the left of each city's cluster, the three parking-
    facility rings (same three hues, lighter shade) sit on the right, so
    transit and parking density read as two side-by-side blocks per city
    instead of across two separately-sorted charts. Both counts share one
    axis since they run in comparable ranges (roughly 0-600 real facilities/
    stops across hosts). Sorted by transit stops within 1 mi - the more
    heavily weighted signal in the first/last-mile access score - since the
    two metrics don't always rank hosts the same way. Cities with no parking
    snapshot yet still show their transit bars; a text note above the column
    marks the missing parking data instead of leaving an unexplained gap.
    """

    chart = frame.copy()
    chart["_transit_0_5mi"] = _numeric(chart, "transit_stops_0_5mi")
    chart["_transit_1mi"] = _numeric(chart, "gtfs_stops_1mi")
    chart["_transit_2mi"] = _numeric(chart, "gtfs_stops_2mi")
    chart = chart.dropna(subset=["_transit_1mi"]).sort_values("_transit_1mi", ascending=False)
    chart["_parking_0_5mi"] = _numeric(chart, "parking_count_0_5mi")
    chart["_parking_1mi"] = _numeric(chart, "parking_count_1mi")
    chart["_parking_2mi"] = _numeric(chart, "parking_count_2mi")

    nearest = _numeric(chart, "nearest_stop_mi")
    agencies = chart.get("gtfs_agencies", pd.Series(dtype=object)).fillna("Not available")
    tagged = _numeric(chart, "parking_facilities_with_capacity_tag")
    total = _numeric(chart, "parking_total_facilities")

    figure = go.Figure()
    rings = [
        ("0.5 mi", "_transit_0_5mi", "_parking_0_5mi", "parking_tagged_capacity_0_5mi", COLORS["teal"]),
        ("1 mi", "_transit_1mi", "_parking_1mi", "parking_tagged_capacity_1mi", COLORS["blue"]),
        ("2 mi", "_transit_2mi", "_parking_2mi", "parking_tagged_capacity_2mi", COLORS["violet"]),
    ]
    # All three transit bars first, then all three parking bars, so
    # barmode="group" clusters transit on the left half of each city's group
    # and parking on the right half, rather than interleaving ring pairs.
    for label, transit_column, _parking_column, _capacity_column, color in rings:
        figure.add_trace(
            go.Bar(
                x=chart["city"],
                y=chart[transit_column],
                name=f"Transit stops ({label})",
                legendgroup=label,
                marker_color=color,
                opacity=1.0,
                customdata=np.column_stack([nearest, agencies]),
                hovertemplate=(
                    f"<b>%{{x}}</b><br>Transit stops within {label}: %{{y:,.0f}}"
                    "<br>Nearest stop: %{customdata[0]:.2f} mi"
                    "<br>Agencies: %{customdata[1]}<extra></extra>"
                ),
            )
        )
    for label, _transit_column, parking_column, capacity_column, color in rings:
        capacity = _numeric(chart, capacity_column)
        figure.add_trace(
            go.Bar(
                x=chart["city"],
                y=chart[parking_column],
                name=f"Parking facilities ({label})",
                legendgroup=label,
                marker_color=color,
                opacity=0.45,
                customdata=np.column_stack([capacity, tagged, total]),
                hovertemplate=(
                    f"<b>%{{x}}</b><br>Parking facilities within {label}: %{{y:,.0f}}"
                    "<br>Spaces recorded in this ring: %{customdata[0]:,.0f} (OSM capacity tag only)"
                    "<br>%{customdata[1]:,.0f} of %{customdata[2]:,.0f} facilities citywide (2 mi) have "
                    "that tag - most don't, so this undercounts true capacity<extra></extra>"
                ),
            )
        )

    # Mark cities with no parking snapshot at all, rather than leaving an
    # unexplained empty half of their bar group. Positioned at a fixed height
    # above the tallest transit bar in the whole chart so it never collides
    # with any city's own bars, wherever that city sits in the sort order.
    missing_parking_cities = chart.loc[
        chart[["_parking_0_5mi", "_parking_1mi", "_parking_2mi"]].isna().all(axis=1), "city"
    ]
    figure.update_layout(barmode="group", uniformtext_minsize=8, uniformtext_mode="hide")
    figure.update_yaxes(title="Transit stops / parking facilities within ring")
    if not missing_parking_cities.empty:
        transit_max = pd.concat([chart["_transit_0_5mi"], chart["_transit_1mi"], chart["_transit_2mi"]]).max()
        note_y = float(transit_max) * 1.08 if pd.notna(transit_max) and transit_max > 0 else 1.0
        for city in missing_parking_cities:
            figure.add_annotation(
                x=city, y=note_y, xref="x", yref="y", xanchor="center", yanchor="bottom",
                text="No parking data", showarrow=False,
                font=dict(size=10, color=COLORS["muted"]),
            )
        figure.update_yaxes(range=[0, note_y * 1.15])
    return style_figure(figure, 520, margin=dict(l=18, r=18, t=42, b=38))


# Fixed label placement per host city so the 11 static venue dots don't overlap
# each other on the national map at the default zoom (e.g. Boston/New York/NJ/
# Philadelphia and Dallas/Houston sit close together).
_MAP_LABEL_POSITIONS = {
    "Atlanta": "top center",
    "Boston": "top center",
    "Dallas": "top left",
    "Houston": "bottom right",
    "Kansas City": "top center",
    "Los Angeles": "bottom center",
    "Miami": "bottom center",
    "New York/NJ": "middle right",
    "Philadelphia": "bottom center",
    "San Francisco": "top left",
    "Seattle": "top center",
}


def readiness_map_chart(frame: pd.DataFrame) -> go.Figure:
    """Plot every host city as a dot at its venue location, colored by readiness score
    and sized by its venue's seating capacity.

    Scattermap's textposition is a per-trace scalar, not a per-point array, so
    cities are split into one trace per fixed label position (see
    _MAP_LABEL_POSITIONS) to keep the 11 static venue labels from overlapping.
    Only the first trace carries the colorbar; the rest share its color scale
    with showscale=False so it is not repeated per group.
    """

    chart = frame.copy()
    chart["_score"] = _numeric(chart, "strict_score")
    chart["_lat"] = _numeric(chart, "lat")
    chart["_lon"] = _numeric(chart, "lon")
    chart["_capacity"] = _numeric(chart, "capacity")
    chart["_matches"] = _numeric(chart, "forecast_match_count")
    chart["_furthest_stage"] = chart["forecast_furthest_stage"].fillna("Not available")
    chart["_position"] = chart["city"].map(_MAP_LABEL_POSITIONS).fillna("top center")
    chart = chart.dropna(subset=["_score", "_lat", "_lon", "_capacity"]).sort_values("city")

    # Real venue capacities only span about 65k-82.5k (roughly +/-13% either side
    # of the median), so a literal area-proportional size barely differs between
    # the smallest and largest venue. Min-max normalize to a much wider pixel
    # range instead, so the spread reads clearly even though the underlying
    # capacities are numerically close.
    min_capacity, max_capacity = chart["_capacity"].min(), chart["_capacity"].max()
    span = max_capacity - min_capacity
    if pd.notna(span) and span > 0:
        chart["_size"] = 20 + (chart["_capacity"] - min_capacity) / span * 34
    else:
        chart["_size"] = 32.0

    figure = go.Figure()
    for index, (position, group) in enumerate(chart.groupby("_position", sort=False)):
        is_first = index == 0
        figure.add_trace(
            go.Scattermap(
                lat=group["_lat"],
                lon=group["_lon"],
                mode="markers+text",
                marker=dict(
                    size=group["_size"],
                    color=group["_score"],
                    colorscale=READINESS_SCALE,
                    cmin=0,
                    cmax=100,
                    showscale=is_first,
                    colorbar=dict(
                        title=dict(text="Readiness score", side="top"),
                        orientation="h",
                        x=.5,
                        xanchor="center",
                        y=1.05,
                        yanchor="bottom",
                        thickness=9,
                        len=.58,
                        outlinewidth=0,
                    ) if is_first else None,
                ),
                text=group["city"],
                textposition=position,
                textfont=dict(size=11, color=COLORS["ink"]),
                customdata=np.column_stack(
                    [
                        group["strict_rank"].fillna("Not ranked"),
                        group["_score"],
                        group["_matches"],
                        group["_capacity"],
                        group["_furthest_stage"],
                    ]
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>Readiness score: %{customdata[1]:.1f}/100"
                    "<br>Readiness rank: %{customdata[0]}"
                    "<br>Hosted matches: %{customdata[2]:.0f}"
                    "<br>Venue capacity: %{customdata[3]:,.0f}"
                    "<br>Furthest round played: %{customdata[4]}<extra></extra>"
                ),
                showlegend=False,
            )
        )
    return style_map(figure, 480, zoom=2.3, lat=38.0, lon=-97.0)


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


def city_hourly_movement_chart(hourly_movement: pd.DataFrame, city: str) -> go.Figure:
    """Show one host city's average modeled hourly passenger movement, relative to kickoff.

    Averages arrivals and departures across every hosted match in the city so a
    single match's attendance scenario doesn't dominate the shape.
    """

    chart = hourly_movement[hourly_movement["city"] == city].sort_values("hours_from_kickoff")
    for direction in ("arrivals", "departures"):
        base_column = f"avg_{direction}_base"
        for case in ("low", "high"):
            column = f"avg_{direction}_{case}"
            if column not in chart.columns:
                chart[column] = chart[base_column]

    # Arrival buckets only exist at hours -4..1 (a small tail of the arrival
    # profile lands one hour after kickoff, i.e. latecomers) and departure
    # buckets only at hours 1..5 (kickoff + the assumed 120-minute match
    # length, with a small early-leaver share one hour before that). Restrict
    # each line to its own real domain rather than flat-lining across the
    # other direction's whole range.
    arrivals = chart.loc[
        chart["hours_from_kickoff"] <= 1,
        ["hours_from_kickoff", "avg_arrivals_low", "avg_arrivals_base", "avg_arrivals_high"],
    ]
    departures = chart.loc[
        chart["hours_from_kickoff"] >= 1,
        ["hours_from_kickoff", "avg_departures_low", "avg_departures_base", "avg_departures_high"],
    ]

    figure = go.Figure()
    for movement, direction, color, fill_color, label in (
        (arrivals, "arrivals", COLORS["teal_light"], "rgba(11, 113, 105, .26)", "Arrivals planning range"),
        (departures, "departures", COLORS["coral"], "rgba(185, 83, 58, .24)", "Departures planning range"),
    ):
        low_column = f"avg_{direction}_low"
        high_column = f"avg_{direction}_high"
        figure.add_trace(
            go.Scatter(
                x=movement["hours_from_kickoff"],
                y=movement[high_column],
                mode="lines",
                line=dict(color=color, width=1, dash="dot"),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=movement["hours_from_kickoff"],
                y=movement[low_column],
                mode="lines",
                fill="tonexty",
                fillcolor=fill_color,
                line=dict(color=color, width=1, dash="dot"),
                name=label,
                hoverinfo="skip",
            )
        )
    figure.add_trace(
        go.Scatter(
            x=arrivals["hours_from_kickoff"],
            y=arrivals["avg_arrivals_base"],
            mode="lines+markers",
            name="Arrivals",
            line=dict(color=COLORS["teal"], width=3),
            marker=dict(size=7),
            customdata=np.column_stack([arrivals["avg_arrivals_low"], arrivals["avg_arrivals_high"]]),
            hovertemplate=(
                "<b>%{x:+.0f}h from kickoff</b><br>Avg arrivals: %{y:,.0f}/hour"
                "<br>Planning range: %{customdata[0]:,.0f}-%{customdata[1]:,.0f}/hour<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=departures["hours_from_kickoff"],
            y=departures["avg_departures_base"],
            mode="lines+markers",
            name="Departures",
            line=dict(color=COLORS["coral"], width=3),
            marker=dict(size=7),
            customdata=np.column_stack([departures["avg_departures_low"], departures["avg_departures_high"]]),
            hovertemplate=(
                "<b>%{x:+.0f}h from kickoff</b><br>Avg departures: %{y:,.0f}/hour"
                "<br>Planning range: %{customdata[0]:,.0f}-%{customdata[1]:,.0f}/hour<extra></extra>"
            ),
        )
    )
    figure.add_vline(x=0, line_dash="dot", line_color=COLORS["muted"])
    figure.update_xaxes(title="Hours from kickoff", dtick=1, zeroline=False)
    figure.update_yaxes(title="Average modeled passengers / hour")
    return style_figure(figure, 530, margin=dict(l=18, r=18, t=42, b=38))


def transit_solution_comparison_chart(
    options: pd.DataFrame, recommended: dict | None = None,
) -> go.Figure:
    """Four distinct solution types, with compact numbered markers and a key."""
    figure = go.Figure()
    colors = ("blue", "amber", "teal", "violet", "coral")
    records = options.to_dict("records")
    if recommended is not None:
        records.append(recommended)
    for index, row in enumerate(records):
        is_recommended = recommended is not None and index == len(records) - 1
        context = row.get("city_context", "")
        has_context = context in {"Existing approach", "Related approach", "Published plan"}
        number = "R" if is_recommended else str(index + 1)
        label = "Recommended first action" if is_recommended else f"{number}. {row['label']}"
        if has_context:
            label += f"<br>{context}"
        name = "<br>".join(escape(line) for line in wrap(row["solution"], width=32))
        figure.add_trace(go.Scatter(
            x=[row["passengers"]], y=[row["net_co2e_kg"]],
            mode="markers+text", name=label,
            text=[number], textposition="middle center",
            textfont=dict(color="white", size=14),
            marker=dict(size=42 if is_recommended else 30, color=COLORS[colors[index]],
                        symbol="star" if is_recommended else "diamond" if has_context else "circle",
                        line=dict(width=2, color=COLORS["ink"] if has_context else COLORS["surface"])),
            customdata=[[name, row["shifted_passengers"], row["net_vehicle_miles"],
                         "Recommended first action" if is_recommended else context or "Planning scenario",
                         row.get("co2e_screen", "Not assessed")]],
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>Passengers addressed: %{x:,.0f} / match"
                "<br>Net CO2e avoided: %{y:,.0f} kg / match"
                "<br>Shifted from cars: %{customdata[1]:,.0f}"
                "<br>Net vehicle-miles saved: %{customdata[2]:,.0f}"
                "<br>%{customdata[3]}<br>Operating CO2e screen: %{customdata[4]}<extra></extra>"
            ),
            hoverlabel=dict(align="left", font_size=12),
        ))
    figure.update_xaxes(title="Passengers addressed per match", rangemode="tozero", tickformat=",")
    figure.update_yaxes(title="Net CO2e avoided (kg / match)", rangemode="tozero", tickformat=",",
                        zeroline=True, zerolinecolor=COLORS["muted"], zerolinewidth=1)
    figure = style_figure(figure, 550, margin=dict(l=18, r=18, t=25, b=190))
    if records:
        plotted = pd.DataFrame(records)
        xmax = max(float(plotted["passengers"].max()), 1.0)
        ymin = min(float(plotted["net_co2e_kg"].min()), 0.0)
        ymax = max(float(plotted["net_co2e_kg"].max()), 0.0)
        padding = max((ymax - ymin) * 0.15, 1.0)
        figure.update_xaxes(range=[-xmax * 0.08, xmax * 1.12])
        figure.update_yaxes(range=[ymin - padding, ymax + padding])
    figure.update_yaxes(zeroline=True)
    figure.update_layout(legend=dict(orientation="h", x=0, y=-0.22, yanchor="top",
                                    entrywidth=0.5, entrywidthmode="fraction",
                                    font=dict(size=11), itemclick=False, itemdoubleclick=False))
    return figure


def city_action_options_chart(options: pd.DataFrame) -> go.Figure:
    """Compare one match's screened intervention options on cost vs peak-demand impact.

    One point per named intervention (Shuttle service, Added transit frequency,
    Cooled walking corridors, Arrival spreading and curb management) - the same
    real, scenario-labeled numbers shown in the table next to it, plotted so
    cost and impact can be read against each other at a glance. Qualified
    options (teal) have a real local route/evidence assignment; exploratory
    options (slate) are missing one (e.g. a route or terminal) and aren't
    ready to fund yet.
    """

    chart = options.dropna(subset=["cost_per_passenger", "gap_resolved_passengers"]).copy()
    if chart.empty:
        return style_figure(go.Figure(), 380, legend=False, margin=dict(l=18, r=18, t=42, b=38))
    colors = [COLORS["teal"] if qualified else COLORS["slate"] for qualified in chart["evidence_qualified"]]
    evidence_label = chart["evidence_qualified"].map({True: "Qualified", False: "Exploratory"})
    figure = go.Figure(
        go.Scatter(
            x=chart["cost_per_passenger"],
            y=chart["gap_resolved_passengers"],
            mode="markers+text",
            text=chart["intervention"],
            textposition="top center",
            textfont=dict(size=10, color=COLORS["ink"]),
            marker=dict(size=16, color=colors, line=dict(width=1, color=COLORS["surface"])),
            customdata=np.column_stack([chart["lead_time_band"], evidence_label]),
            hovertemplate=(
                "<b>%{text}</b><br>Screening cost ratio: $%{x:.2f} / passenger"
                "<br>Peak demand addressed: %{y:,.0f} passengers"
                "<br>Lead time: %{customdata[0]}"
                "<br>Evidence: %{customdata[1]}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(title="Screening cost ratio ($ / peak passenger addressed)")
    figure.update_yaxes(title="Peak demand addressed (passengers)")
    return style_figure(figure, 380, legend=False, margin=dict(l=18, r=18, t=42, b=38))


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
                ("Scheduled transit demand (bus, rail, subway)", "mode_scheduled_transit_share_pct", "mode_scheduled_transit_attendees_base", "teal"),
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
    figure = style_figure(figure, 540, margin=dict(l=18, r=18, t=42, b=38))
    # Traces are added (and stack left-to-right) in reading order - Host market
    # first - but Plotly defaults stacked bar/area legends to the opposite of
    # trace-add order, so it must be forced back to "normal" to match what the
    # stacked bars actually show left-to-right.
    figure.update_layout(legend=dict(traceorder="normal"))
    return figure


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
                    _numeric(chart, "forecast_match_count"),
                    _numeric(chart, "capacity"),
                    chart["forecast_furthest_stage"].fillna("Not available"),
                ]
            ),
            hovertemplate=(
                "<b>%{y}</b><br>Readiness score: %{x:.1f}/100"
                "<br>Readiness rank: %{customdata[0]}"
                "<br>Hosted matches: %{customdata[1]:.0f}"
                "<br>Venue capacity: %{customdata[2]:,.0f}"
                "<br>Furthest round played: %{customdata[3]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_xaxes(title="Weighted readiness score (0–100)", range=[0, 105])
    return style_figure(figure, 480, legend=False, margin=dict(l=18, r=42, t=22, b=38))


def portfolio_frequency_benchmark_chart(frame: pd.DataFrame) -> go.Figure:
    """Compare the two newer transit-access inputs - real event-window frequency and
    real published/benchmark dedicated-service evidence - all hosts at once.

    Both feed transit_access_score (30% each) alongside stop density (40%);
    neither is visible in the stop/parking density chart above, so this is
    the only place a host's frequency and benchmark-evidence standing show up
    on their own. Sorted by frequency score, since it's the more granular of
    the two (benchmark evidence is only a 100/60 tier).
    """

    chart = frame.copy()
    chart["_frequency"] = _numeric(chart, "frequency_score")
    chart["_benchmark"] = _numeric(chart, "benchmark_capacity_score")
    chart = chart.dropna(subset=["_frequency", "_benchmark"], how="all").sort_values(
        ["_frequency", "city"], ascending=[False, True], na_position="last"
    )
    departures = _numeric(chart, "event_window_departures")
    tier_label = chart["_benchmark"].map(
        lambda value: "High-frequency rail/BRT" if value == 100 else "Dedicated shuttle/bus" if value == 60 else "Not available"
    )
    basis = chart.get("dedicated_service_basis", pd.Series(dtype=object)).fillna("Not available")
    publisher = chart.get("dedicated_service_publisher", pd.Series(dtype=object)).fillna("Not available")
    # Keep previews compact; full evidence and citations remain in the table below.
    basis = basis.map(lambda value: "<br>".join(
        escape(line) for line in wrap(shorten(str(value), width=180, placeholder="..."), width=32)
    ))
    publisher = publisher.map(lambda value: "<br>".join(
        escape(line) for line in wrap(shorten(str(value), width=80, placeholder="..."), width=32)
    ))

    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=chart["city"],
            y=chart["_frequency"],
            name="Event-window frequency score",
            marker_color=COLORS["blue"],
            customdata=np.column_stack([departures]),
            hovertemplate=(
                "<b>%{x}</b><br>Frequency score: %{y:.1f}/100"
                "<br>Real event-window departures: %{customdata[0]:,.0f}<extra></extra>"
            ),
        )
    )
    figure.add_trace(
        go.Bar(
            x=chart["city"],
            y=chart["_benchmark"],
            name="Published-service evidence tier",
            marker_color=COLORS["violet"],
            customdata=np.column_stack([tier_label, basis, publisher]),
            hovertemplate=(
                "<b>%{x}</b><br>%{customdata[0]}<br>Score: %{y:.0f}/100"
                "<br>%{customdata[1]}<br>Source:<br>%{customdata[2]}"
                "<br>Full details in evidence table.<extra></extra>"
            ),
            hoverlabel=dict(align="left", font_size=12),
        )
    )
    figure.update_layout(barmode="group", uniformtext_minsize=8, uniformtext_mode="hide")
    figure.update_yaxes(title="Score (0–100)", range=[0, 105])
    return style_figure(figure, 480, margin=dict(l=18, r=18, t=42, b=38))


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
            x=[label.replace(" ", "<br>", 1) for label in READINESS_COMPONENTS],
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


def transportation_resilience_ranking_chart(frame: pd.DataFrame) -> go.Figure:
    """Rank cities by the 0-10 transportation resilience rating.

    Blends real demand-surge stress-test coverage (50%), real GTFS
    event-window departure frequency (30%), and real published dedicated-
    capacity evidence (20%) - see dashboard/ui/portfolio/context.py's
    _with_resilience_score for the exact formula and why raw nearby route
    density was deliberately excluded. Renormalizes over whichever
    components are real for a city; unavailable only if none are.
    """

    chart = frame.copy()
    chart["_rating"] = _numeric(chart, "resilience_rating")
    chart = chart.dropna(subset=["_rating"]).sort_values(["_rating", "city"])
    stress = _numeric(chart, "stress_coverage_pct")
    frequency = _numeric(chart, "frequency_score")
    benchmark = _numeric(chart, "benchmark_capacity_score")
    figure = go.Figure(
        go.Bar(
            y=chart["city"],
            x=chart["_rating"],
            orientation="h",
            marker=dict(color=chart["_rating"], colorscale=READINESS_SCALE, cmin=0, cmax=10),
            text=chart["_rating"],
            texttemplate="%{text:.1f}",
            textposition="outside",
            customdata=np.column_stack([stress, frequency, benchmark]),
            hovertemplate=(
                "<b>%{y}</b><br>Transportation resilience: %{x:.1f}/10"
                "<br>Stress-test coverage (after a 10% demand surge + 20% capacity loss): %{customdata[0]:.1f}%"
                "<br>Event-window frequency score: %{customdata[1]:.1f}/100"
                "<br>Published dedicated-capacity evidence: %{customdata[2]:.0f}/100<extra></extra>"
            ),
            showlegend=False,
        )
    )
    figure.update_xaxes(title="Transportation resilience rating (0–10)", range=[0, 10.6])
    return style_figure(figure, 480, legend=False, margin=dict(l=18, r=42, t=22, b=38))


def transportation_resilience_components_chart(frame: pd.DataFrame, city_order: list[str]) -> go.Figure:
    """Expose the three real signals blended into the transportation resilience rating."""

    columns = {
        "stress_coverage_pct": "Stress-test<br>coverage",
        "frequency_score": "Event-window<br>frequency",
        "benchmark_capacity_score": "Published-capacity<br>evidence",
    }
    chart = frame.copy().set_index("city").reindex(city_order)
    values = np.column_stack([_numeric(chart, column) for column in columns])
    figure = go.Figure(
        go.Heatmap(
            z=values,
            x=list(columns.values()),
            y=chart.index.tolist(),
            zmin=0,
            zmax=100,
            colorscale=READINESS_SCALE,
            text=np.where(pd.isna(values), "—", np.round(values).astype(object)),
            texttemplate="%{text}",
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
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}/100<extra></extra>",
        )
    )
    figure.update_xaxes(title=None, side="bottom", tickangle=0)
    figure.update_yaxes(title=None, showticklabels=True)
    return style_figure(figure, 460, legend=False, margin=dict(l=18, r=18, t=58, b=38))


def access_sustainability_components_chart(frame: pd.DataFrame, city_order: list[str]) -> go.Figure:
    """Expose every real input behind the first/last-mile access and sustainability

    scores, side by side - the same "What drives readiness?" heatmap style used
    in the Overview tab, applied to this tab's two composites instead.
    """

    chart = frame.copy().set_index("city").reindex(city_order)
    parking = _numeric(chart, "parking_score")
    columns: dict[str, tuple[pd.Series, str]] = {
        "Transit-stop<br>density": (_numeric(chart, "transit_score"), "transit_status"),
        "Event-window<br>frequency": (_numeric(chart, "frequency_score"), "frequency_status"),
        "Dedicated-service<br>evidence": (_numeric(chart, "benchmark_capacity_score"), "benchmark_capacity_status"),
        "Pedestrian<br>infrastructure": (
            _numeric(chart, "pedestrian_infrastructure_score"),
            "pedestrian_infrastructure_status",
        ),
        "Parking-facility<br>density (0.5mi)": (parking, "parking_status"),
        "Fleet<br>electrification": (_numeric(chart, "fleet_electrification_score"), "fleet_electrification_status"),
    }
    values = np.column_stack([series.to_numpy() for series, _ in columns.values()])
    evidence = np.column_stack(
        [
            chart.get(status_column, pd.Series("unavailable", index=chart.index)).fillna("unavailable")
            for _, status_column in columns.values()
        ]
    )
    figure = go.Figure(
        go.Heatmap(
            z=values,
            x=list(columns.keys()),
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
            hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}/100<br>Evidence: %{customdata}<extra></extra>",
        )
    )
    figure.update_xaxes(title=None, side="bottom", tickangle=0)
    figure.update_yaxes(title=None, showticklabels=True)
    return style_figure(figure, 500, legend=False, margin=dict(l=18, r=18, t=58, b=38))
