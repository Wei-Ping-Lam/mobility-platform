"""First/last-mile objective renderer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.tables import access_table
from dashboard.viz.portfolio import (
    access_sustainability_components_chart,
    portfolio_access_density_chart,
    portfolio_frequency_benchmark_chart,
    portfolio_sustainability_access_chart,
)


def render(frame: pd.DataFrame) -> None:
    st.markdown("#### Where does the venue-side journey fail in the modeled peak hour?")
    access = pd.to_numeric(frame.get("gap_score"), errors="coerce")
    if access.notna().any():
        strongest = frame.loc[access.idxmax()]
        weakest = frame.loc[access.idxmin()]
        st.info(
            f"Access takeaway: {strongest['city']} has the strongest venue-side access score, "
            f"while {weakest['city']} has the weakest. "
            "Atlanta stands out for strong access but a low sustainability score, "
            "showing that good venue access does not necessarily mean sustainable mobility."
        )
    st.markdown("##### Sustainability score vs. first/last-mile access score")
    st.plotly_chart(
        portfolio_sustainability_access_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_sustainability_access",
    )
    with st.expander("How the two scores are calculated"):
        st.markdown("**Access score (0-100)**")
        st.markdown(
            "75% transit-access score + 25% parking-density score. "
            "The transit-access score combines stop density (30%), event-window departure frequency (20%), "
            "published dedicated-service evidence (35%), and pedestrian infrastructure (15%)."
        )
        st.markdown("**Sustainability score (0-100)**")
        st.markdown(
            "50% low-parking score + 30% transit-fleet electrification score + 20% pedestrian-infrastructure score. "
            "The low-parking score equals 100 minus the parking-density score."
        )
        st.caption(
            "Weights apply to normalized 0-100 component scores, not raw stop or facility counts. "
            "Parking uses facilities within 0.5 miles, not parking spaces. More parking raises access but "
            "lowers sustainability, treating parking availability as an access benefit and car dependence as "
            "a sustainability drawback. These are planning indices, not percentages of passengers served "
            "or measured emissions reductions. Missing components are omitted and remaining weights rescaled; "
            "access requires an eligible transit-stop-density input. Heat affects neither score."
        )

    st.markdown("##### What drives access and sustainability?")
    ranked = frame.dropna(subset=["gap_score"]).sort_values("gap_score", ascending=False)
    access_order = ranked["city"].tolist() + [
        city for city in frame["city"].tolist() if city not in set(ranked["city"])
    ]
    st.plotly_chart(
        access_sustainability_components_chart(frame, access_order),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_access_sustainability_components",
    )
    st.caption(
        "Inputs, left to right: transit-stop density, event-window frequency, and dedicated-service evidence "
        "(access); pedestrian infrastructure (both scores); parking-facility density within 0.5 miles "
        "(raises access but lowers sustainability); and fleet electrification (sustainability). "
        "Sorted by access score, matching the exact values table below."
    )
    parking_available = pd.to_numeric(frame.get("parking_count_1mi"), errors="coerce").notna()
    missing_parking = sorted(frame.loc[~parking_available, "city"].dropna().tolist())

    st.markdown("##### Evidence: Transit stop and parking density around each venue")
    st.plotly_chart(
        portfolio_access_density_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_access_density",
    )
    st.caption(
        "Each city's three solid bars on the left are transit stops (sourced from each city's live GTFS transit "
        "feed); the three lighter-shade bars on the right, in the same three ring colors, are real OpenStreetMap "
        "amenity=parking facilities. Parking bars are facility counts, not total spaces, since most OSM parking "
        "facilities have no recorded space count; hover for the real space count where one is tagged, plus "
        "nearest-stop distance and serving agencies. Sorted by transit stops within 1 mi, the more heavily "
        "weighted signal in the access score above, so the two metrics don't always agree on host order. Only "
        "the within-0.5-mile parking ring feeds the access and sustainability scores above - a lot a mile or two "
        "out doesn't meaningfully change the actual walk, so it's shown here for context but not counted further. "
        "Cities marked \"No parking data\" have no OSM parking snapshot at all - not a real zero. This is "
        "scheduled-service and OSM coverage, not walking-path safety, ADA accessibility, or verified event-day "
        "parking supply."
        + (f" Parking not yet available for: {', '.join(missing_parking)}." if missing_parking else "")
    )

    st.markdown("##### Evidence: Transit frequency and published-service evidence around each venue")
    st.plotly_chart(
        portfolio_frequency_benchmark_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="portfolio_frequency_benchmark",
    )
    st.caption(
        "The two other real inputs to transit access, alongside stop density above: frequency score (blue) is a "
        "log-scaled measure of real GTFS scheduled departures within the match-day event window near the venue - "
        "a throughput signal raw stop counts miss. Evidence tier (violet) is a 100/60 tier for whether a real, "
        "cited source documents a high-frequency dedicated rail/BRT connection (100) or a dedicated event "
        "shuttle/bus service without strong frequency evidence (60); hover for the specific cited fact. See the "
        "sourced evidence table below for the full citation per city."
    )
    with st.expander("Published-service evidence, city by city", icon=":material/fact_check:"):
        evidence_table = frame[
            [
                "city",
                "dedicated_service_tier",
                "dedicated_service_basis",
                "dedicated_service_publisher",
                "dedicated_service_source_url",
            ]
        ].copy()
        evidence_table["dedicated_service_tier"] = evidence_table["dedicated_service_tier"].map(
            {100: "High-frequency rail/BRT", 60: "Dedicated shuttle/bus"}
        )
        evidence_table.columns = ["City", "Tier", "Basis", "Publisher", "Source"]
        st.dataframe(
            evidence_table,
            hide_index=True,
            width="stretch",
            height=455,
            column_config={"Source": st.column_config.LinkColumn(display_text="Open source")},
        )

    with st.expander(
        "Exact first/last-mile values", icon=":material/table_chart:"
    ):
        st.dataframe(
            access_table(frame),
            hide_index=True,
            width="stretch",
            height=455,
        )
