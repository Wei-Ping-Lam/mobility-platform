from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.etl.build import _sha256
from dashboard.pipeline.etl.rice_enrichment import (
    _write_artifact,
    build_corridor_summary,
    build_movement_context,
    build_origin_flows,
    build_poi_points,
    build_uhi_grid,
)
from dashboard.pipeline.schemas.rice_enrichment import ARTIFACT_SCHEMAS, SOURCE_COLLECTION, validate_artifact

FIXTURE_SHA = "f" * 64


def _expected() -> dict[str, object]:
    path = Path(__file__).parent / "fixtures" / "rice_spatial_expected.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_uhi() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "MARKET": metadata["market"],
                "LATITUDE": float(metadata["lat"]) + offset,
                "LONGITUDE": float(metadata["lon"]) + offset,
                "UHI": 55.0 + index + point,
            }
            for index, metadata in enumerate(HOST_CITIES.values())
            for point, offset in enumerate((0.001, 0.015, 0.04))
        ]
    )


def _raw_poi() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "MARKET": metadata["market"],
                "LATITUDE": float(metadata["lat"]) + offset,
                "LONGITUDE": float(metadata["lon"]),
                "TOP_CATEGORY": "Food" if point % 2 == 0 else "Retail",
                "PLACEKEY": f"fixture-{index}-{point}",
            }
            for index, metadata in enumerate(HOST_CITIES.values())
            for point, offset in enumerate((0.001, 0.02, 0.05))
        ]
    )


def _raw_origins() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "MARKET": metadata["market"],
                "CUSTOMER_HOME_CITY": '{"Houston, TX": 8, "Portland, OR": 2}',
            }
            for metadata in HOST_CITIES.values()
        ]
    )


def _cached_visits() -> pd.DataFrame:
    rows = []
    for index, (city, metadata) in enumerate(HOST_CITIES.items()):
        for date, visits in (("2024-06-14", 100 + index), ("2024-06-15", 120 + index)):
            rows.append(
                {
                    "city": city,
                    "date": date,
                    "category": "Retail",
                    "daily_visits": visits,
                    "source_market": metadata["market"],
                    "evidence_status": "derived",
                }
            )
    return pd.DataFrame(rows)


def _frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    uhi = build_uhi_grid(_raw_uhi(), FIXTURE_SHA)
    poi = build_poi_points(_raw_poi(), FIXTURE_SHA)
    origins = build_origin_flows(_raw_origins(), FIXTURE_SHA)
    movement = build_movement_context(_cached_visits(), FIXTURE_SHA)
    corridors = build_corridor_summary(uhi, poi, origins, movement)
    return uhi, poi, origins, movement, corridors


def test_fixture_outputs_cover_all_cities_and_corridor_bands():
    expected = _expected()
    uhi, poi, origins, movement, corridors = _frames()
    cities = set(expected["cities"])

    for frame in (uhi, poi, origins, movement, corridors):
        assert set(frame["city"]) == cities
        assert set(frame["source_collection"]) == {expected["source_collection"]}
    assert len(corridors) == expected["corridor_rows"]
    assert set(corridors["distance_band"]) == set(expected["distance_bands"])
    assert set(uhi.loc[uhi["point_count"] == 0, "evidence_status"]).issubset({"unavailable"})


def test_spatial_coordinates_and_distances_are_valid():
    uhi, poi, origins, movement, corridors = _frames()

    for name, frame in (
        ("uhi_grid", uhi),
        ("poi_points", poi),
        ("origin_flows", origins),
        ("movement_context", movement),
        ("corridors", corridors),
    ):
        validate_artifact(name, frame)
        assert frame["venue_lat"].between(-90, 90).all()
        assert frame["venue_lon"].between(-180, 180).all()
    assert uhi["grid_lat"].between(-90, 90).all()
    assert uhi["grid_lon"].between(-180, 180).all()
    assert uhi["distance_mi"].between(0, 5).all()
    assert poi["point_lat"].between(-90, 90).all()
    assert poi["point_lon"].between(-180, 180).all()
    assert poi["distance_mi"].between(0, 5).all()


def test_schema_uses_commercial_context_not_event_demand_claims():
    schema_text = " ".join(
        column.lower()
        for schema in ARTIFACT_SCHEMAS.values()
        for column in schema.required_columns
    )
    assert "attendance" not in schema_text
    assert "spectator" not in schema_text
    assert "fan" not in schema_text


def test_combined_market_origin_and_movement_rows_remain_partial():
    origins = build_origin_flows(
        pd.DataFrame(
            {
                "MARKET": ["Dallas / Houston", "Los Angeles / SF Bay Area"],
                "CUSTOMER_HOME_CITY": ['{"Austin, TX": 10}', '{"Sacramento, CA": 6}'],
            }
        ),
        FIXTURE_SHA,
    )
    assert set(origins["city"]) == {"Dallas", "Houston", "Los Angeles", "San Francisco"}
    assert set(origins["evidence_status"]) == {"partial"}
    assert set(origins["allocation_method"]) == {"equal_split_combined_market"}
    assert set(origins["allocation_factor"]) == {0.5}
    assert origins.groupby("source_market")["customer_count"].sum().to_dict() == {
        "Dallas / Houston": 10.0,
        "Los Angeles / SF Bay Area": 6.0,
    }

    visits = pd.DataFrame(
        {
            "city": ["Dallas", "Houston"],
            "date": ["2024-06-14", "2024-06-14"],
            "category": ["Retail", "Retail"],
            "daily_visits": [50.0, 50.0],
            "source_market": ["Dallas / Houston", "Dallas / Houston"],
            "evidence_status": ["partial", "partial"],
        }
    )
    movement = build_movement_context(visits, FIXTURE_SHA)
    assert set(movement["evidence_status"]) == {"partial"}
    assert set(movement["allocation_method"]) == {"equal_split_combined_market"}
    assert set(movement["allocation_factor"]) == {0.5}


def test_deterministic_sorting_and_parquet_hashes(tmp_path):
    frames = _frames()
    names = ("uhi_grid", "poi_points", "origin_flows", "movement_context", "corridors")
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    for name, frame in zip(names, frames):
        shuffled = frame.sample(frac=1, random_state=37).reset_index(drop=True)
        first_path, first_hash = _write_artifact(name, frame, first_root)
        second_path, second_hash = _write_artifact(name, shuffled, second_root)
        assert first_hash == second_hash
        assert first_hash == _sha256(first_path) == _sha256(second_path)
        assert list(pd.read_parquet(first_path).columns) == list(ARTIFACT_SCHEMAS[name].required_columns)


def test_origin_shares_sum_to_one_for_each_city():
    origins = build_origin_flows(_raw_origins(), FIXTURE_SHA)
    shares = origins.groupby("city")["city_customer_share"].sum()
    assert shares.round(12).eq(1.0).all()
    assert set(origins["source_collection"]) == {SOURCE_COLLECTION}
