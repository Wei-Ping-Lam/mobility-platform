"""Visitor movement objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.tables import movement_table
from dashboard.viz.portfolio import (
    portfolio_transit_capacity_chart,
    portfolio_visitor_forecast_chart,
)


def render(frame: pd.DataFrame) -> None:
    st.markdown(
        "#### Where are World Cup attendees forecast to come from, and how might they reach the venue?"
    )
    forecast_view = st.segmented_control(
        "Forecast view",
        ["Attendee Origin", "Mode mix", "Peak timing"],
        default="Attendee Origin",
        required=True,
        key="portfolio_forecast_view",
        width="stretch",
        persist_state="session",
    )
    if str(forecast_view) == "Peak timing":
        col_timing, col_capacity = st.columns(2)
        with col_timing:
            st.plotly_chart(
                portfolio_visitor_forecast_chart(frame, str(forecast_view)),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_visitor_forecast_peak_timing",
            )
        with col_capacity:
            st.plotly_chart(
                portfolio_transit_capacity_chart(frame),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_transit_capacity",
            )
            st.caption(
                "Right: modeled Scheduled-transit demand at arrival vs. departure, as a % of each host's own real "
                "scheduled transit capacity (GTFS) - log scale, since some venues have almost no nearby scheduled "
                "service and reach many times capacity. Scheduled transit is the only mode with an evidenced "
                "capacity ceiling in the supplied data; hosts with zero supplied capacity are listed above the "
                "chart rather than shown at 0%, since a ratio against zero is undefined."
            )
    else:
        st.plotly_chart(
            portfolio_visitor_forecast_chart(frame, str(forecast_view)),
            width="stretch",
            config={"displayModeBar": False},
            key=(
                "portfolio_visitor_forecast_"
                + str(forecast_view).lower().replace(" ", "_")
            ),
        )
    forecast_caption = {
        "Attendee Origin": (
            "Shows the modeled origin mix - host-market, nearby U.S., long-distance U.S., and international/unobserved - "
            "for every hosted match's base attendance case, aggregated across each city's tournament. "
            "Source: FIFA's official match schedule and stage-conditioned attendance scenarios, blended with the Rice-supplied "
            "Veraset/SafeGraph spend-pattern dataset. Supplied commercial customer origins shape only the U.S. prior; "
            "international share is an explicit tournament-stage scenario. Neither is observed FIFA fan behavior."
        ),
        "Mode mix": (
            "Shows modeled planning demand for scheduled transit, event shuttle/coach, private vehicle/taxi, and walk/bike access to each venue. "
            "Source: each city's live GTFS transit feed (exact-hour scheduled service), the first/last-mile access-gap model, and "
            "OSM-derived venue walking evidence. Broad mode demand responds to transit readiness, scheduled coverage, access-gap "
            "severity, and venue-side walking evidence - not delivered service, exact routes, travel time, or measured mode share."
        ),
        "Peak timing": (
            "Left: modeled arrival and departure passenger volumes by hour, anchored to each city's single highest non-host-demand match. "
            "Source: FIFA's official local kickoff time, combined with the low/base/high attendance scenario for that match. "
            "The timing curve reconciles to attendance but is not calibrated to ticket scans or observed FIFA crowd movement."
        ),
    }[str(forecast_view)]
    st.caption(forecast_caption)
    with st.expander("Exact movement values", icon=":material/table_chart:"):
        st.dataframe(
            movement_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
