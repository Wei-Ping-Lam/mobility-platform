"""First/last-mile objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.tables import access_table
from dashboard.viz.portfolio import (
    portfolio_access_density_chart,
    portfolio_access_score_chart,
    portfolio_gap_quadrant_chart,
)


def render(frame: pd.DataFrame) -> None:
    st.markdown("#### Where does the venue-side journey fail in the modeled peak hour?")

    parking_available = pd.to_numeric(frame.get("parking_count_1mi"), errors="coerce").notna()
    missing_parking = sorted(frame.loc[~parking_available, "city"].dropna().tolist())

    st.markdown("##### Transit stop and parking density around each venue")
    st.plotly_chart(
        portfolio_access_density_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_access_density",
    )
    st.caption(
        "Each city's three solid bars on the left are transit stops (sourced from each city's live GTFS transit "
        "feed); the three lighter-shade bars on the right, in the same three ring colors, are real OpenStreetMap "
        "amenity=parking facilities. Parking bars are facility counts, not total spaces, since most OSM parking "
        "facilities have no recorded space count; hover for the real space count where one is tagged, plus "
        "nearest-stop distance and serving agencies. Sorted by transit stops within 1 mi, the more heavily "
        "weighted signal in the access score below, so the two metrics don't always agree on host order. Cities "
        "marked \"No parking data\" have no OSM parking snapshot at all - not a real zero. This is "
        "scheduled-service and OSM coverage, not walking-path safety, ADA accessibility, or verified event-day "
        "parking supply."
        + (f" Parking not yet available for: {', '.join(missing_parking)}." if missing_parking else "")
    )

    nearest_stops = frame[["city", "nearest_stop_mi", "feed_status", "nearest_stop_agency"]].copy()
    nearest_stops["_distance"] = pd.to_numeric(nearest_stops["nearest_stop_mi"], errors="coerce")
    nearest_stops = nearest_stops.sort_values("_distance", na_position="last")
    any_estimated = bool((nearest_stops["feed_status"].fillna("unavailable") != "observed").any())
    with st.container(key="nearest_stop_metrics"):
        # 11 cities in one row leaves each column too narrow for the agency
        # name in the delta pill to read - shrink the value text and let the
        # delta pill wrap onto a second line instead of truncating, and split
        # the cities across two rows of columns so each one gets more width.
        st.markdown(
            """
            <style>
            .st-key-nearest_stop_metrics [data-testid='stMetricValue'] { font-size: 1.6rem; }
            .st-key-nearest_stop_metrics [data-testid='stMetricDelta'],
            .st-key-nearest_stop_metrics [data-testid='stMetricDelta'] div {
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: unset !important;
                font-size: 0.75rem;
                line-height: 1.2;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        rows = [row for _, row in nearest_stops.iterrows()]
        midpoint = -(-len(rows) // 2)  # ceil division, so an odd city count puts the extra one in the first row
        for chunk in (rows[:midpoint], rows[midpoint:]):
            for column, row in zip(st.columns(len(chunk)), chunk):
                estimated = row["feed_status"] != "observed"
                label = str(row["city"]) + (" *" if estimated else "")
                value = f"{row['_distance']:.2f} mi" if pd.notna(row["_distance"]) else "N/A"
                agency = row["nearest_stop_agency"]
                delta = f"nearest {agency} stop" if pd.notna(agency) and agency else "nearest stop"
                with column:
                    st.metric(label=label, value=value, delta=delta, delta_color="off")
    if any_estimated:
        st.caption("\\* Estimated (GTFS not available) - distances from venue centroid to nearest transit stop")
    else:
        st.caption("Distances from venue centroid to nearest transit stop")

    st.markdown("##### First/last-mile access score")
    st.plotly_chart(
        portfolio_access_score_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_access_score",
    )
    st.caption(
        "Access score = 100 minus a 75/25 blend of real GTFS transit-stop density and real OSM parking-facility "
        "density (transit weighted more heavily since it is more reliable evidence; falls back to transit density "
        "alone where parking data isn't available yet); it does not factor in heat, so it stays independent of "
        "the heat and urban heat safety criteria, and it doesn't depend on any weight profile - a stable reference "
        "for the readiness-vs-access comparison below."
    )

    st.markdown("##### Weighted readiness score vs. first/last-mile access score")
    st.plotly_chart(
        portfolio_gap_quadrant_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_gap_quadrant",
    )
    st.caption(
        "Access score = 100 minus a 75/25 blend of real GTFS transit-stop density and real OSM parking-facility "
        "density (transit weighted more heavily since it is more reliable evidence; falls back to transit density "
        "alone where parking data isn't available yet); it does not factor in heat, so it stays independent of "
        "the heat and urban heat safety criteria. Bubble size is venue capacity; color is average summer "
        "temperature, shown for context only. Threshold lines are illustrative reference points for this "
        "branch's current score distribution, not evidenced cutoffs."
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
