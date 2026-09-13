"""Transportation resilience objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.tables import transportation_resilience_table
from dashboard.viz.portfolio import (
    transportation_resilience_components_chart,
    transportation_resilience_ranking_chart,
)


def render(frame: pd.DataFrame) -> None:
    ranked = frame.dropna(subset=["resilience_rating"]).sort_values(
        "resilience_rating", ascending=False
    )
    city_order = ranked["city"].tolist() + [
        city for city in frame["city"].tolist() if city not in set(ranked["city"])
    ]

    st.markdown("#### How well does each host's transportation system absorb a shock?")
    st.plotly_chart(
        transportation_resilience_ranking_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_resilience_rank",
    )
    st.caption(
        "A 0-10 rating blending three real signals: how much scheduled transit capacity would still cover peak "
        "demand after a 10% demand surge and a 20% capacity loss (50%), real GTFS event-window departure "
        "frequency near the venue (30% - faster recovery if one trip is missed or delayed), and real published "
        "dedicated-capacity evidence (20%). This is a sensitivity stress test, not a probability-weighted "
        "disruption forecast, and it is independent of readiness and sustainability - a city can score well on "
        "either of those and poorly here."
    )
    st.markdown("##### What drives resilience?")
    st.plotly_chart(
        transportation_resilience_components_chart(frame, city_order),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_resilience_components",
    )
    st.caption(
        "Stress-test coverage is scheduled passenger capacity divided by peak demand after the same shock, "
        "capped at 100%. Every host's coverage after this shock is well under half, reflecting how little spare "
        "transit capacity is scheduled for peak match-day movement across this dataset - a shared structural "
        "finding, not a single host's failure."
    )
    with st.expander("Exact resilience values", icon=":material/table_chart:"):
        st.dataframe(
            transportation_resilience_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
