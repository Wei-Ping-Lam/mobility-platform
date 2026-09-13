"""Thin composition root for the all-city Portfolio page."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio import (
    first_last_mile,
    resilience,
    visitor_movement,
)
from dashboard.ui.portfolio.context import build_city_hourly_movement, build_portfolio_frame
from dashboard.ui.theme import page_header

TAB_LABELS = (
    ":material/health_and_safety: Overview",
    ":material/route: Visitor movement",
    ":material/transfer_within_a_station: Venue access",
)

_PORTFOLIO_FRAME_CACHE_KEY = "_portfolio_frame_cache"


def _cached_portfolio_frame(
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    weights: Mapping[str, float],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cache the all-city frame + hourly movement table across reruns.

    Streamlit reruns this whole script on every tab click or slider drag
    anywhere in the Portfolio workspace; only metrics (already cached in
    app.py on weights/include_estimates) changes what these two builders
    return, so cache on that object's identity instead of rebuilding both on
    every unrelated rerun.
    """

    cache_key = id(metrics)
    cached = st.session_state.get(_PORTFOLIO_FRAME_CACHE_KEY)
    if cached is not None and cached[0] == cache_key:
        return cached[1], cached[2]
    frame = build_portfolio_frame(metrics, artifacts, weights)
    hourly_movement = build_city_hourly_movement(artifacts)
    st.session_state[_PORTFOLIO_FRAME_CACHE_KEY] = (cache_key, frame, hourly_movement)
    return frame, hourly_movement


def render_portfolio(
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    weights: Mapping[str, float],
) -> None:
    page_header(
        "Transportation & access",
        "FIFA 2026 Host City Mobility Readiness",
        "Compare readiness, model visitor movement, and view access gaps across every U.S. host.",
    )
    frame, hourly_movement = _cached_portfolio_frame(metrics, artifacts, weights)

    tabs = st.tabs(
        list(TAB_LABELS),
        key="track1_objective",
        on_change="rerun",
    )
    renderers = (
        lambda: resilience.render(frame, metrics),
        lambda: visitor_movement.render(frame, hourly_movement),
        lambda: first_last_mile.render(frame),
    )
    for tab, renderer in zip(tabs, renderers):
        if tab.open:
            with tab:
                renderer()
