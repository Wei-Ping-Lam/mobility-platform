"""First/last-mile objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.ui.portfolio.tables import access_table
from dashboard.viz.portfolio import portfolio_access_chart


def render(frame: pd.DataFrame) -> None:
    largest_gap = frame.dropna(subset=["capacity_qualified_gap_pph"]).sort_values(
        "capacity_qualified_gap_pph", ascending=False
    )
    largest_gap_row = largest_gap.iloc[0] if not largest_gap.empty else None
    zero_capacity_matches = int(
        pd.to_numeric(frame["zero_capacity_matches"], errors="coerce")
        .fillna(0)
        .sum()
    )
    match_count = int(
        pd.to_numeric(frame["city_match_count"], errors="coerce").fillna(0).sum()
    )
    missing_walk_paths = int((frame["walking_status"] == "unavailable").sum())

    st.markdown("#### Where does the venue-side journey fail in the modeled peak hour?")
    metric_grid(
        [
            (
                number(
                    largest_gap_row["capacity_qualified_gap_pph"], " / hr"
                )
                if largest_gap_row is not None
                else "Not available",
                f"Largest scheduled-capacity gap - {largest_gap_row['city']}"
                if largest_gap_row is not None
                else "Largest scheduled-capacity gap",
                "scenario",
                f"{largest_gap_row['peak_direction']} peak for the representative match"
                if largest_gap_row is not None
                else "Peak direction unavailable",
                "coral",
            ),
            (
                f"{zero_capacity_matches} of {match_count}",
                "Matches with zero scheduled half-mile capacity",
                "derived",
                f"{missing_walk_paths} cities also lack an event-stop walking path",
                "amber",
            ),
        ]
    )
    st.plotly_chart(
        portfolio_access_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_first_last_mile",
    )
    st.caption(
        "Scheduled coverage = event-valid scheduled passenger capacity in the exact peak hour and direction divided by modeled peak movement. "
        "Walking evidence covers one event-relevant stop-to-venue path; it is the venue-side last mile for arrivals and first mile for departures, not an origin-to-venue accessibility or safety audit."
    )
    with st.expander(
        "Exact first/last-mile values", icon=":material/table_chart:"
    ):
        st.dataframe(
            access_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
