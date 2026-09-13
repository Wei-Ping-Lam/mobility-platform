"""Resilience objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import render_weight_settings
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
    if not ranked.empty:
        top = ranked.iloc[0]
        bottom = ranked.iloc[-1]
        issue_columns = {
            "transit_score": "Sparse transit stops",
            "frequency_score": "Infrequent transit service",
            "pedestrian_infrastructure_score": "Limited pedestrian infrastructure",
            "benchmark_capacity_score": "Limited dedicated-service evidence",
        }
        components = frame[[column for column in issue_columns if column in frame]].apply(
            pd.to_numeric, errors="coerce"
        )
        components = components.dropna(thresh=2)
        common_issue = "Not available"
        issue_note = "Insufficient comparable access data"
        if not components.empty:
            # Count tied weakest components equally rather than choosing by column order.
            counts = components.eq(components.min(axis=1), axis=0).sum()
            weakest = counts.idxmax()
            common_issue = issue_columns[weakest]
            issue_note = f"Lowest access component in {int(counts[weakest])} of {len(components)} assessed hosts"
        col_top, col_bottom, col_driver = st.columns(3)
        col_top.metric(
            "Highest readiness",
            str(top["city"]),
            f"{float(top['strict_score']):.1f}/100",
            delta_color="off",
        )
        col_bottom.metric(
            "Lowest readiness",
            str(bottom["city"]),
            f"{float(bottom['strict_score']):.1f}/100",
            delta_color="off",
        )
        col_driver.metric(
            "Common first/last-mile issue",
            common_issue,
            issue_note,
            delta_color="off",
        )
    col_rank, col_map = st.columns(2)
    with col_rank:
        st.plotly_chart(
            readiness_ranking_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="portfolio_readiness_rank",
        )
        st.caption(
            "Readiness combines first/last-mile access, heat safety, venue support, and traffic management under the comparison settings below. "
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
            "Each dot is a host city's venue location, colored by its readiness score under the comparison settings below. "
            "Dot size corresponds to the venue's seating capacity."
        )
    render_weight_settings()
    st.markdown("##### What drives readiness?")
    st.plotly_chart(
        readiness_components_chart(metrics, readiness_order),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_readiness_components",
    )
    st.caption(
        "**First/last-mile access** is 100 minus the first/last-mile gap score: a 75/25 blend of a transit-access "
        "score and real OSM parking-facility density - transit access weighted more heavily since it is more "
        "reliable evidence. Transit access itself blends real GTFS transit-stop density (30%), real GTFS "
        "event-window departure frequency (20%), real published/benchmark dedicated-service evidence (35%), and "
        "real pedestrian-infrastructure evidence (15%) - benchmark evidence is weighted above raw density/frequency "
        "because a real, working service that reaches the venue from farther away (e.g. Dallas's TRE-to-charter-bus "
        "bridge) is otherwise invisible to a radius-based density metric. It falls back to whichever of these "
        "components are available for a city, and does not factor in heat."
    )
    st.caption(
        "**Traffic management** is a hand-curated analyst score grounded in each host's real, cited "
        "match-day traffic evidence (documented road closures, enforcement zones, and any real congestion or "
        "gridlock incidents - see the City action plan's Traffic management solution tab). Unlike the other "
        "three criteria, this is decision support - an analyst's synthesis of real reporting, not a directly "
        "measured quantity - the same convention this app uses for its hand-authored city action plans."
    )
    st.caption(
        "**Heat safety** blends two real signals 50/50: ambient air-temperature risk on match days, and how "
        "much hotter the immediate venue area itself runs due to pavement and built environment (the local "
        "urban-heat-island effect) - previously two separate readiness dimensions, combined into one so a host "
        "isn't penalized or credited twice for what is fundamentally one environmental concern. Renormalizes to "
        "whichever of the two is available. "
        "Heat safety's air-temperature component starts at 100 and subtracts 2.2 points per degree Celsius the "
        "June-July 90th-percentile [NOAA heat index](https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database) "
        "(Rothfusz formula, from the nearest real weather station) sits above 20°C. Its urban-heat-island "
        "component starts at 100 and subtracts 7 points per degree Celsius of real surface-temperature effect "
        "near the venue. Most cities use the Rice WC Hack urban-heat dataset's distance-weighted venue reading; "
        "Boston instead uses real [USGS Landsat Collection 2 satellite surface-temperature imagery]"
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
