"""Thin composition root for the all-city Portfolio page."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio import (
    first_last_mile,
    investments,
    resilience,
    visitor_movement,
)
from dashboard.ui.portfolio.context import build_portfolio_frame
from dashboard.ui.portfolio.shared import navigate
from dashboard.ui.theme import page_header, section_header

TAB_LABELS = (
    ":material/health_and_safety: Overview",
    ":material/route: Visitor movement",
    ":material/transfer_within_a_station: First/last mile",
    ":material/construction: Investments & transit",
)


def render_portfolio(
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    weights: Mapping[str, float],
) -> None:
    page_header(
        "Transportation & access",
        "FIFA 2026 Host City Mobility Readiness",
        "Compare readiness, modeled visitor movement, first/last-mile gaps, and investment choices across every U.S. host.",
        (
            "11 cities at once",
            "4 portfolio comparisons",
            "No portfolio map or city filter",
        ),
    )
    frame = build_portfolio_frame(metrics, artifacts, weights)

    section_header(
        "Compare the portfolio-level objectives",
        "Each tab answers one cross-city decision question. Match-day traffic operations stay in each City action plan, where they can be tied to local hubs, controls, and evidence.",
        "Track 1 scorecard",
    )
    tabs = st.tabs(
        list(TAB_LABELS),
        key="track1_objective",
        on_change="rerun",
    )
    renderers = (
        lambda: resilience.render(frame, metrics),
        lambda: visitor_movement.render(frame),
        lambda: first_last_mile.render(frame),
        lambda: investments.render(frame),
    )
    for tab, renderer in zip(tabs, renderers):
        if tab.open:
            with tab:
                renderer()

    largest_gap = frame.dropna(subset=["capacity_qualified_gap_pph"]).sort_values(
        "capacity_qualified_gap_pph", ascending=False
    )
    priority_city = str(largest_gap.iloc[0]["city"]) if not largest_gap.empty else None
    section_header(
        "Open the priority case",
        "Continue from the all-city comparison to the representative match, traffic strategy, candidate hubs, concrete scope, delivery owner, dependencies, and evidence limits.",
        "Drill down",
    )
    st.button(
        f"Open {priority_city} action plan" if priority_city else "Open priority city action plan",
        key="overview_open_city",
        on_click=navigate,
        args=("City Brief", priority_city),
        disabled=priority_city is None,
        width="stretch",
    )
    st.download_button(
        "Download exact Track 1 comparison CSV",
        frame[[column for column in frame.columns if not column.startswith("package_")]].to_csv(index=False),
        file_name="track-1-host-city-comparison.csv",
        mime="text/csv",
        width="stretch",
    )
