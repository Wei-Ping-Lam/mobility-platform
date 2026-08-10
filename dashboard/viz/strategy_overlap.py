"""Focused maps showing where strategy evidence overlaps around a venue."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import plotly.graph_objects as go

from dashboard.viz.style import COLORS, style_map

HALF_MILE_METERS = 804.672


def _number(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _line_coordinates(records: object) -> tuple[list[float | None], list[float | None], list[str | None]]:
    latitudes: list[float | None] = []
    longitudes: list[float | None] = []
    labels: list[str | None] = []
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        return latitudes, longitudes, labels
    for record in records:
        if not isinstance(record, Mapping):
            continue
        coordinates = record.get("coordinates") or record.get("geometry")
        if isinstance(coordinates, Mapping):
            coordinates = coordinates.get("coordinates")
        if not isinstance(coordinates, Sequence) or isinstance(coordinates, (str, bytes)):
            continue
        label = str(
            record.get("name")
            or record.get("route_name")
            or record.get("route_id")
            or (f"{record.get('minutes')}-minute walking contour" if record.get("minutes") else "Evidence geometry")
        )
        for coordinate in coordinates:
            if not isinstance(coordinate, Sequence) or len(coordinate) < 2:
                continue
            lon = _number(coordinate[0])
            lat = _number(coordinate[1])
            if lat is None or lon is None:
                continue
            latitudes.append(lat)
            longitudes.append(lon)
            labels.append(label)
        if latitudes and latitudes[-1] is not None:
            latitudes.append(None)
            longitudes.append(None)
            labels.append(None)
    return latitudes, longitudes, labels


def _circle(latitude: float, longitude: float, radius_m: float) -> tuple[list[float], list[float]]:
    earth_radius_m = 6_371_008.8
    angular = radius_m / earth_radius_m
    latitude_rad = math.radians(latitude)
    latitudes: list[float] = []
    longitudes: list[float] = []
    for step in range(73):
        bearing = math.radians(step * 5)
        point_lat = math.asin(
            math.sin(latitude_rad) * math.cos(angular)
            + math.cos(latitude_rad) * math.sin(angular) * math.cos(bearing)
        )
        point_lon = math.radians(longitude) + math.atan2(
            math.sin(bearing) * math.sin(angular) * math.cos(latitude_rad),
            math.cos(angular) - math.sin(latitude_rad) * math.sin(point_lat),
        )
        latitudes.append(math.degrees(point_lat))
        longitudes.append(math.degrees(point_lon))
    return latitudes, longitudes


def access_overlap_map(venue: Mapping[str, Any], layers: Mapping[str, Any]) -> go.Figure:
    """Map the exact evidence layers used to interpret venue-side access."""

    venue_lat = _number(venue.get("lat"))
    venue_lon = _number(venue.get("lon"))
    figure = go.Figure()
    if venue_lat is None or venue_lon is None:
        return style_map(figure, 390, zoom=3, lat=38.5, lon=-96)

    circle_lat, circle_lon = _circle(venue_lat, venue_lon, HALF_MILE_METERS)
    figure.add_trace(
        go.Scattermap(
            lat=circle_lat,
            lon=circle_lon,
            mode="lines",
            line=dict(color=COLORS["amber"], width=3),
            name="Half-mile service screen",
            hovertemplate="Half-mile scheduled-service screen<extra></extra>",
        )
    )

    route_lat, route_lon, route_labels = _line_coordinates(layers.get("gtfs_routes", []))
    if route_lat:
        figure.add_trace(
            go.Scattermap(
                lat=route_lat,
                lon=route_lon,
                mode="lines",
                line=dict(color=COLORS["violet"], width=1.5),
                name="Event-valid GTFS routes",
                text=route_labels,
                hovertemplate="%{text}<extra></extra>",
                connectgaps=False,
            )
        )

    stops = [item for item in layers.get("gtfs", []) if isinstance(item, Mapping)]
    stop_points = [
        (item, _number(item.get("lat")), _number(item.get("lon")))
        for item in stops
    ]
    stop_points = [(item, lat, lon) for item, lat, lon in stop_points if lat is not None and lon is not None]
    if stop_points:
        figure.add_trace(
            go.Scattermap(
                lat=[lat for _, lat, _ in stop_points],
                lon=[lon for _, _, lon in stop_points],
                mode="markers",
                marker=dict(size=8, color=COLORS["blue"], opacity=0.78),
                name="Event-relevant stops",
                text=[str(item.get("name") or "GTFS stop") for item, _, _ in stop_points],
                hovertemplate="%{text}<extra></extra>",
            )
        )

    walk_lat, walk_lon, walk_labels = _line_coordinates(layers.get("walk", []))
    if walk_lat:
        figure.add_trace(
            go.Scattermap(
                lat=walk_lat,
                lon=walk_lon,
                mode="lines",
                line=dict(color=COLORS["teal"], width=2.5),
                name="Walking evidence",
                text=walk_labels,
                hovertemplate="%{text}<extra></extra>",
                connectgaps=False,
            )
        )

    figure.add_trace(
        go.Scattermap(
            lat=[venue_lat],
            lon=[venue_lon],
            mode="markers",
            marker=dict(size=18, color=COLORS["ink"]),
            name="Venue",
            text=[str(venue.get("name") or "Venue")],
            hovertemplate="%{text}<extra></extra>",
        )
    )
    return style_map(figure, 390, zoom=11.2, lat=venue_lat, lon=venue_lon)


def _hub_records(plan: Mapping[str, Any], published_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    hubs: list[dict[str, Any]] = []
    published_hubs = published_plan.get("transfer_hubs", [])
    if isinstance(published_hubs, Sequence) and not isinstance(published_hubs, (str, bytes)):
        hubs.extend(dict(hub) for hub in published_hubs if isinstance(hub, Mapping))
    selected = {
        "name": plan.get("regional_hub_name"),
        "lat": plan.get("regional_hub_lat"),
        "lon": plan.get("regional_hub_lon"),
        "role": "engine-selected transfer anchor",
        "status": plan.get("regional_hub_status") or "candidate",
    }
    if selected["lat"] is not None and selected["lon"] is not None:
        selected_key = (str(selected["name"]), _number(selected["lat"]), _number(selected["lon"]))
        existing = {
            (str(hub.get("name")), _number(hub.get("lat")), _number(hub.get("lon")))
            for hub in hubs
        }
        if selected_key not in existing:
            hubs.append(selected)
    return hubs


def operating_overlap_map(
    plan: Mapping[str, Any],
    venue: Mapping[str, Any],
    published_plan: Mapping[str, Any] | None = None,
) -> go.Figure:
    """Map the venue-to-hub structure, separating published from candidate locations."""

    venue_lat = _number(venue.get("lat"))
    venue_lon = _number(venue.get("lon"))
    figure = go.Figure()
    if venue_lat is None or venue_lon is None:
        return style_map(figure, 390, zoom=3, lat=38.5, lon=-96)

    hubs = _hub_records(plan, published_plan or {})
    valid_hubs = [
        (hub, _number(hub.get("lat")), _number(hub.get("lon")))
        for hub in hubs
    ]
    valid_hubs = [(hub, lat, lon) for hub, lat, lon in valid_hubs if lat is not None and lon is not None]

    if valid_hubs:
        link_lat: list[float | None] = []
        link_lon: list[float | None] = []
        link_text: list[str | None] = []
        for hub, lat, lon in valid_hubs:
            label = f"Schematic link: {hub.get('name') or 'hub'} to venue"
            link_lat.extend([lat, venue_lat, None])
            link_lon.extend([lon, venue_lon, None])
            link_text.extend([label, label, None])
        figure.add_trace(
            go.Scattermap(
                lat=link_lat,
                lon=link_lon,
                mode="lines",
                line=dict(color=COLORS["slate"], width=2),
                name="Schematic transfer link",
                text=link_text,
                hovertemplate="%{text}<extra></extra>",
                connectgaps=False,
            )
        )

        for status, label, color in (
            ("observed", "Published hub", COLORS["blue"]),
            ("published", "Published hub", COLORS["blue"]),
            ("candidate", "Engine candidate hub", COLORS["amber"]),
        ):
            subset = [(hub, lat, lon) for hub, lat, lon in valid_hubs if str(hub.get("status")) == status]
            if not subset:
                continue
            figure.add_trace(
                go.Scattermap(
                    lat=[lat for _, lat, _ in subset],
                    lon=[lon for _, _, lon in subset],
                    mode="markers",
                    marker=dict(size=15, color=color),
                    name=label,
                    text=[
                        f"{hub.get('name') or 'Hub'} - {hub.get('role') or 'transfer role'}"
                        for hub, _, _ in subset
                    ],
                    hovertemplate="%{text}<extra></extra>",
                )
            )

    figure.add_trace(
        go.Scattermap(
            lat=[venue_lat],
            lon=[venue_lon],
            mode="markers",
            marker=dict(size=18, color=COLORS["ink"]),
            name="Venue",
            text=[str(venue.get("name") or "Venue")],
            hovertemplate="%{text}<extra></extra>",
        )
    )

    all_latitudes = [venue_lat, *[lat for _, lat, _ in valid_hubs]]
    all_longitudes = [venue_lon, *[lon for _, _, lon in valid_hubs]]
    spread = max(
        max(all_latitudes) - min(all_latitudes),
        (max(all_longitudes) - min(all_longitudes)) * math.cos(math.radians(venue_lat)),
        0.01,
    )
    zoom = 11.2 if spread < 0.04 else 9.2 if spread < 0.16 else 7.7 if spread < 0.55 else 6.4
    return style_map(
        figure,
        390,
        zoom=zoom,
        lat=sum(all_latitudes) / len(all_latitudes),
        lon=sum(all_longitudes) / len(all_longitudes),
    )
