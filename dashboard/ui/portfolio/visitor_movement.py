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
        ["Attendee Origin", "Transportation Mode Mix", "Peak timing"],
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
            "for every hosted match's base attendance case, aggregated across each city's tournament. Match dates, venues, "
            "and stages are FIFA's official schedule; the domestic (U.S.) split and the international share come from two "
            "different, unrelated inputs detailed below. Neither is observed FIFA fan behavior."
        ),
        "Transportation Mode Mix": (
            "Shows one combined modeled access-mode split per match - scheduled transit, event shuttle/coach, private "
            "vehicle/taxi, and walk/bike - not separated by arrival vs. departure (see below). Source: each city's live "
            "GTFS transit feed and OSM-derived venue walking distance, fed into this app's own access-gap model. Responds "
            "to transit readiness, scheduled coverage, and walking evidence - not delivered service, exact routes, travel "
            "time, or measured mode share."
        ),
        "Peak timing": (
            "Left: modeled arrival and departure passenger volumes by hour, anchored to each city's single highest non-host-demand match. "
            "Source: FIFA's official local kickoff time, combined with the low/base/high attendance scenario for that match. "
            "The timing curve reconciles to attendance but is not calibrated to ticket scans or observed FIFA crowd movement."
        ),
    }[str(forecast_view)]
    st.caption(forecast_caption)

    if str(forecast_view) == "Attendee Origin":
        with st.expander("Data sources and assumptions", icon=":material/fact_check:"):
            st.markdown(
                "**FIFA official match schedule** (real, sourced) - "
                "[fifa.com match schedule](https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums). "
                "Supplies each match's venue, date, local kickoff time, and stage."
            )
            st.markdown(
                "**Domestic (U.S.) host/nearby/long-distance split** - uses the Rice-supplied Veraset/SafeGraph commercial "
                "spend-pattern dataset's real home-state distribution for each market as a *prior*: whatever mix of "
                "local/nearby/distant home states already shows up in that market's general commercial visit data is "
                "carried over as the assumed domestic attendee mix. This is a private dataset supplied directly for this "
                "project (no public link exists) and it records ordinary retail/spend visits, not FIFA ticket holders - "
                "it shapes only the relative split *within* the domestic share, not how many attendees are domestic vs. "
                "international."
            )
            st.markdown(
                "**International / unobserved share** - **not sourced from FIFA or any external data.** It is an "
                "explicit scenario assumption invented for this project, scaled by match stage:"
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Stage": "Group", "Low": "10%", "Base": "20%", "High": "30%"},
                        {"Stage": "Round of 32", "Low": "12%", "Base": "22%", "High": "32%"},
                        {"Stage": "Round of 16", "Low": "14%", "Base": "24%", "High": "34%"},
                        {"Stage": "Quarterfinal", "Low": "16%", "Base": "27%", "High": "38%"},
                        {"Stage": "Semifinal / 3rd place", "Low": "18%", "Base": "30%", "High": "42%"},
                        {"Stage": "Final", "Low": "22%", "Base": "35%", "High": "48%"},
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            st.caption(
                "No ticketing, airport, hotel, or visitor-survey evidence backs these numbers yet - replace them if that "
                "evidence becomes available."
            )

    with st.expander("Exact movement values", icon=":material/table_chart:"):
        st.dataframe(
            movement_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
