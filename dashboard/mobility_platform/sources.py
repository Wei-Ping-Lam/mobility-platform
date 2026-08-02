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


def rice_source(dataset: str, detail: str | None = None) -> str:
    """Return a stable, user-facing citation to one supplied dataset."""

    source = f"{RICE_COLLECTION} / {dataset}"
    return f"{source} / {detail}" if detail else source
