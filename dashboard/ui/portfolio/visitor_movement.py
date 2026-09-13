"""Visitor movement objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.tables import movement_table
from dashboard.viz.portfolio import (
    city_hourly_movement_chart,
    portfolio_visitor_forecast_chart,
)


def render(frame: pd.DataFrame, hourly_movement: pd.DataFrame) -> None:
    st.markdown(
        "#### Where are World Cup attendees forecasted to come from, and how might they reach the venue?"
    )
    forecast_view = st.segmented_control(
        "Forecast view",
        ["Peak timing", "Transportation Mode Mix", "Attendee Origin"],
        default="Peak timing",
        required=True,
        key="portfolio_forecast_view",
        width="stretch",
        persist_state="session",
    )
    if str(forecast_view) == "Peak timing":
        peak_city = frame.sort_values("forecast_departure_peak_base", ascending=False, na_position="last").iloc[0]
        st.info(
            f"Peak timing takeaway: {peak_city['city']} has the largest modeled departure peak in the representative-match screen "
            f"({float(peak_city['forecast_departure_peak_base']):,.0f} passengers/hour). Shaded bands on the city curve show the low-high attendance scenario."
        )
        col_timing, col_capacity = st.columns(2)
        with col_timing:
            st.plotly_chart(
                portfolio_visitor_forecast_chart(frame, str(forecast_view)),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_visitor_forecast_peak_timing",
            )
            st.caption(
                "Arrival and departure peak-hour volumes for each city's highest non-host-demand match, "
                "using the base attendance scenario (95% of venue capacity). Hover for the 85-100% occupancy "
                "planning range and peak time relative to FIFA's official local kickoff. "
                "These modeled peaks are not calibrated to ticket scans or observed FIFA crowd movement."
            )
        with col_capacity:
            # The chart needs the selected city before it renders, but the selector
            # itself belongs visually below the chart - reserve the chart's slot
            # first, read the persisted selection, then fill the slot afterward.
            chart_slot = st.container()
            cities = sorted(hourly_movement["city"].dropna().unique().tolist())
            selected_city = st.selectbox("Select host city", cities, key="peak_timing_city")
            city_rows = hourly_movement[hourly_movement["city"] == selected_city]
            match_count = int(city_rows["match_count"].iloc[0]) if not city_rows.empty else 0
            with chart_slot:
                st.plotly_chart(
                    city_hourly_movement_chart(hourly_movement, selected_city),
                    width="stretch",
                    config={"displayModeBar": False},
                    key="portfolio_city_hourly_movement",
                )
            st.caption(
                f"Average modeled arrival and departure passengers per hour for {selected_city}, relative to "
                f"kickoff, averaged across all {match_count} of its hosted matches. The hour-by-hour shape (how "
                "sharply arrivals concentrate before kickoff, how departures spread afterward) is the same fixed "
                "assumption applied to every city and match; only the attendance scale differs, so this shows "
                "city-specific volume, not a city-specific timing pattern. Lines use 95% occupancy; shaded "
                "bands span 85-100% of venue capacity. These are attendance scenarios, not statistical confidence intervals."
            )
    else:
        if str(forecast_view) == "Transportation Mode Mix":
            private = pd.to_numeric(frame.get("mode_private_taxi_share_pct"), errors="coerce")
            if private.notna().any():
                row = frame.loc[private.idxmax()]
                st.info(
                    f"Mode-mix takeaway: {row['city']} has the highest modeled private vehicle/taxi share "
                    f"({float(row['mode_private_taxi_share_pct']):.1f}%), making it the clearest candidate for shuttle, curb, and parking-pressure review."
                )
        if str(forecast_view) == "Attendee Origin":
            non_host = pd.to_numeric(frame.get("forecast_non_host_share_pct"), errors="coerce")
            if non_host.notna().any():
                row = frame.loc[non_host.idxmax()]
                st.info(
                    f"Origin takeaway: {row['city']} has the highest modeled non-host-market share "
                    f"({float(row['forecast_non_host_share_pct']):.1f}%), so regional and long-distance arrival planning matters most there."
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
            "Attendee Origin": (
                "Shows the modeled origin mix - host-market, nearby U.S., long-distance U.S., and international/unobserved - "
                "for every hosted match's base attendance case, aggregated across each city's tournament. Match dates, venues, "
                "and stages are FIFA's official schedule; the domestic (U.S.) split and the international share come from two "
                "different, unrelated inputs detailed below. Neither is observed FIFA fan behavior."
            ),
            "Transportation Mode Mix": (
                "Shows one combined modeled access-mode split per match - scheduled transit, event shuttle/coach, private "
                "vehicle/taxi, and walk/bike - not separated by arrival vs. departure (see below). Each origin type's "
                "attendees start from a different assumed base leaning toward transit, shuttle, and walking, which is then "
                "scaled by this city's real transit readiness, real scheduled-capacity coverage, and real venue walking "
                "distance; private vehicle/taxi is whatever is left over. See assumptions below for the full breakdown - "
                "this is not delivered service, exact routes, travel time, or measured mode share."
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

    if str(forecast_view) == "Transportation Mode Mix":
        with st.expander("Data sources and assumptions", icon=":material/fact_check:"):
            st.markdown(
                "**Real evidence inputs** - this city's transit-proximity readiness score (from real nearby GTFS "
                "service), how much of the match's modeled peak demand its real scheduled GTFS capacity actually "
                "covers, and the real OSM-derived walking-network distance from venue to the nearest useful stop."
            )
            st.markdown(
                "**Base mode leanings by origin type (EQ-MODE-SPLIT-01)** - explicit scenario assumptions invented for "
                "this project, not measured: attendees traveling from farther away are assumed more transit- and "
                "shuttle-inclined and less likely to walk or bike."
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Origin type": "Host market", "Base transit lean": "18%", "Base shuttle lean": "6%", "Base walk/bike lean": "8%"},
                        {"Origin type": "Nearby U.S.", "Base transit lean": "12%", "Base shuttle lean": "12%", "Base walk/bike lean": "3%"},
                        {"Origin type": "Long-distance U.S.", "Base transit lean": "20%", "Base shuttle lean": "18%", "Base walk/bike lean": "2%"},
                        {"Origin type": "International / unobserved", "Base transit lean": "24%", "Base shuttle lean": "20%", "Base walk/bike lean": "4%"},
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            st.markdown(
                "- **Scheduled transit** scales up from that base with this city's real transit-readiness score, then "
                "collapses to roughly 5% of that level at venues with no real scheduled capacity at all - it never "
                "exceeds 62% for any origin type.\n"
                "- **Event shuttle/coach** rises further with however much of modeled peak demand the real scheduled "
                "capacity does not cover, since shuttle service is scenario-modeled as one way to help fill that gap.\n"
                "- **Walk/bike** scales down with the real OSM walking distance to the venue and reaches zero beyond "
                "2.4 km.\n"
                "- **Private vehicle/taxi is not modeled directly** - it is whatever share is left after scheduled "
                "transit, shuttle, and walk/bike are subtracted, with a floor of at least 18% for every origin type "
                "by construction."
            )
            st.caption(
                "No ticketing, mobile-location, parking, or observed-mode-share evidence backs these base leanings or "
                "the 62%/2.4 km ceilings - they are explicit scenario assumptions. Replace them if that evidence "
                "becomes available."
            )

    if str(forecast_view) == "Peak timing":
        with st.expander("Data sources and assumptions", icon=":material/fact_check:"):
            st.markdown(
                "**Kickoff time and attendance scenario** (real, sourced) - FIFA's official local kickoff time for "
                "each match, combined with a low/base/high attendance scenario equal to the venue's real seating "
                "capacity times an assumed 85% / 95% / 100% occupancy rate. Occupancy is an explicit scenario "
                "assumption, not observed or ticketed attendance."
            )
            st.markdown(
                "**Arrival and departure timing (fixed scenario shape)** - not measured, not city- or "
                "match-specific: the same assumed hour-by-hour profile is applied to every match at every venue."
            )
            st.dataframe(
                pd.DataFrame(
                    [
                        {"Hours from kickoff": "-4", "Share of attendance": "5%", "Direction": "Arrival"},
                        {"Hours from kickoff": "-3", "Share of attendance": "15%", "Direction": "Arrival"},
                        {"Hours from kickoff": "-2", "Share of attendance": "30%", "Direction": "Arrival"},
                        {"Hours from kickoff": "-1", "Share of attendance": "35%", "Direction": "Arrival"},
                        {"Hours from kickoff": "0", "Share of attendance": "10%", "Direction": "Arrival"},
                        {"Hours from kickoff": "+1", "Share of attendance": "5%", "Direction": "Arrival"},
                        {"Hours from kickoff": "+1", "Share of attendance": "2%", "Direction": "Departure"},
                        {"Hours from kickoff": "+2", "Share of attendance": "43%", "Direction": "Departure"},
                        {"Hours from kickoff": "+3", "Share of attendance": "35%", "Direction": "Departure"},
                        {"Hours from kickoff": "+4", "Share of attendance": "15%", "Direction": "Departure"},
                        {"Hours from kickoff": "+5", "Share of attendance": "5%", "Direction": "Departure"},
                    ]
                ),
                hide_index=True,
                width="stretch",
            )
            st.markdown(
                "Departure hours assume a fixed 120-minute match length, so departure shares are anchored to "
                "kickoff + 2 hours, not the actual final whistle. Both profiles carry a small tail into hour +1 "
                "(kickoff + 1 hour) - a few attendees still arriving after kickoff, and a much smaller share "
                "leaving early, one hour before the assumed final whistle - so that hour shows real, if modest, "
                "movement in both directions rather than a gap. Left shows this profile for each city's single "
                "highest non-host-demand match; right averages it across every one of that city's real hosted "
                "matches, which changes the volume but not the shape."
            )
            st.caption(
                "No ticket scans, stadium egress counts, or observed crowd-movement data back the occupancy rates "
                "or the arrival/departure profile - they are explicit scenario assumptions. Replace them if that "
                "evidence becomes available."
            )

    with st.expander("Exact movement values", icon=":material/table_chart:"):
        st.caption(
            "Tournament totals sum attendance across all hosted matches, not unique visitors. "
            "For example, a 70,000-seat venue hosting 6 matches at 95% occupancy totals 399,000 "
            "attendee-visits. Non-host-market attendee-visits are a subset of that total; "
            "a person attending multiple matches is counted each time. Peak-hour values refer to the peak forecast match."
        )
        st.dataframe(
            movement_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
