"""Portfolio-first landing page for all FIFA 2026 U.S. host cities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.domain.overview import PACKAGE_NAMES, build_portfolio_overview, portfolio_summary
from dashboard.ui.theme import metric_card, page_header, section_header
from dashboard.viz.portfolio import LENS_DEFINITIONS, outcome_ranking_chart, portfolio_map


def _number(value: Any, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.{decimals}f}{suffix}"


def _money(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    numeric = float(value)
    if abs(numeric) >= 1_000_000:
        return f"${numeric / 1_000_000:,.1f}M"
    if abs(numeric) >= 1_000:
        return f"${numeric / 1_000:,.0f}K"
    return f"${numeric:,.0f}"


def _median(frame: pd.DataFrame, column: str) -> float | None:
    values = pd.to_numeric(frame.get(column), errors="coerce").dropna()
    return float(values.median()) if not values.empty else None


def _metric_grid(items: list[tuple[str, str, str, str, str]]) -> None:
    for column, item in zip(st.columns(len(items)), items):
        value, label, status, note, accent = item
        with column:
            st.markdown(metric_card(value, label, status, note=note, accent=accent), unsafe_allow_html=True)


def _navigate(workspace: str, city: str | None = None) -> None:
    st.session_state["workspace"] = workspace
    if city:
        st.session_state["city_focus"] = city


def _readiness_position(rank: Any, rankable_count: int) -> str:
    if rank is None or pd.isna(rank):
        return "Not rankable"
    numeric = int(rank)
    third = max(1, (rankable_count + 2) // 3)
    if numeric <= third:
        return "Higher-readiness third"
    if numeric > rankable_count - third:
        return "Priority-improvement third"
    return "Middle third"


def _comparison_table(frame: pd.DataFrame, lens: str) -> pd.DataFrame:
    rankable_count = int(frame["strict_rank"].notna().sum())
    display_frame = frame.copy()
    display_frame["readiness_position"] = display_frame["strict_rank"].map(
        lambda rank: _readiness_position(rank, rankable_count)
    )
    definition = LENS_DEFINITIONS[lens]
    display_frame = display_frame.sort_values(
        [definition["column"], "city"],
        ascending=[not bool(definition["higher_is_better"]), True],
        na_position="last",
    )
    display = display_frame[
        [
            "strict_rank",
            "city",
            "strict_score",
            "readiness_position",
            "capacity_qualified_gap_pph",
            "package_vehicle_trips_base",
            "package_net_co2e_base",
            "package_cost_per_passenger",
            "qualified_option_count",
            "screening_confidence",
        ]
    ].copy()
    display.columns = [
        "Readiness rank",
        "City",
        "Readiness score",
        "Portfolio position",
        "Peak access gap (pph)",
        "Traffic pressure after package (vehicle trips)",
        "Net CO2e avoided (kg)",
        "Package cost/passenger addressed",
        "Qualified investment options",
        "Evidence confidence",
    ]
    return display


def render_home(metrics: pd.DataFrame, artifacts: Mapping[str, Any], weights: Mapping[str, float]) -> None:
    """Render a progressive all-city overview with optional city drill-down."""

    page_header(
        "Transportation & access",
        "FIFA 2026 Host City Mobility Readiness",
        "Compare how 11 U.S. host cities could move match-day visitors, close first/last-mile gaps, and prioritize lower-emission transportation investments.",
        ("11 U.S. host cities", "78 official matches", "Start broad, then explore a city"),
    )
    package_name = st.selectbox(
        "Scenario package",
        list(PACKAGE_NAMES),
        index=list(PACKAGE_NAMES).index("Operational Package"),
        help="Updates access, traffic-pressure, emissions, and investment outcomes. Readiness remains a current-condition score.",
        key="overview_package",
    )
    frame = build_portfolio_overview(
        metrics,
        artifacts.get("access_gaps", []),
        artifacts.get("investment_recommendations", []),
        artifacts.get("intervention_outcomes", []),
        weights=weights,
        package_name=package_name,
    )
    summary = portfolio_summary(frame, len(artifacts.get("match_events", [])))
    ranked = frame.dropna(subset=["strict_rank", "strict_score"]).sort_values("strict_rank")
    highest = ranked.iloc[0] if not ranked.empty else None
    lowest = ranked.iloc[-1] if not ranked.empty else None
    largest_gap = frame.dropna(subset=["capacity_qualified_gap_pph"]).sort_values(
        "capacity_qualified_gap_pph", ascending=False
    )
    largest_gap_row = largest_gap.iloc[0] if not largest_gap.empty else None
    _metric_grid(
        [
            (
                f"{highest['city']} · {_number(highest['strict_score'], decimals=1)}" if highest is not None else "Not available",
                "Highest readiness",
                "derived",
                "Relative MRS under selected weights",
                "teal",
            ),
            (
                f"{lowest['city']} · {_number(lowest['strict_score'], decimals=1)}" if lowest is not None else "Not available",
                "Greatest readiness challenge",
                "derived",
                "Relative MRS under selected weights",
                "blue",
            ),
            (
                f"{largest_gap_row['city']} · {_number(largest_gap_row['capacity_qualified_gap_pph'], ' pph')}" if largest_gap_row is not None else "Not available",
                "Largest peak access gap",
                "scenario",
                "Scheduled capacity, not roadway congestion",
                "coral",
            ),
            (f"{summary.cities_with_qualified_options} / {summary.city_count}", "Cities with qualified options", "scenario", "No automatic winner", "amber"),
        ]
    )
    section_header(
        "Selected package outcomes",
        "Median representative-match result across the 11 host cities.",
        package_name,
    )
    _metric_grid(
        [
            (_number(_median(frame, "package_gap_resolved"), " passengers"), "Peak gap addressed", "scenario", package_name, "teal"),
            (_number(_median(frame, "package_vehicle_trips_base"), " trips"), "Venue-area vehicle pressure", "scenario", package_name, "blue"),
            (_number(_median(frame, "package_net_co2e_base"), " kg"), "Net CO2e avoided", "scenario", package_name, "coral"),
            (_money(_median(frame, "package_cost_base")), "Planning cost", "scenario", package_name, "amber"),
        ]
    )

    section_header(
        "See which cities are most ready—and why",
        "All 11 cities are shown by default. Switch outcomes to compare readiness, access, traffic pressure, CO2, or investment efficiency without losing the national context.",
        "All-city overview",
    )
    lens = st.segmented_control(
        "Outcome to compare",
        list(LENS_DEFINITIONS),
        default="Mobility readiness",
        key="overview_map_lens",
    ) or "Mobility readiness"
    selected_cities = st.multiselect(
        "Filter cities (leave empty to show all 11)",
        sorted(frame["city"].tolist()),
        default=[],
        help="Optionally narrow the chart and table to any number of cities. An empty filter always means all cities.",
        key="overview_cities",
    )
    active = frame[frame["city"].isin(selected_cities)].copy() if selected_cities else frame.copy()
    ranking_column, map_column = st.columns([1.15, 1], gap="large")
    with ranking_column:
        st.plotly_chart(
            outcome_ranking_chart(active, lens),
            width="stretch",
            config={"displayModeBar": False},
            key=f"overview_rank_{lens}",
        )
        st.caption(str(LENS_DEFINITIONS[lens]["context"]))
    with map_column:
        st.plotly_chart(
            portfolio_map(frame, lens, selected_cities),
            width="stretch",
            config={"displayModeBar": False},
            key=f"overview_map_{lens}",
        )

    comparison_table = _comparison_table(active, lens)
    st.dataframe(comparison_table, hide_index=True, width="stretch", height=455)
    st.caption("MRS ranks current readiness; the other lenses show selected-package outcomes.")

    section_header(
        "Open a city decision brief",
        "Choose any host to understand its score components, match-level access gap, traffic-pressure proxy, CO2 range, investment choices, assumptions, and evidence.",
        "Drill down",
    )
    drill_order = ranked["city"].tolist() if not ranked.empty else sorted(frame["city"].tolist())
    drill_city = st.selectbox(
        "City to investigate",
        ["Select a city"] + drill_order,
        index=0,
        key="overview_drill_city",
    )
    st.button(
        "Open city brief",
        key="overview_open_city",
        on_click=_navigate,
        args=("City Brief", None if drill_city == "Select a city" else drill_city),
        disabled=drill_city == "Select a city",
        width="stretch",
    )

    action_compare, action_methods = st.columns(2)
    with action_compare:
        st.button(
            "Open full city comparison",
            on_click=_navigate,
            args=("Compare Cities",),
            key="overview_open_compare",
            width="stretch",
        )
    with action_methods:
        st.button(
            "Review methods, assumptions, and sources",
            on_click=_navigate,
            args=("Methods & QA",),
            key="overview_open_methods",
            width="stretch",
        )

    st.download_button(
        "Download exact overview comparison CSV",
        frame.to_csv(index=False),
        file_name="host-city-mobility-overview.csv",
        mime="text/csv",
        width="stretch",
    )
