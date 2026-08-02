"""Refresh and validate compact, pinned OSM walking-network evidence."""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx
import osmnx as ox
import pandas as pd
from shapely.geometry import MultiPoint, mapping

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash, base_snapshot, sha256_bytes, validate_source, write_json
from dashboard.pipeline.public.loaders import load_gtfs_snapshot

OSM_URL = "https://www.openstreetmap.org/copyright"
RADIUS_METERS = 5.0 * 1609.344
WALK_SPEED_MPS = 1.34
RETRIES = 3


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    value = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(value))


def _isochrone(graph: nx.MultiDiGraph, venue_node: int, minutes: int) -> dict[str, Any]:
    reachable = nx.ego_graph(graph.to_undirected(), venue_node, radius=minutes * 60 * WALK_SPEED_MPS, distance="length")
    points = [MultiPoint([(float(data["x"]), float(data["y"]))]) for _, data in reachable.nodes(data=True)]
    merged = MultiPoint([point.geoms[0] for point in points]).buffer(0.00025).convex_hull
    return {"minutes": minutes, "walking_speed_mps": WALK_SPEED_MPS, "geometry": mapping(merged)}


def _tag_coverage(graph: nx.MultiDiGraph) -> tuple[float, float]:
    edge_lengths = []
    tagged_lengths = []
    for _, _, data in graph.edges(data=True):
        length = float(data.get("length") or 0)
        edge_lengths.append(length)
        if data.get("sidewalk") not in (None, "", "no", "none"):
            tagged_lengths.append(length)
    sidewalk = 100 * sum(tagged_lengths) / sum(edge_lengths) if sum(edge_lengths) else 0.0
    nodes = list(graph.nodes(data=True))
    crossings = sum(
        1
        for _, data in nodes
        if data.get("highway") == "crossing" or data.get("crossing") not in (None, "", "no")
    )
    crossing = 100 * crossings / len(nodes) if nodes else 0.0
    return round(sidewalk, 2), round(crossing, 2)


def _nearest_node(graph: nx.MultiDiGraph, lat: float, lon: float) -> Any:
    """Find a nearest node without OSMnx's optional scikit-learn dependency."""

    return min(
        graph.nodes,
        key=lambda node: (
            (float(graph.nodes[node]["y"]) - lat) ** 2
            + ((float(graph.nodes[node]["x"]) - lon) * math.cos(math.radians(lat))) ** 2
        ),
    )


def _nearest_event_stop(gtfs_city: dict[str, Any]) -> dict[str, Any] | None:
    eligible = [
        row
        for row in gtfs_city.get("stop_points_2mi", [])
        if row.get("lat") is not None
        and row.get("lon") is not None
        and str(row.get("route") or "") != "Route unavailable"
    ]
    return min(eligible, key=lambda row: float(row.get("distance_mi", math.inf)), default=None)


def _route_heat(
    city: str,
    coordinates: list[list[float]],
    uhi: pd.DataFrame,
    weather: pd.DataFrame,
) -> tuple[float | None, float | None]:
    city_uhi = uhi[uhi["city"] == city].copy() if not uhi.empty and "city" in uhi else pd.DataFrame()
    if city_uhi.empty or not coordinates:
        return None, None
    lat_col = "grid_lat" if "grid_lat" in city_uhi else "lat"
    lon_col = "grid_lon" if "grid_lon" in city_uhi else "lon"
    values = []
    for lon, lat in coordinates:
        distance = (pd.to_numeric(city_uhi[lat_col], errors="coerce") - lat) ** 2 + (pd.to_numeric(city_uhi[lon_col], errors="coerce") - lon) ** 2
        if distance.notna().any():
            value = pd.to_numeric(pd.Series([city_uhi.loc[distance.idxmin(), "avg_uhi"]]), errors="coerce").iloc[0]
            if pd.notna(value):
                values.append(float(value))
    route_uhi = float(pd.Series(values).mean()) if values else None
    city_weather = weather[weather["city"] == city].copy() if not weather.empty and "city" in weather else pd.DataFrame()
    ambient = None
    if not city_weather.empty and "max_temp_c" in city_weather:
        dates = pd.to_datetime(city_weather.get("date"), errors="coerce")
        summer = city_weather[dates.dt.month.isin([6, 7])]
        temperatures = pd.to_numeric(summer["max_temp_c"], errors="coerce").dropna()
        ambient = float(temperatures.quantile(0.9)) if not temperatures.empty else None
    return (round(route_uhi, 2) if route_uhi is not None else None, round(ambient + route_uhi, 2) if ambient is not None and route_uhi is not None else None)


def validate_walking_city(row: dict[str, Any]) -> None:
    straight = row.get("straight_distance_m")
    network = row.get("network_distance_m")
    if straight is not None or network is not None:
        if straight is None or network is None or float(straight) < 0 or float(network) < float(straight) - 1:
            raise ValueError(f"Network distance invariant failed for {row.get('city')}")
        expected = float(network) / float(straight) if float(straight) else 1.0
        if abs(float(row["detour_ratio"]) - expected) > 0.001:
            raise ValueError(f"Detour ratio is inconsistent for {row.get('city')}")
    for field in ("sidewalk_tag_coverage_pct", "crossing_tag_coverage_pct"):
        if not 0 <= float(row.get(field, 0)) <= 100:
            raise ValueError(f"Invalid {field} for {row.get('city')}")
    if row.get("snapshot_kind") == "fixture":
        raise ValueError("Tracked walking evidence cannot be a fixture")


def _fetch_graph(city: str, venue: dict[str, Any], raw_root: Path) -> tuple[nx.MultiDiGraph, Path]:
    slug = "".join(character.lower() if character.isalnum() else "_" for character in city).strip("_")
    graph_path = raw_root / f"{slug}.graphml"
    if graph_path.exists():
        return ox.io.load_graphml(filepath=graph_path), graph_path
    error: Exception | None = None
    for attempt in range(RETRIES):
        try:
            graph = ox.graph.graph_from_point(
                (float(venue["lat"]), float(venue["lon"])),
                dist=RADIUS_METERS,
                network_type="walk",
                simplify=True,
                retain_all=False,
            )
            graph_path.parent.mkdir(parents=True, exist_ok=True)
            ox.io.save_graphml(graph, filepath=graph_path)
            return graph, graph_path
        except Exception as exc:  # OSMnx wraps network and graph errors across several libraries.
            error = exc
            if attempt < RETRIES - 1:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"OSM refresh failed after {RETRIES} attempts: {error}") from error


def _city_snapshot(
    city: str,
    venue: dict[str, Any],
    gtfs_city: dict[str, Any],
    raw_root: Path,
    retrieved_at: str,
    uhi: pd.DataFrame,
    weather: pd.DataFrame,
) -> dict[str, Any]:
    query = {"center": [venue["lat"], venue["lon"]], "distance_m": RADIUS_METERS, "network_type": "walk"}
    try:
        graph, graph_path = _fetch_graph(city, venue, raw_root)
        graph_hash = sha256_bytes(graph_path.read_bytes())
        venue_node = _nearest_node(graph, float(venue["lat"]), float(venue["lon"]))
        component_nodes = nx.node_connected_component(graph.to_undirected(), venue_node)
        graph = graph.subgraph(component_nodes).copy()
        stop = _nearest_event_stop(gtfs_city)
        route_coordinates: list[list[float]] = []
        straight = network = detour = None
        target = None
        if stop:
            stop_node = _nearest_node(graph, float(stop["lat"]), float(stop["lon"]))
            route = nx.shortest_path(graph, venue_node, stop_node, weight="length")
            route_coordinates = [[round(float(graph.nodes[node]["x"]), 6), round(float(graph.nodes[node]["y"]), 6)] for node in route]
            raw_network = sum(float(graph.edges[left, right, min(graph[left][right], key=lambda key: float(graph[left][right][key].get("length") or math.inf))].get("length") or 0) for left, right in zip(route, route[1:]))
            straight = _haversine_m(float(venue["lat"]), float(venue["lon"]), float(stop["lat"]), float(stop["lon"]))
            network = max(raw_network, straight)
            detour = network / straight if straight else 1.0
            target = {key: stop.get(key) for key in ("stop_id", "name", "lat", "lon", "agency", "route", "status")}
        sidewalk, crossing = _tag_coverage(graph)
        route_uhi, route_heat = _route_heat(city, route_coordinates, uhi, weather)
        status = "derived" if route_coordinates else "partial"
        source = {
            "source": "OpenStreetMap five-mile walking-network extract",
            "url": OSM_URL,
            "publisher": "OpenStreetMap contributors",
            "retrieved_at_utc": retrieved_at,
            "version": f"OSMnx {ox.__version__}",
            "sha256": graph_hash,
            "license": "Open Database License (ODbL)",
            "coverage_start": None,
            "coverage_end": None,
            "status": "derived",
            "hash_scope": "Local GraphML extract bytes",
            "notes": "Network planning evidence; sidewalk/crossing tags are incomplete and do not certify accessibility.",
        }
        row = {
            "city": city,
            "venue": venue["venue"],
            "venue_lat": venue["lat"],
            "venue_lon": venue["lon"],
            "snapshot_kind": "osm_walking_network",
            "schema_version": "1.0.0",
            "status": status,
            "query": query,
            "graph_nodes": graph.number_of_nodes(),
            "graph_edges": graph.number_of_edges(),
            "connected_component_nodes": len(component_nodes),
            "target_kind": "nearest event-relevant GTFS stop" if stop else "unavailable without event-relevant GTFS stop",
            "target_stop": target,
            "straight_distance_m": round(straight, 1) if straight is not None else None,
            "network_distance_m": round(network, 1) if network is not None else None,
            "detour_ratio": round(detour, 3) if detour is not None else None,
            "route_geometry": {"type": "LineString", "coordinates": route_coordinates} if route_coordinates else None,
            "isochrones": [_isochrone(graph, venue_node, 15), _isochrone(graph, venue_node, 30)],
            "sidewalk_tag_coverage_pct": sidewalk,
            "crossing_tag_coverage_pct": crossing,
            "route_uhi_c_above_rural": route_uhi,
            "route_heat_exposure_c": route_heat,
            "accessibility_status": "not_measured",
            "source": source,
        }
        validate_walking_city(row)
        return row
    except Exception as exc:
        descriptor = json.dumps({"city": city, "query": query, "error": str(exc)[:500]}, sort_keys=True).encode()
        return {
            "city": city,
            "venue": venue["venue"],
            "venue_lat": venue["lat"],
            "venue_lon": venue["lon"],
            "snapshot_kind": "osm_walking_network",
            "schema_version": "1.0.0",
            "status": "unavailable",
            "query": query,
            "straight_distance_m": None,
            "network_distance_m": None,
            "detour_ratio": None,
            "route_geometry": None,
            "isochrones": [],
            "sidewalk_tag_coverage_pct": 0.0,
            "crossing_tag_coverage_pct": 0.0,
            "route_uhi_c_above_rural": None,
            "route_heat_exposure_c": None,
            "accessibility_status": "not_measured",
            "error": str(exc)[:500],
            "source": {
                "source": "OpenStreetMap walking-network refresh attempt",
                "url": OSM_URL,
                "publisher": "OpenStreetMap contributors",
                "retrieved_at_utc": retrieved_at,
                "version": f"OSMnx {ox.__version__}",
                "sha256": sha256_bytes(descriptor),
                "license": "Open Database License (ODbL)",
                "status": "unavailable",
                "notes": "No geometry is published for this failed refresh.",
            },
        }


def build_snapshot(
    gtfs_path: Path,
    raw_root: Path,
    cache_root: Path,
    uhi_path: Path,
    weather_path: Path,
) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(cache_root)
    ox.settings.requests_timeout = 180
    gtfs = load_gtfs_snapshot(gtfs_path)
    uhi = pd.read_parquet(uhi_path) if uhi_path.exists() else pd.DataFrame()
    weather = pd.read_parquet(weather_path) if weather_path.exists() else pd.DataFrame()
    cities = {}
    for city, venue in HOST_CITIES.items():
        print(json.dumps({"city": city, "phase": "walking_network_refresh"}), flush=True)
        cities[city] = _city_snapshot(city, venue, gtfs.get("cities", {}).get(city, {}), raw_root, retrieved_at, uhi, weather)
        print(json.dumps({"city": city, "status": cities[city]["status"]}), flush=True)
    city_hashes = {city: row["source"]["sha256"] for city, row in cities.items()}
    source = {
        "source": "OpenStreetMap five-mile walking-network extracts",
        "url": OSM_URL,
        "publisher": "OpenStreetMap contributors",
        "retrieved_at_utc": retrieved_at,
        "version": f"OSMnx {ox.__version__}",
        "sha256": sha256_bytes(json.dumps(city_hashes, sort_keys=True).encode()),
        "license": "Open Database License (ODbL)",
        "status": "derived" if all(row["status"] != "unavailable" for row in cities.values()) else "partial",
        "notes": "Hashes identify local GraphML extracts; compact derived geometry is tracked.",
    }
    snapshot = base_snapshot("osm_walking_networks", retrieved_at)
    snapshot.update(
        {
            "schema_version": "1.0.0",
            "status": source["status"],
            "source": source,
            "radius_miles": 5.0,
            "cities": cities,
            "policy": {
                "runtime": "cache-only; no OSM request during dashboard use",
                "ada": "Missing OSM tags remain unknown and never imply ADA compliance",
                "distance": "Network paths are planning evidence and include a straight-line lower-bound guard",
            },
        }
    )
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Walking snapshot contract version mismatch")
    if snapshot.get("snapshot_kind") != "osm_walking_networks":
        raise ValueError("Walking snapshot must be graph-derived, not a fixture")
    validate_source(snapshot["source"])
    cities = snapshot.get("cities")
    if not isinstance(cities, dict) or set(cities) != set(HOST_CITIES):
        raise ValueError("Walking snapshot must contain exactly all 11 U.S. host cities")
    for row in cities.values():
        validate_walking_city(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Fetch all 11 five-mile OSM walking graphs")
    mode.add_argument("--validate", type=Path, help="Validate an existing compact graph-derived snapshot")
    parser.add_argument("--gtfs", type=Path, default=Path("data/snapshots/gtfs/gtfs_venue_access.json"))
    parser.add_argument("--raw-root", type=Path, default=Path("data/snapshots/osm/raw"))
    parser.add_argument("--cache-root", type=Path, default=Path("data/osmnx-cache"))
    parser.add_argument("--uhi", type=Path, default=Path("dashboard/cache/rice_spatial_uhi_grid.parquet"))
    parser.add_argument("--weather", type=Path, default=Path("dashboard/cache/weather_city_daily.parquet"))
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/osm/walking_networks.json"))
    args = parser.parse_args()
    snapshot = (
        build_snapshot(args.gtfs, args.raw_root, args.cache_root, args.uhi, args.weather)
        if args.refresh
        else json.loads(args.validate.read_text(encoding="utf-8"))
    )
    validate_snapshot(snapshot)
    digest = write_json(args.output, snapshot) if args.refresh else sha256_bytes(args.validate.read_bytes())
    print(json.dumps({"status": snapshot["status"], "cities": len(snapshot["cities"]), "sha256": digest}))


if __name__ == "__main__":
    main()
