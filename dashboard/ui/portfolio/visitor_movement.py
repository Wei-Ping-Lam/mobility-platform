"""Visitor movement objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.ui.portfolio.tables import movement_table
from dashboard.viz.portfolio import portfolio_visitor_forecast_chart


def render(frame: pd.DataFrame) -> None:
    forecast_rows = frame.dropna(
        subset=["forecast_non_host_attendees_base"]
    ).sort_values("forecast_non_host_attendees_base", ascending=False)
    highest_external = forecast_rows.iloc[0] if not forecast_rows.empty else None
    planning_scenarios = int((frame["forecast_status"] == "scenario").sum())

    st.markdown(
        "#### Where are World Cup attendees forecast to come from, and how might they reach the venue?"
    )
    metric_grid(
        [
            (
                number(
                    highest_external["forecast_non_host_attendees_base"],
                    " attendees",
                )
                if highest_external is not None
                else "Not available",
                f"Largest non-host-market forecast - {highest_external['city']}"
                if highest_external is not None
                else "Largest non-host-market forecast",
                "scenario",
                f"{number(highest_external['forecast_non_host_share_pct'], '%', 1)} of base city-tournament attendance"
                if highest_external is not None
                else "Base city-tournament attendance",
                "violet",
            ),
            (
                f"{planning_scenarios} of {len(frame)}",
                "Cities labeled scenario forecast",
                "scenario",
                "No city has observed FIFA fan origin and mode calibration",
                "amber",
            ),
        ]
    )
    forecast_view = st.segmented_control(
        "Forecast view",
        ["Origin mix", "Mode mix", "Peak timing"],
        default="Origin mix",
        required=True,
        key="portfolio_forecast_view",
        width="stretch",
        persist_state="session",
    )
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
        "Origin mix": (
            "The forecast allocates every hosted match attendance case to host-market, nearby U.S., long-distance U.S., and international/unobserved origin types, then aggregates compatible attendee counts across the city tournament. "
            "Supplied commercial customer origins shape only the U.S. prior; international share is an explicit tournament-stage scenario. Neither is observed FIFA fan behavior."
        ),
        "Mode mix": (
            "Broad mode demand responds to transit readiness, exact-hour scheduled coverage, access-gap severity, and venue-side walking evidence. "
            "It predicts planning demand for transit, shuttles/coaches, private vehicles/taxis, and walk/bike access—not delivered service, exact routes, travel time, or measured mode share."
        ),
        "Peak timing": (
            "The city's highest non-host-demand match anchors this timing view. Official local kickoff anchors fixed low/base/high arrival and post-match departure profiles. "
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
