"""Pinned GTFS feed registry and scenario capacity assumptions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GtfsFeedSource:
    """One agency feed or immutable archive assigned to an event-date window."""

    agency: str
    url: str
    publisher_url: str | None = None
    archive_provider: str | None = None
    expected_sha256: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None


def _live(agency: str, url: str) -> GtfsFeedSource:
    return GtfsFeedSource(agency=agency, url=url, publisher_url=url)

GTFS_FEEDS = {
    "Atlanta": [_live("MARTA", "https://www.itsmarta.com/google_transit_feed/google_transit.zip")],
    "Boston": [_live("MBTA", "https://cdn.mbta.com/MBTA_GTFS.zip")],
    "Dallas": [_live("DART", "https://www.dart.org/transitdata/latest/google_transit.zip")],
    "Houston": [_live("METRO Houston", "https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip")],
    "Kansas City": [
        GtfsFeedSource(
            agency="RideKC/KCATA",
            url=(
                "https://files.mobilitydatabase.org/mdb-187/"
                "mdb-187-202607020106/mdb-187-202607020106.zip"
            ),
            publisher_url="https://www.kcata.org/transit_data/access_gtdf",
            archive_provider="MobilityDatabase",
            expected_sha256="2a49be56567391508e8ac456d09e165564ccf46ddc3cb0ffb38c06f0d1ec13e7",
            valid_from="2026-06-07",
            valid_to="2026-07-11",
        )
    ],
    "Los Angeles": [
        _live("LA Metro Rail", "https://gitlab.com/LACMTA/gtfs_rail/raw/master/gtfs_rail.zip"),
        _live("LA Metro Bus", "https://gitlab.com/LACMTA/gtfs_bus/-/raw/master/gtfs_bus.zip"),
    ],
    "Miami": [_live("Miami-Dade Transit", "https://www.miamidade.gov/transit/googletransit/current/google_transit.zip")],
    "New York/NJ": [_live("NJ Transit Rail", "https://www.njtransit.com/rail_data.zip")],
    "Philadelphia": [
        GtfsFeedSource(
            agency="SEPTA",
            url="https://github.com/septadev/GTFS/releases/download/v202606141/gtfs_public.zip",
            publisher_url="https://www3.septa.org/developer/",
            archive_provider="SEPTA GitHub releases",
            expected_sha256="aea11dbc7a53ed534658f2d7147b1e1569aaf900f7c523e43d327af5ae694078",
            valid_from="2026-06-14",
            valid_to="2026-06-27",
        ),
        GtfsFeedSource(
            agency="SEPTA",
            url="https://github.com/septadev/GTFS/releases/download/v202606282/gtfs_public.zip",
            publisher_url="https://www3.septa.org/developer/",
            archive_provider="SEPTA GitHub releases",
            expected_sha256="c343b768a50670ebf9dab965df30fcc88aa8cf7069f3ed5aa103d21623ad8a64",
            valid_from="2026-06-28",
            valid_to="2026-07-19",
        ),
    ],
    "San Francisco": [_live("VTA", "https://gtfs.vta.org/gtfs_vta.zip")],
    "Seattle": [
        _live("Sound Transit", "https://gtfs.sound.obaweb.org/prod/40_gtfs.zip"),
        _live("King County Metro", "https://metro.kingcounty.gov/GTFS/google_transit.zip"),
    ],
}

# Passengers per scheduled vehicle, deliberately represented as planning ranges.
MODE_CAPACITY_RANGES = {
    0: {"mode": "tram_light_rail", "low": 120, "base": 180, "high": 250},
    1: {"mode": "subway_metro", "low": 600, "base": 900, "high": 1200},
    2: {"mode": "rail", "low": 500, "base": 800, "high": 1200},
    3: {"mode": "bus", "low": 40, "base": 55, "high": 80},
    4: {"mode": "ferry", "low": 150, "base": 300, "high": 600},
    5: {"mode": "cable_tram", "low": 40, "base": 70, "high": 100},
    6: {"mode": "aerial_lift", "low": 20, "base": 40, "high": 80},
    7: {"mode": "funicular", "low": 60, "base": 100, "high": 180},
    11: {"mode": "trolleybus", "low": 40, "base": 55, "high": 80},
    12: {"mode": "monorail", "low": 150, "base": 250, "high": 400},
}
