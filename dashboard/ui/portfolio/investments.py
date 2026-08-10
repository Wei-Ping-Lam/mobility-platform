"""Investments and strategies objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import (
    intervention_package_levers,
    metric_grid,
    number,
)
from dashboard.ui.portfolio.tables import actions_table
from dashboard.viz.portfolio import portfolio_actions_chart, portfolio_package_benefit_chart

PACKAGE_OPTIONS = ("Operational Package", "Capital Package")
_PACKAGE_KEY = {"Operational Package": "operational", "Capital Package": "capital"}


def render(frame: pd.DataFrame) -> None:
    actions = frame.dropna(subset=["top_gap_resolved"]).sort_values(
        "top_gap_resolved", ascending=False
    )
    highest_action = actions.iloc[0] if not actions.empty else None
    distinct_actions = int(frame["top_intervention"].dropna().nunique())
    qualified_action_cities = int(frame["top_option_qualified"].fillna(False).sum())

    st.markdown("#### What concrete measure should each host validate first?")
    metric_grid(
        [
            (
                f"{distinct_actions} measure types",
                "Bottleneck-matched priority screens",
                "scenario",
                "Zero service, long approaches, heat, and existing route capacity trigger different screens",
                "teal",
            ),
            (
                f"{qualified_action_cities} of {len(frame)}",
                "Cities with a qualified priority screen",
                "scenario",
                number(highest_action["top_gap_resolved"], " / hr")
                + " is the largest modeled single-measure benefit"
                if highest_action is not None
                else "No qualified benefit available",
                "blue",
            ),
        ]
    )
    st.plotly_chart(
        portfolio_actions_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_priority_actions",
    )
    st.caption(
        "The priority is a transparent bottleneck-matched screening measure, not an automatic winner or agency commitment. "
        "Operational/capital packages are compared directly, per city, below."
    )
    with st.expander(
        "Exact investment and strategy values", icon=":material/table_chart:"
    ):
        st.dataframe(
            actions_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )

    st.divider()
    st.markdown("##### Mobility intervention scenario planner")
    st.caption(
        "Compare the two named, pre-evaluated intervention packages for one host against its own scheduled baseline. "
        "Levers and outcomes are the real InterventionPackage definitions and evaluate_intervention() results already "
        "computed for that host's representative match - not a live formula driven by these controls."
    )

    cities = sorted(frame["city"].dropna().unique().tolist())
    default_city = str(highest_action["city"]) if highest_action is not None and highest_action["city"] in cities else cities[0]
    selected_city = st.selectbox(
        "Select host city",
        cities,
        index=cities.index(default_city),
        key="investments_planner_city",
    )
    package_name = st.segmented_control(
        "Intervention package",
        list(PACKAGE_OPTIONS),
        default="Operational Package",
        required=True,
        key="investments_planner_package",
        width="stretch",
    )
    package_key = _PACKAGE_KEY[str(package_name)]
    city_row = frame[frame["city"] == selected_city].iloc[0]

    col_levers, col_impact = st.columns([1, 1])
    with col_levers:
        st.markdown("**Package levers**")
        levers = intervention_package_levers().get(str(package_name), [])
        if levers:
            for label, value in levers:
                st.markdown(f"- {label}: **{value}**")
        else:
            st.caption("No levers defined for this package.")
        st.caption(
            f"Evidence status: {city_row.get(f'{package_key}_status', 'unavailable')} - "
            "a planning scenario, not an agency commitment or observed outcome."
        )

    with col_impact:
        st.markdown("**Projected impact vs. baseline**")
        gap_resolved = city_row.get(f"{package_key}_gap_resolved")
        baseline_trips = city_row.get("baseline_vehicle_trips_base")
        package_trips = city_row.get(f"{package_key}_vehicle_trips_base")
        trips_avoided = (
            max(float(baseline_trips) - float(package_trips), 0.0)
            if pd.notna(baseline_trips) and pd.notna(package_trips)
            else None
        )
        net_co2e = city_row.get(f"{package_key}_net_co2e_base")
        cost_base = city_row.get(f"{package_key}_cost_base")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("Peak passengers addressed / hr", number(gap_resolved))
            st.metric("Vehicle trips avoided", number(trips_avoided))
        with c2:
            st.metric("Net CO2e avoided (kg)", number(net_co2e))
            st.metric(
                "Planning cost",
                f"${float(cost_base):,.0f}" if pd.notna(cost_base) else "Not available",
            )

    st.plotly_chart(
        portfolio_package_benefit_chart(city_row),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_package_benefit",
    )
    st.caption(
        "Baseline resolves zero gap, avoids zero vehicle trips, and avoids zero CO2e by definition, so it is omitted "
        "from the chart rather than plotted as three zero bars. Cost is reported above, not on this chart, because it "
        "is on a different unit (planning USD) than the three benefit measures shown here."
    )
