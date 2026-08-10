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


def _hub_records(plan: Mapping[str, Any], candidate_hubs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    selected_name = str(plan.get("regional_hub_name") or "")
    hubs: list[dict[str, Any]] = []
    seen: set[tuple[str, float | None, float | None]] = set()
    for raw in candidate_hubs:
        name = str(raw.get("name") or "")
        if "no service" in name.casefold():
            continue
        hub = dict(raw)
        key = (name.casefold(), _number(hub.get("lat")), _number(hub.get("lon")))
        if key in seen:
            continue
        seen.add(key)
        hub["selected"] = name == selected_name
        hubs.append(hub)
    if selected_name and not any(bool(hub.get("selected")) for hub in hubs):
        hubs.insert(
            0,
            {
                "name": selected_name,
                "lat": plan.get("regional_hub_lat"),
                "lon": plan.get("regional_hub_lon"),
                "selected": True,
            },
        )
    return hubs


def operating_overlap_map(
    plan: Mapping[str, Any],
    venue: Mapping[str, Any],
    candidate_hubs: Sequence[Mapping[str, Any]] = (),
) -> go.Figure:
    """Map the selected transfer anchor alongside the retained candidate shortlist."""

    venue_lat = _number(venue.get("lat"))
    venue_lon = _number(venue.get("lon"))
    figure = go.Figure()
    if venue_lat is None or venue_lon is None:
        return style_map(figure, 390, zoom=3, lat=38.5, lon=-96)

    hubs = _hub_records(plan, candidate_hubs)
    valid_hubs = [
        (hub, _number(hub.get("lat")), _number(hub.get("lon")))
        for hub in hubs
    ]
    valid_hubs = [(hub, lat, lon) for hub, lat, lon in valid_hubs if lat is not None and lon is not None]

    selected_hubs = [(hub, lat, lon) for hub, lat, lon in valid_hubs if bool(hub.get("selected"))]
    other_hubs = [(hub, lat, lon) for hub, lat, lon in valid_hubs if not bool(hub.get("selected"))]
    if selected_hubs:
        selected, selected_lat, selected_lon = selected_hubs[0]
        label = f"Schematic link: {selected.get('name') or 'hub'} to venue"
        figure.add_trace(
            go.Scattermap(
                lat=[selected_lat, venue_lat],
                lon=[selected_lon, venue_lon],
                mode="lines",
                line=dict(color=COLORS["slate"], width=2),
                name="Schematic transfer link",
                text=[label, label],
                hovertemplate="%{text}<extra></extra>",
            )
        )
    if other_hubs:
        figure.add_trace(
            go.Scattermap(
                lat=[lat for _, lat, _ in other_hubs],
                lon=[lon for _, _, lon in other_hubs],
                mode="markers",
                marker=dict(size=10, color=COLORS["blue"], opacity=0.72),
                name="Other screened candidates",
                text=[str(hub.get("name") or "Candidate hub") for hub, _, _ in other_hubs],
                hovertemplate="%{text}<extra></extra>",
            )
        )
    if selected_hubs:
        figure.add_trace(
            go.Scattermap(
                lat=[selected_hubs[0][1]],
                lon=[selected_hubs[0][2]],
                mode="markers",
                marker=dict(size=17, color=COLORS["amber"]),
                name="Selected engine anchor",
                text=[str(selected_hubs[0][0].get("name") or "Selected hub")],
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
    zoom = 11.2 if spread < 0.04 else 9.8 if spread < 0.16 else 8.6 if spread < 0.55 else 7.3
    return style_map(
        figure,
        390,
        zoom=zoom,
        lat=sum(all_latitudes) / len(all_latitudes),
        lon=sum(all_longitudes) / len(all_longitudes),
    )
