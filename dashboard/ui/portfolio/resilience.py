"""Resilience objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import render_weight_settings
from dashboard.ui.portfolio.tables import resilience_table
from dashboard.viz.portfolio import (
    readiness_components_chart,
    readiness_map_chart,
    readiness_ranking_chart,
)


def render(frame: pd.DataFrame, metrics: pd.DataFrame) -> None:
    ranked = frame.dropna(subset=["strict_rank", "strict_score"]).sort_values(
        "strict_rank"
    )
    readiness_order = ranked["city"].tolist() + [
        city for city in frame["city"].tolist() if city not in set(ranked["city"])
    ]

    st.markdown("#### Host City Readiness Ranking")
    render_weight_settings()
    col_rank, col_map = st.columns(2)
    with col_rank:
        st.plotly_chart(
            readiness_ranking_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="portfolio_readiness_rank",
        )
        st.caption(
            "Readiness combines first/last-mile access, heat safety, urban heat safety, and venue support under the weights set above. "
            "It is orientation, not a transport disruption model or an investment ranking."
        )
    with col_map:
        st.plotly_chart(
            readiness_map_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="portfolio_readiness_map",
        )
        st.caption(
            "Each dot is a host city's venue location, colored by its readiness score under the weights set above. "
            "Dot size corresponds to the venue's seating capacity."
        )
    st.markdown("##### What drives readiness?")
    st.plotly_chart(
        readiness_components_chart(metrics, readiness_order),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_readiness_components",
    )
    st.caption(
        "Heat safety and urban heat safety are deliberately separate signals: heat safety reflects the region's "
        "ambient air-temperature risk on match days, while urban heat safety reflects how much hotter the "
        "immediate venue area itself runs due to pavement and built environment (the local urban-heat-island "
        "effect) - a city can score well on one and poorly on the other."
    )
    st.caption(
        "**First/last-mile access** is 100 minus the first/last-mile gap score: a 75/25 blend of real GTFS "
        "transit-stop density (closer stops and more routes count more, scaled so the best-served host among "
        "these 11 cities scores 100) and real OSM parking-facility density (same distance-band weighting, scaled "
        "the same way among cities with a real parking snapshot) - transit weighted more heavily since it is more "
        "reliable evidence. It falls back to transit density alone for cities without parking data yet, and does "
        "not factor in heat."
    )
    st.caption(
        "**Heat safety** starts at 100 and subtracts 2.2 points per degree Celsius the June-July 90th-percentile "
        "[NOAA heat index](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) "
        "(Rothfusz formula, from the nearest real weather station) sits above 20°C."
    )
    st.caption(
        "**Urban heat safety** starts at 100 and subtracts 7 points per degree Celsius of real urban-heat-island "
        "effect near the venue - surface temperature, not air temperature or physiological heat exposure. Most "
        "cities use the Rice WC Hack urban-heat dataset's distance-weighted venue reading; Boston instead uses "
        "real [USGS Landsat Collection 2 satellite surface-temperature imagery]"
        "(https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature) - its two-mile "
        "venue-buffer temperature minus a wider 3-8 mile reference-area temperature, since Boston lacks eligible "
        "Rice UHI coverage."
    )
    st.caption(
        "**Venue support** scores how many real nearby destinations - restaurants, hotels, retail, attractions, "
        "and similar points of interest - sit within one mile of the venue, using the Rice WC Hack "
        "points-of-interest dataset, scaled against the host city with the highest count among these 11 "
        "(technically the 95th-percentile value of that 11-city distribution, which in practice lands very close "
        "to the single highest city). Boston, Dallas, and New York/NJ each show zero POI count within one mile in "
        "the supplied data - consistent with those three stadiums sitting in suburban, parking-lot-dominated "
        "complexes rather than dense urban districts - so they score at or near zero here; that does not mean no "
        "amenities exist nearby, only that none were captured within this specific one-mile radius in this "
        "dataset. A higher score means a more amenity-dense surrounding area; it does not measure walkability, "
        "safety, or actual visitor foot traffic."
    )
    with st.expander("Exact resilience values", icon=":material/table_chart:"):
        st.dataframe(
            resilience_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
