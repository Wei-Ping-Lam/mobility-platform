"""Portfolio-first landing page for all FIFA 2026 U.S. host cities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from dashboard.domain.overview import build_portfolio_overview
from dashboard.ui.theme import metric_card, page_header, section_header
from dashboard.viz.portfolio import (
    portfolio_access_chart,
    portfolio_climate_chart,
    portfolio_traffic_chart,
    readiness_components_chart,
    readiness_ranking_chart,
)


def _number(value: Any, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.{decimals}f}{suffix}"


def _metric_grid(items: list[tuple[str, str, str, str, str]]) -> None:
    for start in range(0, len(items), 2):
        for column, item in zip(st.columns(2), items[start : start + 2]):
            value, label, status, note, accent = item
            with column:
                st.markdown(metric_card(value, label, status, note=note, accent=accent), unsafe_allow_html=True)


def _navigate(workspace: str, city: str | None = None) -> None:
    st.session_state["workspace"] = workspace
    if city:
        st.session_state["city_focus"] = city
        st.session_state["selected_city_context"] = city


def _with_access_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    demand = pd.to_numeric(result.get("peak_demand_pph"), errors="coerce")
    gap = pd.to_numeric(result.get("capacity_qualified_gap_pph"), errors="coerce").clip(lower=0)
    result["scheduled_transit_capacity_pph"] = (demand - gap).clip(lower=0)
    result["scheduled_coverage_pct"] = np.where(
        demand > 0,
        result["scheduled_transit_capacity_pph"] / demand * 100,
        np.nan,
    )
    return result


def _readiness_table(frame: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    components = metrics[
        ["city", "transit_score", "heat_score", "uhi_score", "access_score"]
    ].copy()
    display = frame[["city", "strict_rank", "strict_score"]].merge(components, on="city", how="left")
    display = display.sort_values(["strict_rank", "city"], na_position="last")
    display.columns = [
        "City",
        "Readiness rank",
        "Combined readiness",
        "Transit proximity",
        "Heat safety",
        "Urban heat safety",
        "Venue support",
    ]
    return display


def _access_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["capacity_qualified_gap_pph", "city"], ascending=[False, True]).copy()
    display = display[
        [
            "city",
            "representative_match_id",
            "peak_demand_pph",
            "scheduled_transit_capacity_pph",
            "scheduled_coverage_pct",
            "capacity_qualified_gap_pph",
        ]
    ]
    display.columns = [
        "City",
        "Representative match",
        "Peak arrivals / hour",
        "Scheduled transit capacity / hour",
        "Scheduled coverage",
        "Remaining peak gap / hour",
    ]
    display["Scheduled coverage"] = display["Scheduled coverage"].map(
        lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available"
    )
    return display


def _traffic_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["baseline_vehicle_trips_base", "city"], ascending=[False, True]).copy()
    display = display[
        [
            "city",
            "representative_match_id",
            "baseline_vehicle_trips_low",
            "baseline_vehicle_trips_base",
            "baseline_vehicle_trips_high",
        ]
    ]
    display.columns = [
        "City",
        "Representative match",
        "Low input case",
        "Base input case",
        "High input case",
    ]
    return display


def _climate_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["top_net_co2e_kg", "city"], ascending=[False, True]).copy()
    display = display[
        [
            "city",
            "representative_match_id",
            "lowest_cost_intervention",
            "top_scope",
            "top_net_co2e_kg",
            "top_evidence_quality",
        ]
    ]
    display.columns = [
        "City",
        "Representative match",
        "Qualified single measure",
        "Proposed scale",
        "Net CO2e avoided (kg)",
        "Evidence quality",
    ]
    return display


def render_home(metrics: pd.DataFrame, artifacts: Mapping[str, Any], weights: Mapping[str, float]) -> None:
    """Render an all-city funnel from readiness orientation to task evidence."""

    page_header(
        "Transportation & access",
        "FIFA 2026 Host City Mobility Readiness",
        "Start with the overall readiness order, understand which criteria drive it, then move into narrower access, traffic, and climate questions.",
        ("11 U.S. host cities", "Rank → drivers → task evidence", "No city filter"),
    )
    frame = _with_access_metrics(
        build_portfolio_overview(
            metrics,
            artifacts.get("access_gaps", []),
            artifacts.get("investment_recommendations", []),
            artifacts.get("intervention_outcomes", []),
            weights=weights,
        )
    )
    ranked = frame.dropna(subset=["strict_rank", "strict_score"]).sort_values("strict_rank")
    highest = ranked.iloc[0] if not ranked.empty else None
    readiness_order = frame.dropna(subset=["strict_score"]).sort_values(["strict_score", "city"])["city"].tolist()

    section_header(
        "How do hosts rank on overall readiness?",
        "This is the high-level orientation across all 11 hosts. It combines four normalized criteria under the current sidebar weights; it is not an investment recommendation.",
        "1 · Readiness rank",
    )
    st.plotly_chart(
        readiness_ranking_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="overview_readiness_rank",
    )
    st.caption(
        f"{highest['city']} ranks first at {_number(highest['strict_score'], decimals=1)} under the current weights. "
        "Use the next figure to see why; do not interpret rank as the size of an access gap or expected return on investment."
        if highest is not None
        else "No city has enough eligible evidence for the current readiness ranking."
    )

    st.markdown("#### What drives the rank?")
    st.caption(
        "The grid decomposes the combined score. Darker cells mean a higher normalized criterion score, allowing a reader to distinguish transit proximity from heat and venue-support evidence."
    )
    st.plotly_chart(
        readiness_components_chart(metrics, readiness_order),
        width="stretch",
        config={"displayModeBar": False},
        key="overview_readiness_components",
    )

    with st.container(border=True):
        definitions = [
            ("Transit proximity", "Relative GTFS stops and routes near the venue. It does not measure event-hour capacity."),
            ("Heat safety", "Inverse of the June–July 90th-percentile heat index. Higher means less heat exposure."),
            ("Urban heat safety", "Inverse of the venue-area urban heat-island anomaly. Higher means less local heat amplification."),
            ("Venue support", "Nearby support destinations relative to other hosts. It is not a walking-safety or accessibility audit."),
        ]
        for start in range(0, len(definitions), 2):
            for column, (label, definition) in zip(st.columns(2), definitions[start : start + 2]):
                with column:
                    st.markdown(f"**{label}**")
                    st.caption(definition)
        weight_text = " · ".join(
            f"{label} {float(weights.get(key, 0)):.0%}"
            for label, key in (
                ("Transit", "transit"),
                ("Heat", "heat"),
                ("Urban heat", "uhi"),
                ("Venue support", "access"),
            )
        )
        st.caption(f"Current weight profile: {weight_text}. Scores are normalized 0–100 across these hosts.")

    with st.expander("Exact readiness scores", icon=":material/table_chart:"):
        st.dataframe(_readiness_table(frame, metrics), hide_index=True, width="stretch", height=455)

    largest_gap = frame.dropna(subset=["capacity_qualified_gap_pph"]).sort_values(
        "capacity_qualified_gap_pph", ascending=False
    )
    largest_gap_row = largest_gap.iloc[0] if not largest_gap.empty else None
    coverage = pd.to_numeric(frame["scheduled_coverage_pct"], errors="coerce").dropna()
    zero_capacity = int((pd.to_numeric(frame["scheduled_transit_capacity_pph"], errors="coerce").fillna(0) <= 0).sum())
    traffic = frame.dropna(subset=["baseline_vehicle_trips_base"]).sort_values(
        "baseline_vehicle_trips_base", ascending=False
    )
    highest_traffic = traffic.iloc[0] if not traffic.empty else None
    traffic_values = pd.to_numeric(frame["baseline_vehicle_trips_base"], errors="coerce").dropna()
    climate = frame.dropna(subset=["top_net_co2e_kg"]).sort_values("top_net_co2e_kg", ascending=False)
    highest_climate = climate.iloc[0] if not climate.empty else None
    climate_values = pd.to_numeric(frame["top_net_co2e_kg"], errors="coerce").dropna()

    section_header(
        "What does each transportation task show?",
        "Now narrow from the readiness screen to one task-specific question at a time. Each tab uses a different unit and answers a different decision question.",
        "2 · Task-specific evidence",
    )
    access_tab, traffic_tab, climate_tab = st.tabs(
        [
            ":material/train: Access shortfall",
            ":material/traffic: Traffic pressure",
            ":material/eco: Climate outcome",
        ]
    )
    with access_tab:
        st.markdown("#### Can scheduled transit cover the representative peak hour?")
        _metric_grid(
            [
                (
                    _number(largest_gap_row["capacity_qualified_gap_pph"], " pph")
                    if largest_gap_row is not None else "Not available",
                    f"Largest gap — {largest_gap_row['city']}" if largest_gap_row is not None else "Largest remaining peak gap",
                    "scenario",
                    "Scheduled transit shortfall in its representative peak hour",
                    "coral",
                ),
                (
                    f"{coverage.median():.1f}%" if not coverage.empty else "Not available",
                    "Median scheduled coverage",
                    "derived",
                    f"{zero_capacity} of {len(frame)} hosts have zero matched capacity in that hour",
                    "teal",
                ),
            ]
        )
        st.plotly_chart(
            portfolio_access_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="overview_access_coverage",
        )
        st.caption(
            "Scheduled coverage = event-valid scheduled passenger capacity in the matching hour ÷ modeled base peak arrivals. "
            "Each city uses its most constrained capacity-qualified match. The remaining gap is not roadway congestion, "
            "observed ridership, or a citywide daily total."
        )
        with st.expander("Exact access values", icon=":material/table_chart:"):
            st.dataframe(_access_table(frame), hide_index=True, width="stretch", height=455)

    with traffic_tab:
        st.markdown("#### How many venue-area vehicle trips does the base case imply?")
        _metric_grid(
            [
                (
                    _number(highest_traffic["baseline_vehicle_trips_base"], " trips")
                    if highest_traffic is not None else "Not available",
                    f"Highest base pressure — {highest_traffic['city']}" if highest_traffic is not None else "Highest base traffic pressure",
                    "scenario",
                    "Modeled private vehicle trips for the representative match",
                    "blue",
                ),
                (
                    _number(traffic_values.median(), " trips") if not traffic_values.empty else "Not available",
                    "Median base traffic pressure",
                    "scenario",
                    "Across the 11 representative match scenarios",
                    "blue",
                ),
            ]
        )
        st.plotly_chart(
            portfolio_traffic_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="overview_baseline_traffic",
        )
        st.caption(
            "Baseline vehicle trips = modeled attendance × assumed private-vehicle share ÷ 2.2 occupants per vehicle. "
            "Whiskers span the named low and high input cases. This is venue-area trip pressure, not measured roadway congestion, delay, or queue length."
        )
        with st.expander("Exact traffic values", icon=":material/table_chart:"):
            st.dataframe(_traffic_table(frame), hide_index=True, width="stretch", height=455)

    with climate_tab:
        st.markdown("#### What net CO2e benefit does the common qualified measure imply?")
        _metric_grid(
            [
                (
                    _number(highest_climate["top_net_co2e_kg"], " kg")
                    if highest_climate is not None else "Not available",
                    f"Largest modeled benefit — {highest_climate['city']}" if highest_climate is not None else "Largest modeled climate benefit",
                    "scenario",
                    "Base-case net CO2e avoided by the qualified single measure",
                    "teal",
                ),
                (
                    _number(climate_values.median(), " kg") if not climate_values.empty else "Not available",
                    "Median modeled climate benefit",
                    "scenario",
                    "Across the 11 representative match screens",
                    "teal",
                ),
            ]
        )
        st.plotly_chart(
            portfolio_climate_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="overview_single_measure_climate",
        )
        st.caption(
            "Every city's lowest-cost qualified screen is the same proposed scale: add 6 transit departures per hour in the event window. "
            "Net CO2e avoided subtracts added transit-service emissions from displaced private-vehicle emissions; positive values mean modeled avoidance. "
            "The result varies with modeled private trip distance. It is a base-case scenario—not an observed reduction, certified inventory, or package forecast."
        )
        with st.expander("Exact climate values", icon=":material/table_chart:"):
            st.dataframe(_climate_table(frame), hide_index=True, width="stretch", height=455)

    priority_city = str(largest_gap_row["city"]) if largest_gap_row is not None else None
    section_header(
        "Open the priority case",
        "Continue with the largest documented representative peak gap. The action plan shows concrete investment screens, scope, cost, owner, dependencies, and evidence limits.",
        "3 · Drill down",
    )
    st.button(
        f"Open {priority_city} action plan" if priority_city else "Open priority city action plan",
        key="overview_open_city",
        on_click=_navigate,
        args=("City Brief", priority_city),
        disabled=priority_city is None,
        width="stretch",
    )
    st.button(
        "Review methods, assumptions, and sources",
        on_click=_navigate,
        args=("Methods & QA",),
        key="overview_open_methods",
        width="stretch",
    )
    st.download_button(
        "Download exact overview comparison CSV",
        frame[[column for column in frame.columns if not column.startswith("package_")]].to_csv(index=False),
        file_name="host-city-mobility-overview.csv",
        mime="text/csv",
        width="stretch",
    )
