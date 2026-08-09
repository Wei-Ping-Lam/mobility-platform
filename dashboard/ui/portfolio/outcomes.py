"""Decision outcomes objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.ui.portfolio.tables import outcomes_table
from dashboard.viz.portfolio import portfolio_outcome_chart


def render(frame: pd.DataFrame) -> None:
    st.markdown("#### What does each city's priority single measure change?")
    outcome = st.segmented_control(
        "Outcome to compare",
        ["Access", "Traffic", "CO2e"],
        default="Access",
        required=True,
        key="portfolio_outcome_metric",
        width="stretch",
        persist_state="session",
    )
    outcome_column = {
        "Access": "top_gap_resolved",
        "Traffic": "top_vehicle_trips_avoided",
        "CO2e": "top_net_co2e_kg",
    }[str(outcome)]
    outcome_values = pd.to_numeric(
        frame[outcome_column], errors="coerce"
    ).dropna()
    outcome_rows = frame.dropna(subset=[outcome_column]).sort_values(
        outcome_column, ascending=False
    )
    best_outcome = outcome_rows.iloc[0] if not outcome_rows.empty else None
    unit = {"Access": " / hr", "Traffic": " trips", "CO2e": " kg"}[
        str(outcome)
    ]
    outcome_label = {
        "Access": "access",
        "Traffic": "traffic",
        "CO2e": "CO2e",
    }[str(outcome)]
    metric_grid(
        [
            (
                number(best_outcome[outcome_column], unit)
                if best_outcome is not None
                else "Not available",
                f"Largest modeled {outcome_label} outcome - {best_outcome['city']}"
                if best_outcome is not None
                else "Largest modeled outcome",
                "scenario",
                str(best_outcome["top_intervention"])
                if best_outcome is not None
                else "No qualified measure",
                "teal",
            ),
            (
                number(outcome_values.median(), unit)
                if not outcome_values.empty
                else "Not available",
                "Median modeled outcome",
                "scenario",
                "Across representative matches; values are not summed across incompatible event peaks",
                "blue",
            ),
        ]
    )
    st.plotly_chart(
        portfolio_outcome_chart(frame, str(outcome)),
        width="stretch",
        config={"displayModeBar": False},
        key=f"portfolio_outcome_{str(outcome).lower()}",
    )
    st.caption(
        "Access is peak passengers addressed per hour; traffic is modeled venue-area vehicle trips avoided; CO2e is net avoided emissions after added service mileage. "
        "These are planning outcomes with shared factor ranges, not observed mode shift, roadway congestion relief, or a certified emissions inventory."
    )
    with st.expander("Exact outcome values", icon=":material/table_chart:"):
        st.dataframe(
            outcomes_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
