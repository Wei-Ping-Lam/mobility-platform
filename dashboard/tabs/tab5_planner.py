"""Tab 5 — Intervention Planner: scenario sliders, projected impact, cost/ROI, recommendations."""

import streamlit as st
import pandas as pd
import plotly.express as px

from data import HOST_CITIES, PLOTLY_TEMPLATE

DEFAULT_CITY_INDEX = 2  # Dallas

AGENCY_MAP = {
    "Atlanta": "MARTA (Metropolitan Atlanta Rapid Transit Authority)",
    "Boston": "MBTA (Massachusetts Bay Transportation Authority) + Patriot Place",
    "Dallas": "DART (Dallas Area Rapid Transit) + City of Arlington",
    "Houston": "METRO Houston + Harris County",
    "Kansas City": "RideKC / KCATA",
    "Los Angeles": "LA Metro + City of Inglewood",
    "Miami": "Miami-Dade Transit + MDT",
    "New York/NJ": "NJ Transit + NJDOT + Meadowlands Sports Complex",
    "Philadelphia": "SEPTA + Philadelphia PPA",
    "San Francisco": "VTA + Caltrain + City of Santa Clara",
    "Seattle": "Sound Transit + King County Metro",
}


def render(metrics_df, transit_weight_ratio):
    """
    transit_weight_ratio: the normalized transit-score weight (0-1) from the
    global readiness-score weights, used to project composite-score impact.
    """
    st.markdown("### Mobility Intervention Scenario Planner")
    st.caption("Model the impact of transit investments on mobility stress and CO₂ reduction for a selected city.")

    plan_city = st.selectbox(
        "Select Host City",
        list(HOST_CITIES.keys()),
        index=DEFAULT_CITY_INDEX,
        key="plan_city",
    )
    city_row = metrics_df[metrics_df["city"] == plan_city].iloc[0]

    st.divider()
    col_sliders, col_impact = st.columns([1, 1])

    with col_sliders:
        st.markdown("#### Proposed Interventions")

        shuttle_freq = st.slider(
            "🚌 Event Shuttle Frequency (buses/hour)",
            min_value=0, max_value=60, value=10, step=5,
            help="Dedicated shuttle service to/from venue on match days",
        )
        bike_stations = st.slider(
            "🚲 Bike-Share Stations Near Venue",
            min_value=0, max_value=50, value=5, step=5,
            help="New bike-share docking stations within 1 mile of venue",
        )
        park_ride = st.slider(
            "🅿️ Park & Ride Capacity (spaces)",
            min_value=0, max_value=20000, value=2000, step=1000,
            help="Park-and-ride lots served by dedicated transit",
        )
        pedestrian_infra = st.slider(
            "🚶 Pedestrian Infrastructure Upgrade (%)",
            min_value=0, max_value=100, value=20, step=10,
            help="Shade structures, cooling stations, accessible pathways",
        )

    with col_impact:
        st.markdown("#### Projected Impact")

        base_transit = city_row["transit_score"]
        base_gap = city_row["first_last_mile_gap"]
        base_composite = city_row["composite_score"]
        peak_v = city_row["peak_visitors"]

        # Model improvements
        shuttle_boost   = min(20, shuttle_freq * 0.33)
        bike_boost      = min(8,  bike_stations * 0.16)
        pr_boost        = min(12, park_ride / 1000 * 0.6)
        ped_boost       = min(10, pedestrian_infra * 0.10)
        total_boost     = shuttle_boost + bike_boost + pr_boost + ped_boost

        new_transit     = min(100, base_transit + total_boost)
        new_composite   = min(100, base_composite + total_boost * transit_weight_ratio)
        new_gap         = max(0, base_gap - total_boost * 0.9)

        # Visitors shifted to transit
        base_transit_pct   = base_transit / 100
        new_transit_pct    = new_transit / 100
        shifted_visitors   = int(peak_v * (new_transit_pct - base_transit_pct))

        # CO2 reduction: avg car trip to venue assumed 25 km, 0.21 kg CO2/km
        co2_saved_kg = shifted_visitors * 25 * 0.21
        co2_saved_tonnes = co2_saved_kg / 1000

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Transit Score", f"{new_transit:.0f}/100",
                      delta=f"+{total_boost:.1f}")
            st.metric("Composite Readiness", f"{new_composite:.0f}/100",
                      delta=f"+{new_composite - base_composite:.1f}")
        with c2:
            st.metric("Gap Score", f"{new_gap:.0f}",
                      delta=f"{new_gap - base_gap:.1f}", delta_color="inverse")
            st.metric("Visitors Shifted to Transit", f"{shifted_visitors:,}",
                      delta="per match day")

        st.metric("Est. CO₂ Reduction", f"{co2_saved_tonnes:,.0f} tonnes",
                  delta="per match day vs. baseline", delta_color="normal")

        st.divider()
        # Before/after bar
        before_after = pd.DataFrame({
            "Scenario": ["Baseline", "With Interventions"],
            "Transit Score":       [base_transit,  new_transit],
            "Composite Readiness": [base_composite, new_composite],
            "Gap Score":           [base_gap,       new_gap],
        })
        fig_ba = px.bar(
            before_after.melt(id_vars="Scenario"),
            x="variable", y="value",
            color="Scenario",
            barmode="group",
            color_discrete_map={"Baseline": "#475569", "With Interventions": "#38bdf8"},
            labels={"variable": "", "value": "Score"},
            template=PLOTLY_TEMPLATE,
            height=280,
        )
        fig_ba.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", y=-0.2),
            xaxis=dict(gridcolor="#1e3a5f"),
            yaxis=dict(gridcolor="#1e3a5f", range=[0, 110]),
        )
        st.plotly_chart(fig_ba, width='stretch')

    st.divider()
    # ── Cost & ROI Analysis ───────────────────────────────────────────────────
    st.markdown("#### Investment Cost & Return Analysis")
    st.caption("Capital cost estimates based on US transit infrastructure benchmarks (FTA, NACTO, FHWA)")

    shuttle_capex_per_day  = shuttle_freq * 2880        # $180/bus-hr × 16 hrs
    bike_capex             = bike_stations * 45000       # $45K/station (capital)
    pr_capex               = park_ride * 2800            # $2,800/space (capital)
    ped_capex              = (pedestrian_infra / 10) * 800000  # $800K per 10%
    total_capex            = int(bike_capex + pr_capex + ped_capex)
    total_opex_per_match   = int(shuttle_capex_per_day)

    # Economic return: shifted visitors spend $280/match day + CO₂ social cost ($50/tonne)
    total_games_city       = city_row["games"]
    annual_visitor_return  = shifted_visitors * 280 * total_games_city
    annual_co2_value       = co2_saved_tonnes * total_games_city * 50
    annual_return          = annual_visitor_return + annual_co2_value
    payback_years          = (total_capex / annual_return) if annual_return > 1000 else 99

    col_cost1, col_cost2, col_cost3, col_cost4 = st.columns(4)
    with col_cost1:
        st.metric("Capital Investment", f"${total_capex:,.0f}",
                  delta="one-time capex")
    with col_cost2:
        st.metric("Match-Day Opex", f"${total_opex_per_match:,.0f}",
                  delta="per match")
    with col_cost3:
        st.metric("Annual Economic Return", f"${annual_return:,.0f}",
                  delta=f"visitors + CO₂ value")
    with col_cost4:
        pb = f"{payback_years:.1f} yrs" if payback_years < 50 else "Long-term"
        st.metric("Simple Payback", pb, delta="capital recovery")

    # Cost breakdown bar chart
    cost_items = []
    if bike_capex > 0:
        cost_items.append({"Item": "Bike-Share Stations", "Cost ($)": bike_capex, "Type": "Capital"})
    if pr_capex > 0:
        cost_items.append({"Item": "Park & Ride", "Cost ($)": pr_capex, "Type": "Capital"})
    if ped_capex > 0:
        cost_items.append({"Item": "Pedestrian Infra", "Cost ($)": ped_capex, "Type": "Capital"})
    if shuttle_capex_per_day > 0:
        cost_items.append({"Item": "Shuttle (per match)", "Cost ($)": shuttle_capex_per_day, "Type": "Operating"})
    if cost_items:
        cost_df = pd.DataFrame(cost_items)
        fig_cost = px.bar(
            cost_df, x="Item", y="Cost ($)",
            color="Type",
            color_discrete_map={"Capital": "#38bdf8", "Operating": "#818cf8"},
            text=cost_df["Cost ($)"].apply(lambda v: f"${v:,.0f}"),
            template=PLOTLY_TEMPLATE, height=240,
        )
        fig_cost.update_traces(textposition="outside", textfont_color="white")
        fig_cost.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(gridcolor="#1e3a5f"), yaxis=dict(gridcolor="#1e3a5f"),
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig_cost, width='stretch')

    st.divider()
    st.markdown("#### Recommended Priority Investments")

    gap = city_row["first_last_mile_gap"]
    temp = city_row["avg_temp_c"]
    uhi = city_row["avg_uhi"]
    transit = city_row["transit_score"]

    agency = AGENCY_MAP.get(plan_city, "Local transit authority")

    recs = []
    if transit < 50:
        recs.append(("🚌", "High-frequency event shuttles",
                     f"Transit score of {transit:.0f} indicates heavy car dependency. "
                     f"**Implementing agency:** {agency}. "
                     f"Deploy dedicated match-day shuttles from key rail/bus hubs; 15-min frequency can absorb 15–20% of match-day vehicle load."))
    if gap > 50:
        recs.append(("🔗", "First/last-mile micro-mobility",
                     f"Gap score of {gap:.0f} signals poor connections from transit stops to venue. "
                     f"Bike-share and e-scooter docking at the nearest rail station closes this gap. "
                     f"**Estimated cost:** ${bike_stations * 45000:,.0f} for {bike_stations} stations."))
    if temp > 28:
        recs.append(("🌡️", "Cooling corridors & shade canopies",
                     f"June–July average of {temp:.1f}°C poses heat illness risk for pedestrian access routes. "
                     f"Misting stations and tensile shade canopies along pedestrian corridors reduce apparent temperature by 6–10°C. "
                     f"**Implementing agency:** City Public Works + venue operator."))
    if uhi > 5:
        recs.append(("🌳", "Urban greening along transit corridors",
                     f"UHI of {uhi:.1f}°C above rural baseline amplifies heat risk. "
                     f"Tree canopy (target 20% cover on transit corridors) and cool pavements reduce walkway temperatures 3–5°C year-round."))
    recs.append(("📱", "Unified real-time mobility app",
                 "A FIFA 2026 mobility app integrating real-time bus/shuttle arrivals, bike-share availability, "
                 "parking lot status, and crowd-level alerts. Reduces friction for international visitors unfamiliar with local transit. "
                 "**Partners:** transit agencies + FIFA Host City Liaison."))
    recs.append(("🚗", "Dynamic park-and-ride with transit integration",
                 f"Pre-purchased parking + shuttle bundles sold through the FIFA ticketing platform. "
                 f"{park_ride:,} spaces at {park_ride // 50 + 1} sites, served by dedicated express shuttles, can reduce venue-area traffic by {min(40, park_ride // 200)}%."))

    for icon, title, desc in recs:
        with st.expander(f"{icon} {title}"):
            st.markdown(desc)
