"""Judge- and decision-maker-facing proof sequence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.comparison import build_city_comparison
from dashboard.domain.portfolio import build_portfolio_timeline, portfolio_summary
from dashboard.models.interventions import factor_registry_from_snapshot
from dashboard.ui.judging import build_criteria_evidence, build_deliverable_evidence
from dashboard.ui.presentation import build_presentation
from dashboard.ui.theme import callout, metric_card, page_header, priority_card, section_header
from dashboard.viz.style import COLORS, style_figure, style_map


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


def _coverage_map(comparison: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    for confidence in ("high", "medium", "low", "insufficient"):
        subset = comparison[comparison["screening_confidence"] == confidence].dropna(subset=["lat", "lon"])
        if subset.empty:
            continue
        color = {"high": COLORS["teal"], "medium": COLORS["blue"], "low": COLORS["amber"], "insufficient": COLORS["slate"]}[confidence]
        size_value = pd.to_numeric(subset["capacity_qualified_gap_pph"], errors="coerce").fillna(
            pd.to_numeric(subset["peak_demand_pph"], errors="coerce").fillna(0)
        )
        sizes = 13 + 17 * size_value / max(float(size_value.max()), 1)
        figure.add_trace(
            go.Scattermap(
                lat=subset["lat"],
                lon=subset["lon"],
                mode="markers",
                marker=dict(size=sizes, color=color, opacity=.88),
                name=f"{confidence.title()} confidence",
                customdata=subset[["city", "capacity_qualified_gap_pph", "top_intervention", "qualified_matches"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>Capacity-qualified gap: %{customdata[1]:,.0f} passengers/hour"
                    "<br>Portfolio option: %{customdata[2]}<br>Qualified matches: %{customdata[3]}<extra></extra>"
                ),
            )
        )
    return style_map(figure, 440, zoom=3.0, lat=38.5, lon=-96)


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
    comparison_example = min(
        qualified_options,
        key=lambda item: (
            item.cost_per_passenger
            if item.cost_per_passenger is not None
            else float("inf"),
            item.intervention,
        ),
        default=None,
    )

    page_header(
        "Decision brief",
        "From match-hour gap to an auditable investment choice",
        "A guided proof sequence for FIFA 2026 transportation access: where the pressure is, what evidence supports it, which options remain Pareto-efficient, and what outcomes are still only planning scenarios.",
        ("11 U.S. host cities", "78 official matches", "No opaque optimum"),
    )

    section_header(f"Priority case: {city}", f"Representative match {match.match_id} at {match.venue}. The city changes when a capacity-qualified gap is larger or the sidebar selection changes.", "Where and why")
    _metric_row(
        [
            (_number(access.peak_demand_per_hour, " pph"), "Peak movement demand", "scenario", "Low/base/high attendance planning range", "blue"),
            (_number(access.residual_passengers if access.capacity_qualified else None, " pph"), "Capacity-qualified access gap", access.transit_status, "Not measured roadway congestion", "coral"),
            (f"{len(qualified_options)} + {len(exploratory_options)}", "Qualified + exploratory options", "scenario" if qualified_options else "partial", "No automatic winner", "amber"),
            (_money(comparison_example.comparison_cost_base) if comparison_example else "Not available", "Lowest qualified comparison cost", comparison_example.status if comparison_example else "unavailable", "Lifecycle-equivalent; total cost remains separate", "teal"),
        ]
    )
    if not access.capacity_qualified:
        callout("warning", "This case is not capacity-qualified", "Demand remains visible, but missing or partial event transit evidence prevents a strict residual-gap claim.")
    elif float(access.transit_capacity_high or 0) == 0:
        callout(
            "warning",
            "Pinned schedule shows zero nearby event-window departures",
            "This is a qualified observed service gap within the half-mile catchment, not missing data. Any special-event shuttle absent from GTFS remains outside the evidence base.",
        )
    elif access.walking_status == "unavailable":
        callout("warning", "Transit gap qualified; walking route unavailable", "Scheduled capacity can support a residual passenger gap, but the pedestrian connection remains a separate missing evidence component.")

    map_col, action_col = st.columns([1.25, 1], gap="large")
    with map_col:
        st.plotly_chart(_coverage_map(comparison), width="stretch", config={"displayModeBar": False})
        st.caption("Marker size uses the qualified gap when available, otherwise scenario demand. Color indicates screening confidence and is repeated in the table.")
    with action_col:
        st.markdown("#### Match-specific nondominated set")
        if recommendations:
            if qualified_options:
                st.caption("Evidence-qualified screening options")
            for item in qualified_options:
                body = (
                    f"Resolves {_number(item.gap_resolved_passengers, ' peak passengers')}; "
                    f"{_money(item.cost_per_passenger)} comparison cost per passenger; "
                    f"total cost {_money(item.cost_base)}; {_number(item.net_co2e_kg, ' kg')} net CO2e; "
                    f"lead time {item.lead_time_band}. Candidate owner: {item.responsible_actor}. No automatic winner."
                )
                st.markdown(priority_card(city, item.intervention, body, item.status), unsafe_allow_html=True)
            if exploratory_options:
                with st.expander("Exploratory sensitivities requiring additional evidence", expanded=True):
                    for item in exploratory_options:
                        st.markdown(f"**{item.intervention}:** {item.evidence_reason}")
        else:
            callout("warning", "No match-specific recommendation", "Complete movement, transit, factors, and recommendation identity before presenting an investment option.")

    section_header("Package tradeoffs", "Cost, peak benefit, and climate outcome stay separate. Bubble size represents absolute net CO2e magnitude; negative values remain visible in the table.", "What outcome")
    scenario_rows = pd.DataFrame(
        [
            {
                "Scenario": item.name,
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
            color="Scenario",
            size="Climate magnitude",
            text="Scenario",
            color_discrete_map={"Baseline": COLORS["slate"], "Operational Package": COLORS["teal"], "Capital Package": COLORS["blue"]},
        )
        figure.update_traces(textposition="top center")
        figure.update_xaxes(tickprefix="$", title="Planning cost")
        st.plotly_chart(style_figure(figure, 390), width="stretch", config={"displayModeBar": False})
    with st.expander("Accessible table: package tradeoffs", expanded=True):
        st.dataframe(scenario_rows, hide_index=True, width="stretch")

    section_header("Outcomes over time", "Choose one match, the selected city's tournament, or the U.S. tournament. Infrastructure capital is counted once per city; operations recur per match.", "When")
    scope_labels = {"match": "Selected match", "city_tournament": f"{city} tournament", "us_tournament": "All U.S. matches"}
    scope = st.radio("Time horizon", list(scope_labels), format_func=scope_labels.get, horizontal=True, key="brief_scope")
    package_name = st.selectbox("Package", [item.name for item in scenarios], index=1, key="brief_package")
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
            (str(summary.get("match_count", 0)), "Matches included", "scenario" if not timeline.empty else "unavailable", f"{summary.get('omitted_matches', 0)} omitted for evidence", "slate"),
            (_number(summary.get("gap_resolved_passengers"), " passengers"), "Cumulative peak gaps addressed", "scenario", "Sum of match-level peak benefits", "teal"),
            (_number(summary.get("net_co2e_kg"), " kg"), "Cumulative net CO2e avoided", "scenario", "May be negative for poor service", "blue"),
            (_money(summary.get("total_cost_base")), "Cumulative planning cost", "scenario", "Capital + recurring operations", "amber"),
        ]
    )
    if not timeline.empty:
        st.plotly_chart(_portfolio_chart(timeline), width="stretch", config={"displayModeBar": False})
        with st.expander("Accessible table: cumulative outcome ledger"):
            st.dataframe(timeline, hide_index=True, width="stretch")

    section_header("Competition evidence", "These are proof statuses, not self-awarded points. Every partial item states what remains unproven.", "Why it matters")
    criteria = build_criteria_evidence(metrics, artifacts, comparison)
    for start in range(0, len(criteria), 3):
        group = criteria.iloc[start : start + 3]
        for column, (_, criterion) in zip(st.columns(len(group)), group.iterrows()):
            body = f"{criterion['Visible proof']} Limitation: {criterion['Current limitation']} Open: {criterion['Open in']}."
            with column:
                st.markdown(priority_card(f"{criterion['Weight']} points", criterion["Criterion"], body, criterion["Status"]), unsafe_allow_html=True)
    with st.expander("Accessible table: judging criteria evidence", expanded=True):
        st.dataframe(criteria, hide_index=True, width="stretch")

    deliverables = build_deliverable_evidence(metrics, artifacts, comparison)
    section_header("Required deliverables", "Nothing is left implicit: each requested track output has a proof location and an explicit limitation.", "Submission checklist")
    st.dataframe(deliverables, hide_index=True, width="stretch")
    st.download_button(
        "Download decision brief evidence JSON",
        json.dumps({"city_comparison": comparison.to_dict("records"), "criteria": criteria.to_dict("records"), "deliverables": deliverables.to_dict("records")}, indent=2, default=str),
        file_name="mobility-decision-brief-evidence.json",
        mime="application/json",
        width="stretch",
    )
