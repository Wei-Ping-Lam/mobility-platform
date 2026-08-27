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
from dashboard.ui.portfolio.context import build_city_hourly_movement, build_portfolio_frame
from dashboard.ui.theme import page_header

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
    )
    frame = build_portfolio_frame(metrics, artifacts, weights)
    hourly_movement = build_city_hourly_movement(artifacts)

    tabs = st.tabs(
        list(TAB_LABELS),
        key="track1_objective",
        on_change="rerun",
    )
    renderers = (
        lambda: resilience.render(frame, metrics),
        lambda: visitor_movement.render(frame, hourly_movement),
        lambda: first_last_mile.render(frame),
        lambda: investments.render(frame, metrics, artifacts),
    )
    for tab, renderer in zip(tabs, renderers):
        if tab.open:
            with tab:
                renderer()
