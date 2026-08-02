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

GTFS_FEEDS = {
    "Atlanta": [
        GtfsFeedSource(
            agency="MARTA",
            url=(
                "https://files.mobilitydatabase.org/mdb-368/"
                "mdb-368-202604190110/mdb-368-202604190110.zip"
            ),
            publisher_url="https://www.itsmarta.com/google_transit_feed/google_transit.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="2b08551202fdd39ac672d07839fcfc9b702f776a7e31c56b64881191f67c5625",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
    "Boston": [
        GtfsFeedSource(
            agency="MBTA",
            url=(
                "https://files.mobilitydatabase.org/mdb-437/"
                "mdb-437-202606050042/mdb-437-202606050042.zip"
            ),
            publisher_url="https://cdn.mbta.com/MBTA_GTFS.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="cefab608c9d8361ade4ef3f17965cef73d1b4ad343fb9d23935c60b52410b0ce",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
    "Dallas": [
        GtfsFeedSource(
            agency="DART",
            url=(
                "https://files.mobilitydatabase.org/mdb-152/"
                "mdb-152-202606120106/mdb-152-202606120106.zip"
            ),
            publisher_url="https://www.dart.org/transitdata/latest/google_transit.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="46763ba650f462957ff6dc3a4ef163a9bc0122d25891db128fb1aa5e25eb63ef",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
    "Houston": [
        GtfsFeedSource(
            agency="METRO Houston",
            url=(
                "https://files.mobilitydatabase.org/mdb-2060/"
                "mdb-2060-202606090018/mdb-2060-202606090018.zip"
            ),
            publisher_url="https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip",
            archive_provider="MobilityDatabase",
            expected_sha256="ecfff77875bb2c84b8843839020263c0629d1c541670b4841d1a5bce4bac6d10",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
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
        GtfsFeedSource(
            agency="LA Metro Rail",
            url=(
                "https://gitlab.com/LACMTA/gtfs_rail/-/raw/"
                "fa5b72a4789bec68256e52bfce90fe9105db8111/gtfs_rail.zip"
            ),
            publisher_url="https://gitlab.com/LACMTA/gtfs_rail",
            archive_provider="LA Metro GitLab history",
            expected_sha256="e3584722c8b1f85f311eb7573e323c1baa81507b1bf3614f024bc23485add7e4",
            valid_from="2026-06-12",
            valid_to="2026-06-25",
        ),
        GtfsFeedSource(
            agency="LA Metro Rail",
            url=(
                "https://gitlab.com/LACMTA/gtfs_rail/-/raw/"
                "2940747aa442c9ff1c674a1b1035ad968ea7d6cf/gtfs_rail.zip"
            ),
            publisher_url="https://gitlab.com/LACMTA/gtfs_rail",
            archive_provider="LA Metro GitLab history",
            expected_sha256="13b6bd09aa4dfc88ce6b6f99fe64a2ff97c0b8b615df2ccd6c3e3560b8208567",
            valid_from="2026-06-28",
            valid_to="2026-07-10",
        ),
        GtfsFeedSource(
            agency="LA Metro Bus",
            url="https://gitlab.com/LACMTA/gtfs_bus/-/raw/043113f1/gtfs_bus.zip",
            publisher_url="https://gitlab.com/LACMTA/gtfs_bus",
            archive_provider="LA Metro GitLab history",
            expected_sha256="93275d4b50eb22afcfe64f3fe8fd918dfb5fa43600be2e267658e5f2719eda33",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        ),
    ],
    "Miami": [
        GtfsFeedSource(
            agency="Miami-Dade Transit",
            url=(
                "https://files.mobilitydatabase.org/mdb-331/"
                "mdb-331-202603260114/mdb-331-202603260114.zip"
            ),
            publisher_url="https://www.miamidade.gov/transit/googletransit/current/google_transit.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="bc195ae0ecfca9a8946d23f2e1deb8928a0730f8828ddb5ca41361042cfd9704",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
    "New York/NJ": [
        GtfsFeedSource(
            agency="NJ Transit Rail",
            url=(
                "https://files.mobilitydatabase.org/mdb-509/"
                "mdb-509-202606130055/mdb-509-202606130055.zip"
            ),
            publisher_url="https://www.njtransit.com/rail_data.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="0c32bc47fd62e7cc8932973b26336bad25b5f7a933f137a846e790a62279e5c8",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
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
    "San Francisco": [
        GtfsFeedSource(
            agency="VTA",
            url=(
                "https://files.mobilitydatabase.org/mdb-57/"
                "mdb-57-202606030001/mdb-57-202606030001.zip"
            ),
            publisher_url="https://gtfs.vta.org/gtfs_vta.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="e90abd9ef0936b0795075304b72da252d72df0e1200533372136c35d54e53380",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        )
    ],
    "Seattle": [
        GtfsFeedSource(
            agency="Sound Transit",
            url=(
                "https://files.mobilitydatabase.org/mdb-268/"
                "mdb-268-202606060017/mdb-268-202606060017.zip"
            ),
            publisher_url="https://gtfs.sound.obaweb.org/prod/40_gtfs.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="af2b2f6570fe9c8aa207843bcf11b3772f94b21df40fea54e1177af2672d504f",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        ),
        GtfsFeedSource(
            agency="King County Metro",
            url=(
                "https://files.mobilitydatabase.org/mdb-267/"
                "mdb-267-202606090115/mdb-267-202606090115.zip"
            ),
            publisher_url="https://metro.kingcounty.gov/GTFS/google_transit.zip",
            archive_provider="MobilityDatabase",
            expected_sha256="73bb8e90d82adbbfdaebde6e77ff730fc38bf51be099a15b642108fdbb7d12e5",
            valid_from="2026-06-11",
            valid_to="2026-07-19",
        ),
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
