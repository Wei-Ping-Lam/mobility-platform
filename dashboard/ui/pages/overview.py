"""Judge- and decision-maker-facing proof sequence."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.comparison import build_city_comparison
from dashboard.domain.portfolio import build_portfolio_timeline, portfolio_summary
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.models.interventions import factor_registry_from_snapshot, recommendation_candidates
from dashboard.ui.city.traffic_plan import render as render_traffic_plan
from dashboard.ui.presentation import build_presentation
from dashboard.ui.theme import callout, metric_card, page_header, section_header
from dashboard.viz.strategy_overlap import access_overlap_map
from dashboard.viz.style import COLORS, STATUS_COLORS, style_figure

_US_TIME_ZONE_ABBREVIATIONS = {-4: "ET", -5: "CT", -6: "MT", -7: "PT"}


def _format_kickoff(value: str | None) -> str:
    """Render an ISO 8601 kickoff timestamp (e.g. 2026-06-27T19:30:00-04:00) for readability."""

    if not value:
        return "Kickoff unavailable"
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    offset = moment.utcoffset()
    zone = _US_TIME_ZONE_ABBREVIATIONS.get(int(offset.total_seconds() // 3600)) if offset is not None else None
    hour_12 = moment.hour % 12 or 12
    period = "AM" if moment.hour < 12 else "PM"
    date_label = f"{moment.strftime('%B')} {moment.day}, {moment.year}"
    time_label = f"{hour_12}:{moment.minute:02d}{period}"
    return f"{date_label} {time_label}" + (f" {zone}" if zone else "")


def _number(value: Any, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.{decimals}f}{suffix}"


def _money(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.0f}K"
    return f"${value:,.0f}"


def _money_exact(value: Any, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"${float(value):,.{decimals}f}"


def _added_frequency_candidate(artifacts: Mapping[str, Any], city: str) -> str:
    walking = artifacts.get("walking_networks", {})
    city_walk = walking.get(city, {}) if isinstance(walking, Mapping) else {}
    target = city_walk.get("target_stop") if isinstance(city_walk, Mapping) else None
    if not isinstance(target, Mapping):
        return "no route-specific candidate established"
    agency = str(target.get("agency") or "Transit agency")
    route = str(target.get("route") or "route not identified")
    stop = str(target.get("name") or "stop not identified")
    return f"{agency} Route {route} at {stop}"


def _render_added_frequency_cost_basis(
    priority: Any,
    artifacts: Mapping[str, Any],
    *,
    city: str,
    match_id: str,
) -> None:
    if priority.intervention != "Added transit frequency":
        return
    snapshot = artifacts.get("factor_snapshot", {})
    factor_rows = snapshot.get("factors", {}) if isinstance(snapshot, Mapping) else {}
    cost_factor = factor_rows.get("transit_cost_per_departure", {})
    capacity_factor = factor_rows.get("transit_passengers_per_departure", {})
    load_factor = factor_rows.get("service_load_factor", {})
    if not all(isinstance(item, Mapping) for item in (cost_factor, capacity_factor, load_factor)):
        return
    city_input = next(
        (
            row
            for row in artifacts.get("city_intervention_inputs", [])
            if str(row.get("city")) == city and str(row.get("match_id")) == match_id
        ),
        {},
    )
    arrival_hours = float(city_input.get("arrival_window_hours") or 3.0)
    package = next(
        item for item in recommendation_candidates() if item.name == "Added transit frequency"
    )
    departures_per_hour = float(package.added_transit_departures_per_hour)
    event_departures = departures_per_hour * arrival_hours
    base_cost_per_departure = float(cost_factor.get("base") or 0)
    base_capacity = float(capacity_factor.get("base") or 0)
    usable_load = float(load_factor.get("base") or 0)
    peak_capacity = departures_per_hour * base_capacity * usable_load
    source_ids = list(cost_factor.get("source_ids", []))
    source_rows = snapshot.get("sources", {}) if isinstance(snapshot, Mapping) else {}
    source = source_rows.get(source_ids[0], {}) if source_ids else {}
    source_name = source.get("source") or "national transit operating-cost reference"
    source_url = source.get("url")
    candidate = _added_frequency_candidate(artifacts, city)

    with st.expander(
        "Why the unallocated added-service estimate is low",
        expanded=False,
        icon=":material/calculate:",
    ):
        st.markdown(
            f"**Route allocation:** unresolved. The nearest event-relevant GTFS candidate is "
            f"**{candidate}**, but it is not an assigned route, direction, terminal, or operating plan."
        )
        st.markdown(
            f"**Base cost:** {event_departures:,.0f} added departures "
            f"({departures_per_hour:,.0f}/hour × {arrival_hours:g} hours) × "
            f"{base_cost_per_departure:,.0f} USD/departure = "
            f"**{float(priority.comparison_cost_base):,.0f} USD per match**."
        )
        st.markdown(
            f"**Capacity screen:** {departures_per_hour:,.0f} departures/hour × "
            f"{base_capacity:,.0f} passengers/departure × {usable_load:.0%} usable load = "
            f"**{peak_capacity:,.0f} passengers/hour**. The displayed "
            f"{float(priority.cost_per_passenger):,.2f} USD ratio divides the per-match operating screen by that peak-hour capacity; it is not an observed cost per rider."
        )
        st.caption(
            "The 140-passenger factor is a cross-mode planning assumption, not the capacity of the candidate route. Do not interpret the 630-passenger result as a route-specific claim."
        )
        source_label = f"[{source_name}]({source_url})" if source_url else str(source_name)
        st.caption(
            f"Source basis: {source_label}. {cost_factor.get('basis') or ''} "
            "This national order-of-magnitude screen excludes agency-specific overtime, deadhead, dispatch, security, station and curb operations, and fleet acquisition. Replace it with a local operating plan and quote before funding."
        )


def _scenario_scope(package: Mapping[str, Any]) -> str:
    """Translate a model composite into plain-language quantities."""

    fields = (
        ("shuttle_buses_per_hour", "shuttle buses/hour"),
        ("added_transit_departures_per_hour", "added transit departures/hour"),
        ("park_ride_spaces", "park-and-ride spaces"),
        ("park_ride_feeder_departures_per_hour", "feeder departures/hour"),
        ("bike_hub_spaces", "bike and micromobility spaces"),
        ("cooled_walkway_km", "km cooled walking corridor"),
        ("arrival_spreading_pct", "peak arrivals shifted"),
    )
    parts = []
    for field, label in fields:
        value = package.get(field)
        if value is not None and float(value) > 0:
            prefix = f"{float(value):g}%" if field == "arrival_spreading_pct" else f"{float(value):g}"
            parts.append(f"{prefix} {label}")
    return "; ".join(parts) if parts else "No intervention (baseline)"


def _metric_row(items: list[tuple[str, str, str, str, str]]) -> None:
    for start in range(0, len(items), 4):
        group = items[start : start + 4]
        for column, item in zip(st.columns(len(group)), group):
            value, label, status, note, accent = item
            with column:
                st.markdown(metric_card(value, label, status, note=note, accent=accent), unsafe_allow_html=True)


def _priority_city(comparison: pd.DataFrame, selected_city: str | None) -> str:
    if selected_city and selected_city in set(comparison["city"]):
        return selected_city
    qualified = comparison.dropna(subset=["capacity_qualified_gap_pph"])
    if not qualified.empty:
        return str(qualified.sort_values("capacity_qualified_gap_pph", ascending=False).iloc[0]["city"])
    return str(comparison.sort_values("peak_demand_pph", ascending=False, na_position="last").iloc[0]["city"])


def _portfolio_chart(timeline: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=timeline["event_date"],
            y=timeline["gap_resolved_passengers"],
            mode="lines+markers",
            name="Cumulative peak passengers addressed",
            line=dict(color=COLORS["teal"], width=3),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=timeline["event_date"],
            y=timeline["net_co2e_kg"],
            mode="lines+markers",
            name="Cumulative net CO2e avoided (kg)",
            line=dict(color=COLORS["blue"], width=2.5),
            yaxis="y2",
        )
    )
    figure.update_layout(
        yaxis=dict(title="Passengers addressed"),
        yaxis2=dict(title="Net CO2e avoided (kg)", overlaying="y", side="right", showgrid=False),
    )
    return style_figure(figure, 390)


def _readiness_components(metric: Mapping[str, Any]) -> tuple[go.Figure, pd.DataFrame]:
    rows = pd.DataFrame(
        [
            {
                "Component": label,
                "Score": metric.get(f"{key}_score"),
                "Evidence": metric.get(f"{key}_status", "unavailable"),
            }
            for key, label in (
                ("transit", "Transit service"),
                ("access", "Venue support"),
                ("heat", "Heat safety"),
                ("uhi", "Urban heat safety"),
            )
        ]
    )
    rows["Score"] = pd.to_numeric(rows["Score"], errors="coerce")
    chart = rows.dropna(subset=["Score"]).sort_values("Score")
    figure = go.Figure(
        go.Bar(
            x=chart["Score"],
            y=chart["Component"],
            orientation="h",
            marker_color=[STATUS_COLORS.get(str(status), COLORS["slate"]) for status in chart["Evidence"]],
            text=chart["Score"],
            texttemplate="%{text:.1f}",
            textposition="outside",
            customdata=chart[["Evidence"]],
            hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<br>Evidence: %{customdata[0]}<extra></extra>",
        )
    )
    figure.update_xaxes(range=[0, 100], title="Component score (0–100)")
    return style_figure(figure, 300, legend=False), rows


def _current_strategies_summary(city: str, venue: Mapping[str, Any], artifacts: dict[str, Any]) -> None:
    """Show what real transit service already exists for a host, sourced to the transit agency.

    Independent of anything this app recommends further down the page. The map
    reuses the same real GTFS stop/route evidence layers as the venue-access
    map further down the page - it illustrates where that service actually
    runs, not the strategy_benchmarks text itself, which has no coordinates.
    """

    section_header("Current strategies")
    col_text, col_map = st.columns([1.3, 1])

    with col_text:
        benchmark = artifacts.get("strategy_benchmarks", {}).get(city, {})
        if benchmark:
            st.markdown(f"**{benchmark.get('strategy_family', 'Strategy not labeled')}**")
            signals = benchmark.get("official_service_signals", []) or []
            for signal in signals or ["No specific service signals published"]:
                st.markdown(f"- {signal}")
            source_title = benchmark.get("source_title")
            source_url = benchmark.get("source_url")
            source_text = (
                f"[{source_title}]({source_url})" if source_title and source_url else "Source not available"
            )
            st.caption(
                f"{benchmark.get('publisher', 'Publisher not available')} · {source_text} · "
                f"Evidence level: {benchmark.get('evidence_level', 'Not available')}"
            )
        else:
            st.caption(f"No published transit-service benchmark found for {city}.")

    with col_map:
        layers = dict(artifacts.get("map_layers", {}).get(city, {}))
        # Keep the 15/30-minute walking isochrones (real evidence of walkable
        # range) but drop the "Network path to event-relevant stop" line -
        # that's about one specific walking route, not this map's subject.
        layers["walk"] = [
            row for row in layers.get("walk", []) if isinstance(row, Mapping) and "minutes" in row
        ]
        agencies = artifacts.get("gtfs", {}).get(city, {}).get("agencies", [])
        agency_label = " & ".join(agencies) if agencies else "Transit"
        st.plotly_chart(
            access_overlap_map(
                venue,
                layers,
                route_label=f"{agency_label} routes",
                stop_label=f"{agency_label} stops",
            ),
            width="stretch",
            config={"displayModeBar": False},
            key=f"current_strategies_map_{city}",
        )
        st.caption(f"Real {agency_label} routes and stops, and modeled 15/30-minute walking isochrones.")


def render_decision_brief(
    metrics: pd.DataFrame,
    artifacts: dict[str, Any],
    *,
    selected_city: str | None,
    weights: Mapping[str, float],
) -> None:
    presentation = build_presentation(metrics, artifacts)
    comparison = build_city_comparison(
        metrics,
        artifacts.get("access_gaps", []),
        artifacts.get("investment_recommendations", []),
        weights=weights,
    )
    city = _priority_city(comparison, selected_city)
    row = comparison[comparison["city"] == city].iloc[0]
    decision = presentation.city(city)
    match_id = row.get("representative_match_id")
    match = decision.match(str(match_id)) if match_id else decision.match()
    access = decision.access(match.match_id)
    scenarios = decision.scenario_set(match.match_id)
    recommendations = decision.recommendation_set(match.match_id)
    qualified_options = [item for item in recommendations if item.evidence_qualified]
    exploratory_options = [item for item in recommendations if not item.evidence_qualified]
    screening_options = qualified_options or exploratory_options

    page_header(
        "City action plan",
        city,
        f"Representative match {match.match_id} at {match.venue}.",
        (
            match.stage,
            _format_kickoff(match.kickoff_local),
            f"Readiness rank {row.get('strict_rank', '—')} of 11",
        ),
    )
    _current_strategies_summary(
        city,
        {"name": match.venue, "lat": HOST_CITIES.get(city, {}).get("lat"), "lon": HOST_CITIES.get(city, {}).get("lon")},
        artifacts,
    )
    section_header("Readiness Scores")
    readiness_figure, _ = _readiness_components(decision.metric)
    st.plotly_chart(readiness_figure, width="stretch", config={"displayModeBar": False})

    section_header(
        "Access challenge", "Peak-hour demand and scheduled transit capacity for the representative match.", "Problem"
    )
    _metric_row(
        [
            (
                _number(access.peak_demand_per_hour, " / hr"),
                "Peak movement demand",
                "scenario",
                "Base attendance scenario; the representative peak may be a post-match departure",
                "blue",
            ),
            (
                _number(access.residual_passengers if access.capacity_qualified else None, " / hr"),
                "Unserved peak demand",
                access.transit_status,
                "After scheduled transit capacity",
                "coral",
            ),
            (
                _number(access.transit_capacity_base if access.capacity_qualified else None, " / hr"),
                "Scheduled transit capacity",
                access.transit_status,
                "Event-window service",
                "amber",
            ),
        ]
    )
    if not access.capacity_qualified:
        callout(
            "warning",
            "This case is not capacity-qualified",
            "Demand remains visible, but missing or partial event transit evidence prevents a strict residual-gap claim.",
        )
    elif float(access.transit_capacity_high or 0) == 0:
        callout(
            "warning",
            "No nearby event-window departures",
            "The pinned schedule contains no departures within the half-mile venue catchment.",
        )
    elif access.walking_status == "unavailable":
        callout(
            "warning",
            "Transit gap qualified; walking route unavailable",
            "Scheduled capacity can support a residual passenger gap, but the pedestrian connection remains a separate missing evidence component.",
        )

    traffic_plan = next(
        (
            item
            for item in artifacts.get("traffic_strategy_plans", [])
            if str(item.get("city")) == city and str(item.get("match_id")) == match.match_id
        ),
        None,
    )
    section_header(
        "Match-day traffic strategy",
        "Turn the access gap into a time-phased operating pattern, a scale screen, and explicit local validation needs.",
        "Operations",
    )
    if traffic_plan:
        venue_context = HOST_CITIES.get(city, {})
        render_traffic_plan(
            traffic_plan,
            {
                "name": match.venue,
                "lat": venue_context.get("lat"),
                "lon": venue_context.get("lon"),
            },
            hub_candidates=artifacts.get("gtfs", {}).get(city, {}).get("regional_hubs", []),
        )
    else:
        callout(
            "warning",
            "Traffic strategy unavailable",
            "Movement, access, regional-hub, and intervention evidence must reconcile before a match-day strategy can be screened.",
        )

    section_header(
        "Concrete investment screen",
        "Start with one defined measure for this representative match, then compare why another objective could change the choice.",
        "Decision",
    )
    if screening_options:
        priority = min(
            qualified_options,
            key=lambda item: (
                item.cost_per_passenger if item.cost_per_passenger is not None else float("inf"),
                item.intervention,
            ),
            default=None,
        )
        if priority is not None:
            with st.container(border=True):
                st.caption("Priority screen for local validation")
                st.markdown(f"### {priority.intervention}")
                st.write(priority.scope)
                _metric_row(
                    [
                        (
                            _money_exact(priority.comparison_cost_base),
                            "Per-match screening cost",
                            priority.status,
                            priority.cost_basis,
                            "amber",
                        ),
                        (
                            _number(priority.gap_resolved_passengers, " passengers"),
                            "Peak demand addressed",
                            priority.status,
                            "Representative match",
                            "teal",
                        ),
                        (
                            _money_exact(priority.cost_per_passenger, 2),
                            "Screening cost ratio",
                            priority.status,
                            "Per peak-hour capacity addressed; not observed cost/rider",
                            "blue",
                        ),
                        (priority.lead_time_band, "Lead time", priority.status, "Planning range", "slate"),
                    ]
                )
                st.markdown(f"**Delivery owner:** {priority.responsible_actor}")
                st.markdown(f"**Dependencies:** {', '.join(priority.dependencies) or 'Local implementation plan'}")
                st.caption(
                    "Why it leads: lowest modeled comparison cost per peak passenger among evidence-qualified options. "
                    "Validate fleet, labor, operations, uptake, and local pricing before procurement."
                )
        elif exploratory_options:
            callout(
                "warning",
                "Do not select an investment yet",
                "Only exploratory measures remain. Close the stated local evidence gaps before advancing funding.",
            )

        frequency_option = next(
            (option for option in recommendations if option.intervention == "Added transit frequency"),
            None,
        )
        # Every host currently lacks a transit-agency route assignment for this
        # measure (it's a structural evidence gap, not city-specific insight),
        # so it's surfaced once in the table's "Scope and location" column
        # below rather than as a repeated per-city warning callout.

        lens_table = pd.DataFrame(
            [
                {
                    "Decision": (
                        "Screen first"
                        if priority is option
                        else "Compare"
                        if option.evidence_qualified
                        else "Hold - evidence gap"
                    ),
                    "Investment": option.intervention,
                    "Scope and location": (
                        f"{option.scope}. Nearest GTFS candidate: "
                        f"{_added_frequency_candidate(artifacts, city)}; not assigned."
                        if option.intervention == "Added transit frequency"
                        else option.scope
                    ),
                    "Peak passengers": option.gap_resolved_passengers,
                    "Per-match screening cost": option.comparison_cost_base,
                    "Screening cost ratio": option.cost_per_passenger,
                    "Lead time": option.lead_time_band,
                    "Evidence": option.evidence_quality,
                }
                for option in recommendations
            ]
        )
        st.dataframe(
            lens_table,
            hide_index=True,
            width="stretch",
            column_config={
                "Peak passengers": st.column_config.NumberColumn(format="%.0f"),
                "Per-match screening cost": st.column_config.NumberColumn(format="$%,.0f"),
                "Screening cost ratio": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
        st.caption(
            f"{len(qualified_options)} qualified and {len(exploratory_options)} exploratory options. "
            "Local bids, fleet constraints, rights-of-way, and observed uptake should replace the shared national screening assumptions before funding."
        )
        if frequency_option is not None:
            _render_added_frequency_cost_basis(
                frequency_option,
                artifacts,
                city=city,
                match_id=match.match_id,
            )
    else:
        callout(
            "warning",
            "No match-specific action",
            "Movement, transit, factors, and intervention evidence must be complete before screening an option.",
        )

    show_composites = st.toggle(
        "Show advanced composite model tests",
        value=False,
        help="Operational and capital composites combine multiple measures for sensitivity testing; they are not funding recommendations.",
        key="brief_show_composites",
    )
    if not show_composites:
        return

    section_header(
        "Composite scenario sensitivity",
        "These fixed multi-measure bundles stress-test the model. They are not locally engineered plans or investment recommendations.",
        "Advanced",
    )
    st.markdown("#### Exact composite definitions")
    scenario_rows = pd.DataFrame(
        [
            {
                "Composite": item.name,
                "What it combines": _scenario_scope(item.package),
                "Gap resolved": item.gap_resolved_passengers,
                "Cost": item.cost_base,
                "Net CO2e avoided": item.net_co2e_kg_base,
                "Lead time": item.lead_time_band,
                "Evidence": item.status,
            }
            for item in scenarios
        ]
    )
    chart = scenario_rows.dropna(subset=["Gap resolved", "Cost"]).copy()
    if not chart.empty:
        chart["Climate magnitude"] = chart["Net CO2e avoided"].abs().fillna(0) + 1
        figure = px.scatter(
            chart,
            x="Cost",
            y="Gap resolved",
            color="Composite",
            size="Climate magnitude",
            text="Composite",
            color_discrete_map={
                "Baseline": COLORS["slate"],
                "Operational Package": COLORS["teal"],
                "Capital Package": COLORS["blue"],
            },
        )
        figure.update_traces(textposition="top center")
        figure.update_xaxes(tickprefix="$", title="Planning cost")
        st.plotly_chart(style_figure(figure, 390), width="stretch", config={"displayModeBar": False})
    with st.expander("Exact composite outcome table"):
        st.dataframe(scenario_rows, hide_index=True, width="stretch")

    st.markdown("#### Tournament sensitivity")
    scope_labels = {
        "match": "Selected match",
        "city_tournament": f"{city} tournament",
        "us_tournament": "All U.S. matches",
    }
    scope_label = (
        st.segmented_control(
            "Time horizon",
            list(scope_labels.values()),
            default="Selected match",
            key="brief_scope",
        )
        or "Selected match"
    )
    scope = next(key for key, label in scope_labels.items() if label == scope_label)
    package_name = st.selectbox("Composite scenario", [item.name for item in scenarios], index=1, key="brief_package")
    include_partial_portfolio = st.checkbox(
        "Include partial or unavailable access evidence in screening totals",
        value=False,
        help="Default totals include only capacity-qualified access results. Opt-in totals remain scenario screens and retain the access status for every match.",
        key="brief_include_partial",
    )
    factors = factor_registry_from_snapshot(artifacts["factor_snapshot"])
    timeline = build_portfolio_timeline(
        artifacts.get("match_events", []),
        artifacts.get("intervention_outcomes", []),
        artifacts.get("city_intervention_inputs", []),
        factors,
        package_name=package_name,
        scope=scope,
        city=city,
        match_id=match.match_id,
        access_rows=artifacts.get("access_gaps", []),
        include_partial=include_partial_portfolio,
    )
    summary = portfolio_summary(timeline)
    _metric_row(
        [
            (
                str(summary.get("match_count", 0)),
                "Matches included",
                "scenario" if not timeline.empty else "unavailable",
                f"{summary.get('omitted_matches', 0)} omitted for evidence",
                "slate",
            ),
            (
                _number(summary.get("gap_resolved_passengers"), " passengers"),
                "Cumulative peak gaps addressed",
                "scenario",
                "Sum of match-level peak benefits",
                "teal",
            ),
            (
                _number(summary.get("net_co2e_kg"), " kg"),
                "Cumulative net CO2e avoided",
                "scenario",
                "May be negative for poor service",
                "blue",
            ),
            (
                _money(summary.get("total_cost_base")),
                "Cumulative planning cost",
                "scenario",
                "Capital + recurring operations",
                "amber",
            ),
        ]
    )
    if not timeline.empty:
        st.plotly_chart(_portfolio_chart(timeline), width="stretch", config={"displayModeBar": False})
        with st.expander("Accessible table: cumulative outcome ledger"):
            st.dataframe(timeline, hide_index=True, width="stretch")
