"""Judge- and decision-maker-facing proof sequence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.comparison import build_city_comparison
from dashboard.domain.portfolio import build_portfolio_timeline, portfolio_summary
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.models.interventions import factor_registry_from_snapshot
from dashboard.ui.city.traffic_plan import render as render_traffic_plan
from dashboard.ui.presentation import build_presentation
from dashboard.ui.theme import callout, metric_card, page_header, section_header
from dashboard.viz.style import COLORS, STATUS_COLORS, style_figure


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
        f"{city}: from access gap to action",
        f"Representative match {match.match_id} at {match.venue}.",
        (
            match.stage,
            match.kickoff_local or "Kickoff unavailable",
            f"Readiness rank {row.get('strict_rank', '—')} of 11",
        ),
    )
    section_header(
        "Why readiness differs", "The readiness score combines four independently labeled components.", "Why"
    )
    readiness_figure, readiness_table = _readiness_components(decision.metric)
    st.plotly_chart(readiness_figure, width="stretch", config={"displayModeBar": False})
    with st.expander("Readiness component table"):
        st.dataframe(readiness_table, hide_index=True, width="stretch")

    section_header(
        "Access challenge", "Peak-hour demand and scheduled transit capacity for the representative match.", "Problem"
    )
    _metric_row(
        [
            (
                f"#{int(row['strict_rank'])}" if pd.notna(row.get("strict_rank")) else "Not ranked",
                "Readiness rank",
                "derived",
                "Selected weight profile",
                "teal",
            ),
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
            map_layers=artifacts.get("map_layers", {}).get(city, {}),
            published_plan=artifacts.get("published_traffic_plans", {}).get(city, {}),
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
                            _money(priority.comparison_cost_base),
                            "Comparison cost",
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
                            _money(priority.cost_per_passenger),
                            "Cost / passenger",
                            priority.status,
                            "Comparison basis",
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
                    "Proposed scale": option.scope,
                    "Peak passengers": option.gap_resolved_passengers,
                    "Comparison cost": option.comparison_cost_base,
                    "Cost / passenger": option.cost_per_passenger,
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
                "Comparison cost": st.column_config.NumberColumn(format="$%,.0f"),
                "Cost / passenger": st.column_config.NumberColumn(format="$%.2f"),
            },
        )
        st.caption(
            f"{len(qualified_options)} qualified and {len(exploratory_options)} exploratory options. "
            "Local bids, fleet constraints, rights-of-way, and observed uptake should replace the shared national screening assumptions before funding."
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
