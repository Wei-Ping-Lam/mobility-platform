"""Source-bounded event road overlays built offline from OpenStreetMap alignment."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import requests

from dashboard.pipeline.public.common import artifact_hash, write_json

OUTPUT = Path("data/snapshots/operations/road_closure_segments.json")
DEFINITIONS = {
    "Dallas": {
        "bbox": "-97.10,32.74,-97.079,32.757",
        "source": "https://www.dallasfwc26.com/dallas-2026/transportation-mobility/",
        "publisher": "North Texas FIFA World Cup Organizing Committee",
        "segments": [
            ("AT&T Way", "Cowboys Way", "East Randol Mill Road", "closed", "Closed on match days."),
            ("Cowboys Way", "North Collins Street", "AT&T Way", "closed", "Closed on match days."),
        ],
    },
    "San Francisco": {
        "bbox": "-121.986,37.397,-121.958,37.417",
        "source": "https://content.govdelivery.com/accounts/CASANTACLARA/bulletins/41ac963",
        "publisher": "City of Santa Clara",
        "segments": [
            ("Tasman Drive", "Great America Parkway", "Lick Mill Boulevard", "closed",
             "Expanded World Cup match-day Phase 2 closure; hours vary by match. Local access rules apply."),
        ],
    },
    "Miami": {
        "bbox": "-80.249,25.947,-80.223,25.965",
        "source": "https://www.miamidade.gov/global/release.page?Mduid_release=rel1781278551458970",
        "publisher": "Miami-Dade County",
        "segments": [
            ("Northwest 199th Street", "Northwest 27th Avenue", "Northwest 14th Court", "restricted",
             "Match-day vehicle restriction; only vehicles with valid FIFA parking credentials admitted."),
        ],
    },
}
ROAD_TYPES = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "residential", "unclassified",
    "service", "living_street", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link",
}


def parse_roads(payload: bytes) -> tuple[dict, list[dict]]:
    root = ET.fromstring(payload)
    nodes = {node.attrib["id"]: [float(node.attrib["lon"]), float(node.attrib["lat"])] for node in root.findall("node")}
    ways = []
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        if tags.get("highway") in ROAD_TYPES and tags.get("name"):
            ways.append({"id": way.attrib["id"], "name": tags["name"], "nodes": [n.attrib["ref"] for n in way.findall("nd")]})
    return nodes, ways


def road_segment(nodes: dict, ways: list[dict], road: str, start: str, end: str) -> tuple[list, list]:
    def matches(way, name):
        return way["name"].casefold().endswith(name.casefold())
    graph = nx.Graph()
    for way in ways:
        if matches(way, road):
            for u, v in zip(way["nodes"], way["nodes"][1:]):
                if u not in nodes or v not in nodes:
                    continue
                a, b = nodes[u], nodes[v]
                weight = math.hypot((a[0] - b[0]) * math.cos(math.radians(a[1])), a[1] - b[1])
                graph.add_edge(u, v, weight=weight, way_id=way["id"])
    boundaries = [
        {node for way in ways if matches(way, name) for node in way["nodes"]} & set(graph)
        for name in (start, end)
    ]
    paths = []
    for u in sorted(boundaries[0]):
        for v in sorted(boundaries[1]):
            if u != v and nx.has_path(graph, u, v):
                path = nx.shortest_path(graph, u, v, weight="weight")
                paths.append((nx.path_weight(graph, path, "weight"), path))
    if not paths:
        raise ValueError(f"No connected road geometry for {road}: {start} to {end}")
    path = min(paths)[1]
    way_ids = sorted({graph[u][v]["way_id"] for u, v in zip(path, path[1:])})
    return [nodes[node] for node in path], way_ids


def validate_snapshot(snapshot: dict) -> None:
    if snapshot.get("snapshot_kind") != "documented_event_road_segments" or not isinstance(snapshot.get("cities"), dict):
        raise ValueError("Unexpected road closure snapshot")
    if snapshot.get("artifact_sha256") != artifact_hash(snapshot):
        raise ValueError("Road closure snapshot hash mismatch")
    for rows in snapshot.get("cities", {}).values():
        for row in rows:
            if row.get("type") not in {"closed", "restricted"} or not row.get("source_url", "").startswith("https://"):
                raise ValueError("Road overlay needs a documented control type and source")
            points = row.get("coordinates", [])
            if len(points) < 2 or any(
                len(point) != 2 or not all(math.isfinite(value) for value in point)
                or not -180 <= point[0] <= 180 or not -90 <= point[1] <= 90 for point in points
            ):
                raise ValueError("Invalid road geometry")


def main() -> None:
    cities = {}
    for city, definition in DEFINITIONS.items():
        cache = Path("data/raw/roads") / (city.replace(" ", "_") + ".osm")
        if not cache.exists():
            response = requests.get(
                "https://api.openstreetmap.org/api/0.6/map", params={"bbox": definition["bbox"]},
                headers={"User-Agent": "Mobility-Readiness-Platform/0.3"}, timeout=40,
            )
            response.raise_for_status()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(response.content)
        nodes, ways = parse_roads(cache.read_bytes())
        records = []
        for road, start, end, kind, timing in definition["segments"]:
            coordinates, way_ids = road_segment(nodes, ways, road, start, end)
            records.append({
                "name": road, "from": start, "to": end, "type": kind,
                "timing": timing, "source_url": definition["source"], "publisher": definition["publisher"],
                "coordinates": coordinates, "osm_way_ids": way_ids,
                "geometry_source": "https://www.openstreetmap.org/copyright",
            })
        cities[city] = records
        print(city, [(row["name"], len(row["coordinates"])) for row in records], flush=True)
    snapshot = {
        "snapshot_kind": "documented_event_road_segments", "cities": cities,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "policy": "Published 2026 event plans, not live closures. OSM road alignment between named intersections, "
        "not surveyed barricade positions or lane-level geometry. Unmapped does not mean open.",
    }
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    validate_snapshot(snapshot)
    write_json(OUTPUT, snapshot)


if __name__ == "__main__":
    main()
