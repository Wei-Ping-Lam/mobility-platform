"""Canonical source names for supplied and supplemental evidence."""

from __future__ import annotations

RICE_COLLECTION = "Rice WC Hack"
RICE_DATASETS = {
    "store_visits": "store-visits-rice",
    "weather": "daily-weather-rice",
    "uhi": "urban-heat-index-rice",
    "poi": "core-poi-geometry-rice",
    "spend_origins": "spend-patterns-rice",
    "brand_spend": "daily-spend-brand-and-state-rice",
}
GTFS_SOURCE = "Supplemental pinned GTFS snapshot"
PUBLIC_SOURCE_CATALOG = {
    "fifa_schedule": {
        "publisher": "FIFA",
        "url": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums",
        "license": "reference-only; verify FIFA terms before redistribution",
    },
    "gtfs_specification": {
        "publisher": "MobilityData / GTFS",
        "url": "https://gtfs.org/documentation/overview/",
        "license": "Apache-2.0 specification",
    },
    "openstreetmap": {
        "publisher": "OpenStreetMap contributors",
        "url": "https://www.openstreetmap.org/copyright",
        "license": "ODbL 1.0",
    },
    "epa_moves": {
        "publisher": "U.S. Environmental Protection Agency",
        "url": "https://www.epa.gov/moves/latest-version-motor-vehicle-emission-simulator-moves",
        "license": "U.S. government work",
    },
    "fta_costs": {
        "publisher": "Federal Transit Administration",
        "url": "https://www.transit.dot.gov/capital-cost-database",
        "license": "U.S. government data",
    },
    "fta_ntd": {
        "publisher": "Federal Transit Administration",
        "url": "https://www.transit.dot.gov/ntd",
        "license": "U.S. government data",
    },
    "fhwa_active_transport": {
        "publisher": "FHWA / Pedestrian and Bicycle Information Center",
        "url": "https://www.pedbikeinfo.org/topics/more.php?topic=funding&type=resource",
        "license": "reference data; retain source attribution",
    },
}


def rice_source(dataset: str, detail: str | None = None) -> str:
    """Return a stable, user-facing citation to one supplied dataset."""

    source = f"{RICE_COLLECTION} / {dataset}"
    return f"{source} / {detail}" if detail else source
