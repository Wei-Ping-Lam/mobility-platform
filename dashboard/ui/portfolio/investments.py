"""Investments and strategies objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.ui.portfolio.tables import actions_table
from dashboard.viz.portfolio import portfolio_actions_chart


def render(frame: pd.DataFrame) -> None:
    actions = frame.dropna(subset=["top_gap_resolved"]).sort_values(
        "top_gap_resolved", ascending=False
    )
    highest_action = actions.iloc[0] if not actions.empty else None
    distinct_actions = int(frame["top_intervention"].dropna().nunique())
    qualified_action_cities = int(frame["top_option_qualified"].fillna(False).sum())

    st.markdown("#### What concrete measure should each host validate first?")
    metric_grid(
        [
            (
                f"{distinct_actions} measure types",
                "Bottleneck-matched priority screens",
                "scenario",
                "Zero service, long approaches, heat, and existing route capacity trigger different screens",
                "teal",
            ),
            (
                f"{qualified_action_cities} of {len(frame)}",
                "Cities with a qualified priority screen",
                "scenario",
                number(highest_action["top_gap_resolved"], " / hr")
                + " is the largest modeled single-measure benefit"
                if highest_action is not None
                else "No qualified benefit available",
                "blue",
            ),
        ]
    )
    st.plotly_chart(
        portfolio_actions_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_priority_actions",
    )
    st.caption(
        "The priority is a transparent bottleneck-matched screening measure, not an automatic winner or agency commitment. "
        "Operational/capital is retained as delivery and cost metadata on each measure; composite packages remain only in the deferred advanced explorer."
    )
    with st.expander(
        "Exact investment and strategy values", icon=":material/table_chart:"
    ):
        st.dataframe(
            actions_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
