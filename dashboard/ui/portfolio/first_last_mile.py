"""First/last-mile objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.ui.portfolio.tables import access_table
from dashboard.viz.portfolio import (
    portfolio_access_chart,
    portfolio_gap_quadrant_chart,
    portfolio_stop_density_chart,
)


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

    st.markdown("##### Transit readiness vs. first/last-mile gap")
    st.plotly_chart(
        portfolio_gap_quadrant_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_gap_quadrant",
    )
    st.caption(
        "Gap score = a function of transit under-capacity and summer heat (heat compounds a weak transit score, since a hotter "
        "walk from the nearest stop matters more). Bubble size is venue capacity; color is average summer temperature. "
        "Source: GTFS-derived transit score and NOAA/Rice weather evidence. Threshold lines are illustrative reference points "
        "for this branch's current score distribution, not evidenced cutoffs."
    )

    st.markdown("##### Transit stop density around each venue")
    st.plotly_chart(
        portfolio_stop_density_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_stop_density",
    )
    st.caption(
        "Stops counted within walking-distance rings of the actual stadium coordinates, sourced from each city's live GTFS "
        "transit feed. Hover for the nearest-stop distance and serving agencies. This is scheduled-service density, not "
        "walking-path safety or ADA accessibility evidence."
    )

    nearest_stops = frame[["city", "nearest_stop_mi", "feed_status"]].copy()
    nearest_stops["_distance"] = pd.to_numeric(nearest_stops["nearest_stop_mi"], errors="coerce")
    nearest_stops = nearest_stops.sort_values("_distance", na_position="last")
    any_estimated = bool((nearest_stops["feed_status"].fillna("unavailable") != "observed").any())
    for column, (_, row) in zip(st.columns(len(nearest_stops)), nearest_stops.iterrows()):
        estimated = row["feed_status"] != "observed"
        label = str(row["city"]) + (" *" if estimated else "")
        value = f"{row['_distance']:.2f} mi" if pd.notna(row["_distance"]) else "N/A"
        with column:
            st.metric(label=label, value=value, delta="nearest stop", delta_color="off")
    if any_estimated:
        st.caption("\\* Estimated (GTFS not available) - distances from venue centroid to nearest transit stop")
    else:
        st.caption("Distances from venue centroid to nearest transit stop")

    with st.expander(
        "Exact first/last-mile values", icon=":material/table_chart:"
    ):
        st.dataframe(
            access_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
