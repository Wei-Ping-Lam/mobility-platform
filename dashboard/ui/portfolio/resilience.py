"""Resilience objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number, render_weight_settings
from dashboard.ui.portfolio.tables import resilience_table
from dashboard.viz.portfolio import (
    portfolio_resilience_chart,
    readiness_components_chart,
    readiness_ranking_chart,
)


def render(frame: pd.DataFrame, metrics: pd.DataFrame) -> None:
    ranked = frame.dropna(subset=["strict_rank", "strict_score"]).sort_values(
        "strict_rank"
    )
    highest = ranked.iloc[0] if not ranked.empty else None
    readiness_order = ranked["city"].tolist() + [
        city for city in frame["city"].tolist() if city not in set(ranked["city"])
    ]
    stress_values = pd.to_numeric(
        frame["stress_coverage_pct"], errors="coerce"
    ).dropna()

    st.markdown(
        "#### How do hosts rank, and how much scheduled coverage survives a common stress?"
    )
    render_weight_settings()
    metric_grid(
        [
            (
                f"#{int(highest['strict_rank'])} - {highest['city']}"
                if highest is not None
                else "Not available",
                "Overall readiness leader",
                "derived",
                f"{number(highest['strict_score'], decimals=1)} / 100 under current weights"
                if highest is not None
                else "Eligible evidence required",
                "teal",
            ),
            (
                f"{stress_values.median():.1f}%"
                if not stress_values.empty
                else "Not available",
                "Median stress-test coverage",
                "scenario",
                "After 10% more demand and 20% less scheduled capacity",
                "coral",
            ),
        ]
    )
    st.plotly_chart(
        readiness_ranking_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_readiness_rank",
    )
    st.caption(
        "Readiness combines transit proximity, heat safety, urban heat safety, and venue support under the weights set above. "
        "It is orientation, not a transport disruption model or an investment ranking."
    )
    st.markdown("##### Transportation stress test")
    st.plotly_chart(
        portfolio_resilience_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_resilience_stress",
    )
    st.caption(
        "The same sensitivity is applied to every representative match: peak movement rises 10% while scheduled passenger capacity falls 20%. "
        "This reports retained scheduled coverage in physical units; it is not the probability of a disruption."
    )
    with st.expander("What drives readiness?", icon=":material/grid_view:"):
        st.plotly_chart(
            readiness_components_chart(metrics, readiness_order),
            width="stretch",
            config={"displayModeBar": False},
            key="portfolio_readiness_components",
        )
        st.caption(
            "Transit proximity counts relative nearby GTFS service; heat metrics invert exposure; venue support counts nearby destinations. "
            "None of these substitutes for event-hour capacity, walking safety, or ADA evidence."
        )
    with st.expander("Exact resilience values", icon=":material/table_chart:"):
        st.dataframe(
            resilience_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
