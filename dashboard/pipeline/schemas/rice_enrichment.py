"""Schemas and validation rules for compact Rice enrichment artifacts."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

SOURCE_COLLECTION = "Rice WC Hack"
SPATIAL_LIMITATION = (
    "Source coordinates may be spatially jittered or represent POI centroids; "
    "use for area-level planning, not entrance-level or pedestrian-network routing."
)


@dataclass(frozen=True)
class ArtifactSchema:
    filename: str
    required_columns: tuple[str, ...]
    sort_columns: tuple[str, ...]


ARTIFACT_SCHEMAS: dict[str, ArtifactSchema] = {
    "uhi_grid": ArtifactSchema(
        filename="rice_spatial_uhi_grid.parquet",
        required_columns=(
            "city",
            "venue",
            "venue_lat",
            "venue_lon",
            "grid_lat",
            "grid_lon",
            "distance_mi",
            "distance_band",
            "avg_uhi",
            "p90_uhi",
            "max_uhi",
            "point_count",
            "source_collection",
            "source_dataset",
            "source_market",
            "source_sha256",
            "evidence_status",
            "allocation_method",
            "allocation_factor",
            "spatial_limitations",
        ),
        sort_columns=("city", "distance_band", "grid_lat", "grid_lon", "source_market"),
    ),
    "poi_points": ArtifactSchema(
        filename="rice_spatial_poi_points.parquet",
        required_columns=(
            "city",
            "venue",
            "venue_lat",
            "venue_lon",
            "placekey",
            "point_lat",
            "point_lon",
            "distance_mi",
            "distance_band",
            "category",
            "source_collection",
            "source_dataset",
            "source_market",
            "source_sha256",
            "evidence_status",
            "allocation_method",
            "allocation_factor",
            "spatial_limitations",
        ),
        sort_columns=("city", "distance_band", "distance_mi", "placekey", "source_market"),
    ),
    "origin_flows": ArtifactSchema(
        filename="rice_spatial_origin_flows.parquet",
        required_columns=(
            "city",
            "venue_lat",
            "venue_lon",
            "home_state",
            "customer_count",
            "city_customer_share",
            "state_rank",
            "source_collection",
            "source_dataset",
            "source_market",
            "source_sha256",
            "evidence_status",
            "allocation_method",
            "allocation_factor",
            "claim_scope",
        ),
        sort_columns=("city", "state_rank", "home_state", "source_market"),
    ),
    "movement_context": ArtifactSchema(
        filename="rice_spatial_movement_context.parquet",
        required_columns=(
            "city",
            "venue_lat",
            "venue_lon",
            "month",
            "weekday",
            "weekday_name",
            "category",
            "mean_daily_visits",
            "p10_daily_visits",
            "p90_daily_visits",
            "observation_days",
            "source_collection",
            "source_dataset",
            "source_market",
            "source_sha256",
            "evidence_status",
            "allocation_method",
            "allocation_factor",
            "claim_scope",
        ),
        sort_columns=("city", "month", "weekday", "category", "source_market"),
    ),
    "corridors": ArtifactSchema(
        filename="venue_corridor_summary.parquet",
        required_columns=(
            "city",
            "venue",
            "venue_lat",
            "venue_lon",
            "distance_band",
            "band_min_mi",
            "band_max_mi",
            "uhi_point_count",
            "avg_uhi",
            "p90_uhi",
            "poi_count",
            "poi_category_count",
            "top_poi_categories",
            "top_home_states",
            "peak_commercial_month",
            "peak_commercial_weekday",
            "source_collection",
            "source_datasets",
            "source_markets",
            "source_sha256",
            "evidence_status",
            "allocation_method",
            "allocation_factor",
            "spatial_limitations",
            "claim_scope",
        ),
        sort_columns=("city", "band_min_mi"),
    ),
}


def validate_artifact(name: str, frame: pd.DataFrame, *, require_all_cities: set[str] | None = None) -> None:
    """Raise a useful error when an enrichment frame violates its frozen schema."""

    schema = ARTIFACT_SCHEMAS[name]
    missing = sorted(set(schema.required_columns).difference(frame.columns))
    if missing:
        raise ValueError(f"{schema.filename}: missing columns: {', '.join(missing)}")
    if require_all_cities is not None:
        absent = sorted(require_all_cities.difference(set(frame["city"].dropna().astype(str))))
        if absent:
            raise ValueError(f"{schema.filename}: missing cities: {', '.join(absent)}")
    if "evidence_status" in frame and not set(frame["evidence_status"]).issubset({"derived", "partial", "unavailable"}):
        raise ValueError(f"{schema.filename}: invalid evidence status")
    for latitude, longitude in (("venue_lat", "venue_lon"), ("grid_lat", "grid_lon"), ("point_lat", "point_lon")):
        if latitude not in frame or longitude not in frame:
            continue
        lat = pd.to_numeric(frame[latitude], errors="coerce").dropna()
        lon = pd.to_numeric(frame[longitude], errors="coerce").dropna()
        if not lat.between(-90, 90).all() or not lon.between(-180, 180).all():
            raise ValueError(f"{schema.filename}: coordinates outside valid ranges")
