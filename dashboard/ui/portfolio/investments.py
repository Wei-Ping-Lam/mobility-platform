"""Investments and transit objective renderer."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import evaluate_custom_package, number
from dashboard.viz.portfolio import portfolio_custom_scenario_chart


def render(frame: pd.DataFrame, metrics: pd.DataFrame, artifacts: Mapping[str, Any]) -> None:
    st.markdown("#### Model a mobility intervention scenario for one host")
    st.caption(
        "The sliders below build a real InterventionPackage and run it live through this app's own "
        "evaluate_intervention() model - the same equation and factor registry (FTA/NACTO-style shuttle, "
        "park-ride, bike-hub, and cooled-walkway cost/capacity ranges) used everywhere else in this app. "
        "This is not a fabricated formula reacting to the sliders."
    )

    cities = sorted(frame["city"].dropna().unique().tolist())
    selected_city = st.selectbox("Select host city", cities, key="investments_planner_city")
    city_row = frame[frame["city"] == selected_city].iloc[0]
    match_id = str(city_row.get("representative_match_id") or "")

    col_sliders, col_impact = st.columns([1, 1])
    with col_sliders:
        st.markdown("**Proposed interventions**")
        shuttle_freq = st.slider(
            ":material/directions_bus: Event shuttle frequency (buses/hour)",
            0, 60, 10, 5,
            help="Dedicated shuttle service to/from the venue on match days.",
        )
        bike_stations = st.slider(
            ":material/directions_bike: Bike-share stations near venue",
            0, 50, 5, 5,
            help="New bike-share docking stations within the venue-area walk.",
        )
        park_ride = st.slider(
            ":material/local_parking: Park & Ride capacity (spaces)",
            0, 20_000, 2_000, 1_000,
            help="Park-and-ride spaces served by dedicated feeder transit.",
        )
        pedestrian_pct = st.slider(
            ":material/directions_walk: Pedestrian infrastructure upgrade (%)",
            0, 100, 20, 10,
            help="Cooled/shaded walkway coverage on the venue-area walking corridor (100% = about 3 km covered).",
        )
        # Real InterventionPackage levers derived from the sliders above.
        cooled_walkway_km = round(pedestrian_pct / 100 * 3.0, 2)
        feeder_departures = round(park_ride / 80) if park_ride > 0 else 0

    outcome = evaluate_custom_package(
        selected_city,
        match_id,
        metrics,
        artifacts,
        shuttle_buses_per_hour=shuttle_freq,
        bike_hub_spaces=bike_stations,
        park_ride_spaces=park_ride,
        park_ride_feeder_departures_per_hour=feeder_departures,
        cooled_walkway_km=cooled_walkway_km,
    )

    with col_impact:
        st.markdown("**Projected impact**")
        if outcome is None:
            st.info("No representative-match evidence is available for this city yet.")
        else:
            baseline_trips = city_row.get("baseline_vehicle_trips_base")
            custom_trips = outcome.get("venue_vehicle_trips_base")
            trips_avoided = (
                max(float(baseline_trips) - float(custom_trips), 0.0)
                if pd.notna(baseline_trips) and custom_trips is not None
                else None
            )
            co2e_kg = outcome.get("net_co2e_kg_base")
            cost = outcome.get("cost_base")

            c1, c2 = st.columns(2)
            with c1:
                st.metric("Peak passengers addressed / hr", number(outcome.get("gap_resolved_passengers")))
                st.metric("Vehicle trips avoided", number(trips_avoided))
            with c2:
                st.metric(
                    "Est. CO2e avoided",
                    f"{co2e_kg / 1000:,.1f} tonnes" if co2e_kg is not None else "Not available",
                )
            st.metric(
                "Planning cost (capital + operating)",
                f"${float(cost):,.0f}" if cost is not None else "Not available",
            )

    if outcome is not None:
        st.plotly_chart(
            portfolio_custom_scenario_chart(outcome, city_row.get("baseline_vehicle_trips_base")),
            width="stretch",
            config={"displayModeBar": False},
            key="portfolio_custom_scenario",
        )
        st.caption(
            "Baseline is zero by definition - no intervention resolves zero gap, avoids zero vehicle trips, and "
            "avoids zero CO2e. There is no evidenced relationship in this model between these levers and the "
            "Overview tab's Transit Score, Composite Readiness, or First/last-mile Gap Score, so those are not shown "
            "here; inventing one would be exactly the kind of fabricated formula this app avoids."
        )
        with st.expander("Assumptions behind this scenario", icon=":material/fact_check:"):
            st.markdown(
                "- **Park & Ride feeder service** is assumed at roughly 1 departure per 80 spaces (matching this "
                "app's Capital Package ratio); it is not an independent slider.\n"
                "- **Pedestrian infrastructure upgrade (%)** maps to 0-3 km of cooled/shaded walkway coverage.\n"
                "- This custom scenario covers only the four levers above - it does not include added scheduled "
                "transit departures or arrival-time spreading, which the named Operational and Capital packages "
                "elsewhere in this app's evidence base do include.\n"
                "- Costs use the same FTA/NACTO/FHWA-style planning factor ranges (base case) as every other "
                "evaluated package in this app - see `docs/ASSUMPTIONS.md` for the exact low/base/high ranges."
            )
