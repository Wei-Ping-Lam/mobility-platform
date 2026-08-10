"""Traffic-management objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid
from dashboard.ui.portfolio.tables import traffic_management_table


def render(frame: pd.DataFrame) -> None:
    """Compare generated strategy families with reviewed official benchmarks."""

    patterns = int(frame["traffic_predicted_pattern"].dropna().nunique())
    benchmarked = int(frame["traffic_benchmark_pattern"].notna().sum())
    matches = int(frame["traffic_benchmark_agreement"].eq("matches").sum())
    multi_hub = int(
        frame["traffic_single_hub_feasibility"]
        .eq("Multiple hubs or demand spreading required")
        .sum()
    )

    st.markdown("#### How should each city organize match-day movement?")
    metric_grid(
        [
            (
                f"{patterns} operating patterns",
                "City-specific strategy families",
                "scenario",
                "Selected from service, access, walking, and regional-hub evidence",
                "teal",
            ),
            (
                f"{matches} of {benchmarked} match",
                "Official-plan calibration check",
                "partial",
                "Broad family agreement; this is an in-sample benchmark, not holdout accuracy",
                "blue",
            ),
        ]
    )
    comparison = traffic_management_table(frame)
    st.dataframe(
        comparison[["City", "Engine strategy", "Agreement", "Rule strength"]],
        hide_index=True,
        width="stretch",
        height=455,
        column_config={
            "City": st.column_config.TextColumn(width="small"),
            "Engine strategy": st.column_config.TextColumn(width="medium"),
            "Agreement": st.column_config.TextColumn(width="small"),
            "Rule strength": st.column_config.TextColumn(width="small"),
        },
    )
    st.caption(
        "The engine runs without reading the official benchmark label. Agreement checks only the broad network design. "
        f"{multi_hub} cities exceed the single-hub screening threshold."
    )
    with st.expander("Official comparison and scale detail", icon=":material/table_view:"):
        st.dataframe(
            comparison,
            hide_index=True,
            width="stretch",
            height=455,
            column_config={
                "Engine strategy": st.column_config.TextColumn(width="medium"),
                "Official benchmark": st.column_config.TextColumn(width="medium"),
                "Bus eq / hr": st.column_config.TextColumn(width="small"),
            },
        )
        st.markdown(
            "**Engine strategy** uses scheduled coverage, stop proximity, walking evidence, network scale, and regional-hub structure.  \n"
            "**Official benchmark** is an analyst-coded broad family from a reviewed host-city source. A match does not validate exact ridership, fleet, hub, or curb quantities.  \n"
            "**Rule strength** describes how clearly the physical evidence crosses a documented rule; it is not a probability.  \n"
            "**Bus equivalents** compare the remaining peak gap with pinned bus-capacity assumptions. More than 60 buses per hour means split the load, spread arrivals, or reduce demand."
        )
