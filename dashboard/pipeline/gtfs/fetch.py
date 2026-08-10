"""Explicitly refresh pinned GTFS feeds and compute match-window venue evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.gtfs.config import GTFS_FEEDS, MODE_CAPACITY_RANGES, GtfsFeedSource
from dashboard.pipeline.public.common import artifact_hash, write_json
from dashboard.pipeline.public.loaders import load_schedule_snapshot

HEADERS = {"User-Agent": "Mobility-Readiness-Platform/0.3"}
EVENT_WINDOW_START = pd.Timestamp("2026-06-11")
EVENT_WINDOW_END = pd.Timestamp("2026-07-19")
REQUIRED_FILES = ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt")
VENUE_RADIUS_MILES = 2.0
SERVICE_RADIUS_MILES = 0.5
REGIONAL_HUB_RADIUS_MILES = 40.0
MAX_REGIONAL_HUBS = 8
WINDOW_BEFORE_MIN = 240
WINDOW_AFTER_MIN = 240
ASSUMED_MATCH_MIN = 120
RAW_FEED_CACHE = Path("data/raw/gtfs")


def _feed_payload(source: GtfsFeedSource) -> bytes:
    """Return a pinned feed from the ignored local cache or its configured URL."""

    cache_path = RAW_FEED_CACHE / f"{source.expected_sha256}.zip" if source.expected_sha256 else None
    if cache_path and cache_path.exists():
        payload = cache_path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if digest != source.expected_sha256:
            raise ValueError(
                f"Cached GTFS hash mismatch for {source.agency}: expected {source.expected_sha256}, found {digest}"
            )
        return payload
    response = requests.get(source.url, headers=HEADERS, timeout=120)
    response.raise_for_status()
    payload = response.content
    digest = hashlib.sha256(payload).hexdigest()
    if source.expected_sha256 and digest != source.expected_sha256:
        raise ValueError(
            f"Pinned GTFS hash mismatch for {source.agency}: expected {source.expected_sha256}, found {digest}"
        )
    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(payload)
    return payload


def haversine_miles(lat: float, lon: float, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
    radius = 3958.8
    phi1 = math.radians(lat)
    phi2 = np.radians(lats)
    dphi = phi2 - phi1
    dlam = np.radians(lons - lon)
    a = np.sin(dphi / 2) ** 2 + math.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * radius * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _nested_zips(zf: zipfile.ZipFile) -> list[zipfile.ZipFile]:
    result = [zf]
    for name in zf.namelist():
        if name.lower().endswith(".zip"):
            try:
                result.append(zipfile.ZipFile(io.BytesIO(zf.read(name))))
            except (KeyError, zipfile.BadZipFile):
                pass
    return result


def _find_member(zf: zipfile.ZipFile, filename: str) -> str | None:
    expected = filename.lower()
    return next(
        (name for name in zf.namelist() if name.replace("\\", "/").rsplit("/", 1)[-1].lower() == expected),
        None,
    )


def _read_table(zf: zipfile.ZipFile, filename: str) -> pd.DataFrame:
    member = _find_member(zf, filename)
    if member is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(zf.open(member), dtype=str, low_memory=False)
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()


def _gtfs_seconds(value: object) -> int | None:
    parts = str(value).split(":")
    if len(parts) != 3:
        return None
    try:
        hour, minute, second = (int(part) for part in parts)
    except ValueError:
        return None
    if hour < 0 or minute not in range(60) or second not in range(60):
        return None
    return hour * 3600 + minute * 60 + second


def _service_dates(zf: zipfile.ZipFile) -> tuple[dict[date, set[str]], dict[str, Any]]:
    calendar = _read_table(zf, "calendar.txt")
    exceptions = _read_table(zf, "calendar_dates.txt")
    services: dict[date, set[str]] = defaultdict(set)
    starts: list[date] = []
    ends: list[date] = []
    weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    if not calendar.empty and {"service_id", "start_date", "end_date"}.issubset(calendar):
        for row in calendar.to_dict("records"):
            try:
                start = datetime.strptime(str(row["start_date"]), "%Y%m%d").date()
                end = datetime.strptime(str(row["end_date"]), "%Y%m%d").date()
            except ValueError:
                continue
            starts.append(start)
            ends.append(end)
            current = max(start, EVENT_WINDOW_START.date())
            last = min(end, EVENT_WINDOW_END.date())
            while current <= last:
                if str(row.get(weekdays[current.weekday()], "0")) == "1":
                    services[current].add(str(row["service_id"]))
                current += timedelta(days=1)
    if not exceptions.empty and {"service_id", "date", "exception_type"}.issubset(exceptions):
        for row in exceptions.to_dict("records"):
            try:
                service_date = datetime.strptime(str(row["date"]), "%Y%m%d").date()
            except ValueError:
                continue
            starts.append(service_date)
            ends.append(service_date)
            if not EVENT_WINDOW_START.date() <= service_date <= EVENT_WINDOW_END.date():
                continue
            if str(row["exception_type"]) == "1":
                services[service_date].add(str(row["service_id"]))
            elif str(row["exception_type"]) == "2":
                services[service_date].discard(str(row["service_id"]))
    validity = "valid" if any(services.values()) else ("outside_event_window" if starts else "unavailable")
    details = {
        "calendar_validity": validity,
        "calendar_start": min(starts).isoformat() if starts else None,
        "calendar_end": max(ends).isoformat() if ends else None,
        "calendar_present": not calendar.empty,
        "calendar_dates_present": not exceptions.empty,
    }
    return services, details


def _venue_stop_ids(
    stops: pd.DataFrame,
    venue: dict[str, Any],
    radius_miles: float = VENUE_RADIUS_MILES,
) -> tuple[set[str], pd.DataFrame]:
    required = {"stop_id", "stop_lat", "stop_lon"}
    if stops.empty or not required.issubset(stops):
        return set(), pd.DataFrame(columns=["stop_id", "stop_lat", "stop_lon", "distance_mi"])
    columns = [
        column for column in ("stop_id", "stop_name", "stop_lat", "stop_lon", "agency", "routes") if column in stops
    ]
    work = stops[columns].copy()
    work["stop_lat"] = pd.to_numeric(work["stop_lat"], errors="coerce")
    work["stop_lon"] = pd.to_numeric(work["stop_lon"], errors="coerce")
    work = work.dropna(subset=["stop_lat", "stop_lon"])
    work["distance_mi"] = haversine_miles(
        float(venue["lat"]), float(venue["lon"]), work["stop_lat"].to_numpy(), work["stop_lon"].to_numpy()
    )
    nearby = work[work["distance_mi"] <= radius_miles].copy()
    return set(nearby["stop_id"].astype(str)), nearby


def _bounded_coordinates(frame: pd.DataFrame, maximum: int = 200) -> list[list[float]]:
    """Return a deterministic, bounded GTFS line without claiming geometric precision."""

    if frame.empty or not {"shape_pt_lat", "shape_pt_lon"}.issubset(frame):
        return []
    work = frame.copy()
    work["shape_pt_lat"] = pd.to_numeric(work["shape_pt_lat"], errors="coerce")
    work["shape_pt_lon"] = pd.to_numeric(work["shape_pt_lon"], errors="coerce")
    work["shape_pt_sequence_num"] = pd.to_numeric(work.get("shape_pt_sequence"), errors="coerce")
    work = work.dropna(subset=["shape_pt_lat", "shape_pt_lon"]).sort_values(
        ["shape_pt_sequence_num"], kind="stable", na_position="last"
    )
    if len(work) > maximum:
        indices = np.linspace(0, len(work) - 1, maximum, dtype=int)
        work = work.iloc[indices]
    return [
        [round(float(row.shape_pt_lon), 6), round(float(row.shape_pt_lat), 6)] for row in work.itertuples(index=False)
    ]


def _event_route_shapes(
    stops: pd.DataFrame,
    stop_times: pd.DataFrame,
    trips: pd.DataFrame,
    routes: pd.DataFrame,
    shapes: pd.DataFrame,
    services: dict[date, set[str]],
    venue_stop_ids: set[str],
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, tuple[str, ...]]]:
    """Extract route labels and shapes for event-valid trips serving the venue catchment."""

    required_trip = {"trip_id", "service_id", "route_id"}
    if not required_trip.issubset(trips) or not {"trip_id", "stop_id"}.issubset(stop_times):
        return [], {}
    active_services = (
        set().union(
            *(services.get(datetime.fromisoformat(str(event["kickoff_local"])).date(), set()) for event in events)
        )
        if events
        else set().union(*services.values())
        if services
        else set()
    )
    catchment_times = stop_times[stop_times["stop_id"].astype(str).isin(venue_stop_ids)].copy()
    trip_ids = set(catchment_times["trip_id"].astype(str))
    eligible = trips[
        trips["trip_id"].astype(str).isin(trip_ids) & trips["service_id"].astype(str).isin(active_services)
    ].copy()
    route_labels: dict[str, str] = {}
    if "route_id" in routes:
        for row in routes.to_dict("records"):
            route_id = str(row.get("route_id"))
            route_labels[route_id] = str(row.get("route_short_name") or row.get("route_long_name") or route_id)
    if not eligible.empty:
        eligible["trip_id"] = eligible["trip_id"].astype(str)
        eligible["route_id"] = eligible["route_id"].astype(str)
    trip_routes = eligible.set_index("trip_id")["route_id"].to_dict() if not eligible.empty else {}
    stop_routes: dict[str, tuple[str, ...]] = {}
    for stop_id, group in catchment_times.groupby(catchment_times["stop_id"].astype(str)):
        labels = sorted(
            {
                route_labels.get(str(trip_routes.get(str(trip_id))), str(trip_routes.get(str(trip_id))))
                for trip_id in group["trip_id"].astype(str)
                if str(trip_id) in trip_routes
            }
        )
        stop_routes[str(stop_id)] = tuple(label for label in labels if label and label != "None")
    if shapes.empty or "shape_id" not in eligible or not {"shape_id", "shape_pt_lat", "shape_pt_lon"}.issubset(shapes):
        return [], stop_routes
    results = []
    shape_routes = eligible.dropna(subset=["shape_id"])[["route_id", "shape_id"]].drop_duplicates()
    for item in shape_routes.sort_values(["route_id", "shape_id"], kind="stable").itertuples(index=False):
        shape_id = str(item.shape_id)
        coordinates = _bounded_coordinates(shapes[shapes["shape_id"].astype(str) == shape_id])
        if len(coordinates) < 2:
            continue
        route_id = str(item.route_id)
        results.append(
            {
                "route_id": route_id,
                "route_name": route_labels.get(route_id, route_id),
                "shape_id": shape_id,
                "coordinates": coordinates,
                "status": "observed",
            }
        )
    return results, stop_routes


def _regional_hub_candidates(
    stops: pd.DataFrame,
    stop_times: pd.DataFrame,
    trips: pd.DataFrame,
    routes: pd.DataFrame,
    services: dict[date, set[str]],
    venue: dict[str, Any],
    events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a bounded set of event-valid regional transfer-hub candidates.

    These rows rank scheduled network connectivity; they do not establish
    special-event operations, platform capacity, parking, or curb feasibility.
    Parent stations consolidate platform-level GTFS stops where available.
    """

    needed_stops = {"stop_id", "stop_lat", "stop_lon"}
    needed_times = {"trip_id", "stop_id"}
    needed_trips = {"trip_id", "service_id", "route_id"}
    if (
        stops.empty
        or stop_times.empty
        or trips.empty
        or not needed_stops.issubset(stops)
        or not needed_times.issubset(stop_times)
        or not needed_trips.issubset(trips)
    ):
        return []
    event_dates = [datetime.fromisoformat(str(event["kickoff_local"])).date() for event in events]
    active_services = (
        set().union(*(services.get(event_date, set()) for event_date in event_dates)) if event_dates else set()
    )
    if not active_services:
        return []

    stop_info = stops.copy()
    stop_info["stop_id"] = stop_info["stop_id"].astype(str)
    stop_info["stop_lat"] = pd.to_numeric(stop_info["stop_lat"], errors="coerce")
    stop_info["stop_lon"] = pd.to_numeric(stop_info["stop_lon"], errors="coerce")
    stop_info = stop_info.dropna(subset=["stop_lat", "stop_lon"])
    stop_ids = set(stop_info["stop_id"])
    parent_map = {
        str(row.stop_id): (
            str(row.parent_station) if str(getattr(row, "parent_station", "") or "") in stop_ids else str(row.stop_id)
        )
        for row in stop_info.itertuples(index=False)
    }
    station_rows = stop_info.set_index("stop_id").to_dict("index")

    eligible_trips = trips[trips["service_id"].astype(str).isin(active_services)].copy()
    if eligible_trips.empty:
        return []
    eligible_trips["trip_id"] = eligible_trips["trip_id"].astype(str)
    eligible_trips["route_id"] = eligible_trips["route_id"].astype(str)
    eligible_trips["service_id"] = eligible_trips["service_id"].astype(str)
    relevant = stop_times[stop_times["trip_id"].astype(str).isin(set(eligible_trips["trip_id"]))][
        ["trip_id", "stop_id"]
    ].copy()
    relevant["trip_id"] = relevant["trip_id"].astype(str)
    relevant["stop_id"] = relevant["stop_id"].astype(str)
    relevant = relevant[relevant["stop_id"].isin(stop_ids)]
    relevant["hub_stop_id"] = relevant["stop_id"].map(parent_map)
    relevant = relevant.merge(
        eligible_trips[["trip_id", "route_id", "service_id"]],
        on="trip_id",
        how="inner",
    ).drop_duplicates(["hub_stop_id", "trip_id", "route_id"])
    if relevant.empty:
        return []

    route_labels: dict[str, str] = {}
    route_types: dict[str, int] = {}
    if "route_id" in routes:
        for row in routes.to_dict("records"):
            route_id = str(row.get("route_id"))
            route_labels[route_id] = str(row.get("route_short_name") or row.get("route_long_name") or route_id)
            try:
                route_types[route_id] = int(row.get("route_type", 3))
            except (TypeError, ValueError):
                route_types[route_id] = 3

    candidates: list[dict[str, Any]] = []
    for hub_stop_id, group in relevant.groupby("hub_stop_id", sort=False):
        row = station_rows.get(str(hub_stop_id))
        if not row:
            continue
        station_name = str(row.get("stop_name") or "Unnamed station")
        if "no service" in station_name.casefold():
            continue
        lat = float(row["stop_lat"])
        lon = float(row["stop_lon"])
        distance = float(haversine_miles(float(venue["lat"]), float(venue["lon"]), np.array([lat]), np.array([lon]))[0])
        if not SERVICE_RADIUS_MILES < distance <= REGIONAL_HUB_RADIUS_MILES:
            continue
        route_ids = sorted(set(group["route_id"].astype(str)))
        event_valid_dates = sum(
            any(service_id in services.get(event_date, set()) for service_id in set(group["service_id"].astype(str)))
            for event_date in event_dates
        )
        if not route_ids or event_valid_dates == 0:
            continue
        modes = sorted(
            {
                MODE_CAPACITY_RANGES.get(route_types.get(route_id, 3), MODE_CAPACITY_RANGES[3])["mode"]
                for route_id in route_ids
            }
        )
        service_events = int(group["trip_id"].nunique())
        route_count = len(route_ids)
        rail_priority = any(mode in {"tram_light_rail", "subway_metro", "rail", "ferry"} for mode in modes)
        hub_score = (
            (8_000 if rail_priority else 0)
            + route_count * 500
            + min(service_events, 999)
            + event_valid_dates * 10
            - distance
        )
        candidates.append(
            {
                "stop_id": str(hub_stop_id),
                "name": station_name,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "distance_mi": round(distance, 3),
                "routes": [route_labels.get(route_id, route_id) for route_id in route_ids[:12]],
                "route_count": route_count,
                "modes": modes,
                "rail_priority": rail_priority,
                "event_valid_match_dates": event_valid_dates,
                "event_valid_trip_patterns": service_events,
                "hub_score": round(hub_score, 3),
                "status": "observed",
                "evidence_limit": "Scheduled connectivity candidate; special-event platform, parking, curb, and transfer capacity are not established.",
            }
        )
    ordered = sorted(
        candidates, key=lambda row: (-float(row["hub_score"]), float(row["distance_mi"]), str(row["name"]))
    )
    unique: list[dict[str, Any]] = []
    names: set[str] = set()
    for row in ordered:
        name_key = str(row["name"]).strip().casefold()
        if name_key in names:
            continue
        names.add(name_key)
        unique.append(row)
        if len(unique) >= MAX_REGIONAL_HUBS:
            break
    return unique


def _event_departures(
    stop_times: pd.DataFrame,
    trips: pd.DataFrame,
    routes: pd.DataFrame,
    frequencies: pd.DataFrame,
    services: dict[date, set[str]],
    venue_stop_distances: dict[str, float],
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[int]]:
    needed_st = {"trip_id", "stop_id", "departure_time"}
    needed_trips = {"trip_id", "service_id", "route_id"}
    if not needed_st.issubset(stop_times) or not needed_trips.issubset(trips):
        return [], Counter()
    venue_stop_ids = set(venue_stop_distances)
    all_stop_times = stop_times.copy()
    all_stop_times["departure_seconds"] = all_stop_times["departure_time"].map(_gtfs_seconds)
    trip_start_seconds = (
        all_stop_times.dropna(subset=["departure_seconds"]).groupby("trip_id")["departure_seconds"].min().to_dict()
    )
    relevant = all_stop_times[all_stop_times["stop_id"].astype(str).isin(venue_stop_ids)].copy()
    relevant = relevant.dropna(subset=["departure_seconds"])
    relevant["departure_seconds"] = relevant["departure_seconds"].astype(int)
    relevant["stop_distance_mi"] = relevant["stop_id"].astype(str).map(venue_stop_distances)
    relevant = relevant.merge(trips[list(needed_trips)], on="trip_id", how="inner")
    route_types = {}
    if {"route_id", "route_type"}.issubset(routes):
        route_types = {
            str(row.route_id): int(row.route_type)
            for row in routes[["route_id", "route_type"]].itertuples(index=False)
            if str(row.route_type).isdigit()
        }
    relevant["route_type"] = relevant["route_id"].map(lambda value: route_types.get(str(value), 3))

    frequency_rows: dict[str, list[tuple[int, int, int]]] = defaultdict(list)
    if not frequencies.empty and {"trip_id", "start_time", "end_time", "headway_secs"}.issubset(frequencies):
        for row in frequencies.to_dict("records"):
            start = _gtfs_seconds(row["start_time"])
            end = _gtfs_seconds(row["end_time"])
            try:
                headway = int(float(row["headway_secs"]))
            except ValueError:
                continue
            if start is not None and end is not None and headway > 0:
                frequency_rows[str(row["trip_id"])].append((start, end, headway))

    results = []
    mode_counts: Counter[int] = Counter()
    for event in events:
        kickoff = datetime.fromisoformat(str(event["kickoff_local"]))
        match_date = kickoff.date()
        kickoff_seconds = kickoff.hour * 3600 + kickoff.minute * 60 + kickoff.second
        window_start = kickoff_seconds - WINDOW_BEFORE_MIN * 60
        window_end = kickoff_seconds + WINDOW_AFTER_MIN * 60
        active = services.get(match_date, set())
        candidates = relevant[relevant["service_id"].astype(str).isin(active)]
        sort_columns = ["trip_id", "stop_distance_mi", "departure_seconds"]
        if "stop_sequence" in candidates:
            sort_columns.append("stop_sequence")
        trip_rows = candidates.sort_values(sort_columns, kind="stable").drop_duplicates("trip_id")
        departure_occurrences: list[tuple[str, int, int]] = []
        for row in trip_rows.itertuples(index=False):
            seconds = int(row.departure_seconds)
            ranges = frequency_rows.get(str(row.trip_id), [])
            if ranges:
                template_start = int(trip_start_seconds.get(row.trip_id, seconds))
                offset = seconds - min(template_start, seconds)
                for range_index, (start, end, headway) in enumerate(ranges):
                    occurrence = start + int(offset)
                    while occurrence < end + int(offset):
                        if window_start <= occurrence <= window_end:
                            occurrence_id = f"{row.trip_id}:frequency:{range_index}:{occurrence - offset}"
                            departure_occurrences.append((occurrence_id, occurrence, int(row.route_type)))
                        occurrence += headway
            elif window_start <= seconds <= window_end:
                departure_occurrences.append((str(row.trip_id), seconds, int(row.route_type)))
        # One static trip_id or expanded frequency occurrence is one vehicle.
        # Selecting the closest venue stop before expansion prevents a vehicle
        # serving several nearby stops from being counted more than once.
        departure_occurrences = sorted(set(departure_occurrences))
        match_end_seconds = kickoff_seconds + ASSUMED_MATCH_MIN * 60
        after_match = [seconds for _, seconds, _ in departure_occurrences if seconds >= match_end_seconds]
        event_mode_counts: Counter[int] = Counter(route_type for _, _, route_type in departure_occurrences)
        mode_counts.update(event_mode_counts)
        event_capacity = {
            band: sum(
                count * MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])[band]
                for mode, count in event_mode_counts.items()
            )
            for band in ("low", "base", "high")
        }
        service_day = kickoff.replace(hour=0, minute=0, second=0, microsecond=0)
        hourly_counts: Counter[tuple[int, str, int]] = Counter()
        for _, seconds, route_type in departure_occurrences:
            direction = (
                "arrival" if seconds <= kickoff_seconds else "departure" if seconds >= match_end_seconds else "both"
            )
            hourly_counts[(seconds // 3600 * 3600, direction, route_type)] += 1
        hourly_service = []
        for (hour_seconds, direction, route_type), count in sorted(hourly_counts.items()):
            capacity = MODE_CAPACITY_RANGES.get(route_type, MODE_CAPACITY_RANGES[3])
            hourly_service.append(
                {
                    "hour_start_local": (service_day + timedelta(seconds=hour_seconds)).isoformat(),
                    "direction": direction,
                    "mode": capacity["mode"],
                    "departures_per_hour": count,
                    "vehicle_capacity_low": capacity["low"],
                    "vehicle_capacity_base": capacity["base"],
                    "vehicle_capacity_high": capacity["high"],
                }
            )
        results.append(
            {
                "match_id": event["match_id"],
                "kickoff_local": event["kickoff_local"],
                "calendar_valid": bool(active),
                "departures": len(departure_occurrences),
                "latest_departure_seconds": max((seconds for _, seconds, _ in departure_occurrences), default=None),
                "service_span_after_match_min": round(
                    (max(after_match) - kickoff_seconds - ASSUMED_MATCH_MIN * 60) / 60, 1
                )
                if after_match
                else 0.0,
                "mode_departures": {
                    MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])["mode"]: count
                    for mode, count in sorted(event_mode_counts.items())
                },
                "capacity_low": event_capacity["low"],
                "capacity_base": event_capacity["base"],
                "capacity_high": event_capacity["high"],
                "hourly_service": hourly_service,
                "direction_basis": (
                    "arrival through kickoff; departure from assumed match end; in-match service applies to both"
                ),
            }
        )
    return results, mode_counts


def extract_feed(
    payload: bytes,
    venue: dict[str, Any] | None = None,
    events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    venue = venue or {"lat": 0.0, "lon": 0.0}
    events = events or []
    aggregate_stops = []
    route_ids: set[str] = set()
    scheduled_departures = 0
    required_status = {name: False for name in REQUIRED_FILES}
    optional_status = {name: False for name in ("frequencies.txt", "shapes.txt", "transfers.txt", "pathways.txt")}
    validities = []
    calendar_starts = []
    calendar_ends = []
    event_rows: list[dict[str, Any]] = []
    mode_counts: Counter[int] = Counter()
    route_shapes: list[dict[str, Any]] = []
    regional_hubs: list[dict[str, Any]] = []
    stop_routes: dict[str, set[str]] = defaultdict(set)
    with zipfile.ZipFile(io.BytesIO(payload)) as outer:
        for zf in _nested_zips(outer):
            tables = {name: _read_table(zf, name) for name in REQUIRED_FILES}
            optional = {name: _read_table(zf, name) for name in optional_status}
            for name in required_status:
                required_status[name] |= _find_member(zf, name) is not None
            for name in optional_status:
                optional_status[name] |= _find_member(zf, name) is not None
            stops, routes, trips, stop_times = (tables[name] for name in REQUIRED_FILES)
            if not stops.empty:
                aggregate_stops.append(stops)
            if "route_id" in routes:
                route_ids.update(routes["route_id"].astype(str))
            scheduled_departures += len(stop_times) if "departure_time" in stop_times else 0
            services, details = _service_dates(zf)
            validities.append(details["calendar_validity"])
            if details["calendar_start"]:
                calendar_starts.append(details["calendar_start"])
            if details["calendar_end"]:
                calendar_ends.append(details["calendar_end"])
            _, capacity_stops = _venue_stop_ids(stops, venue, SERVICE_RADIUS_MILES)
            regional_hubs.extend(
                _regional_hub_candidates(
                    stops,
                    stop_times,
                    trips,
                    routes,
                    services,
                    venue,
                    events,
                )
            )
            capacity_stop_distances = {
                str(row.stop_id): float(row.distance_mi) for row in capacity_stops.itertuples(index=False)
            }
            walking_stop_ids, _ = _venue_stop_ids(stops, venue, VENUE_RADIUS_MILES)
            shape_rows, stop_route_rows = _event_route_shapes(
                stops,
                stop_times,
                trips,
                routes,
                optional["shapes.txt"],
                services,
                walking_stop_ids,
                events,
            )
            route_shapes.extend(shape_rows)
            for stop_id, labels in stop_route_rows.items():
                stop_routes[stop_id].update(labels)
            rows, counts = _event_departures(
                stop_times,
                trips,
                routes,
                optional["frequencies.txt"],
                services,
                capacity_stop_distances,
                events,
            )
            event_rows.extend(rows)
            mode_counts.update(counts)
    stops = (
        pd.concat(aggregate_stops, ignore_index=True).drop_duplicates("stop_id") if aggregate_stops else pd.DataFrame()
    )
    venue_ids, nearby = _venue_stop_ids(stops, venue, SERVICE_RADIUS_MILES)
    capacity = {
        band: sum(
            count * MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])[band] for mode, count in mode_counts.items()
        )
        for band in ("low", "base", "high")
    }
    if not events:
        event_departures: int | None = scheduled_departures if "valid" in validities else None
    else:
        event_departures = sum(row["departures"] for row in event_rows) if "valid" in validities else None
    return {
        "stops": stops,
        "route_ids": sorted(route_ids),
        "route_count": len(route_ids),
        "scheduled_departures": scheduled_departures,
        "event_window_departures": event_departures,
        "event_departures_by_match": event_rows,
        "service_span_after_match_min": max((row["service_span_after_match_min"] for row in event_rows), default=None),
        "calendar_validity": "valid"
        if "valid" in validities
        else ("outside_event_window" if validities else "unavailable"),
        "service_span": {
            "start_date": min(calendar_starts) if calendar_starts else None,
            "end_date": max(calendar_ends) if calendar_ends else None,
        },
        "required_files": required_status,
        "optional_files": optional_status,
        "venue_stop_count": len(venue_ids),
        "nearest_stop_mi": round(float(nearby["distance_mi"].min()), 3) if not nearby.empty else None,
        "mode_departures": {
            MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])["mode"]: count
            for mode, count in sorted(mode_counts.items())
        },
        "capacity": capacity,
        "route_shapes": route_shapes,
        "regional_hubs": regional_hubs,
        "stop_routes": {stop_id: sorted(labels) for stop_id, labels in stop_routes.items()},
    }


def count_near_venue(stops: pd.DataFrame, venue: dict[str, Any]) -> dict[str, Any]:
    _, nearby = _venue_stop_ids(stops, venue)
    if stops.empty or not {"stop_lat", "stop_lon"}.issubset(stops):
        return {
            **{f"stops_{label}": 0 for label in ("0_25mi", "0_5mi", "1mi", "2mi", "5mi")},
            "nearest_stop_mi": None,
        }
    work = stops.copy()
    work["stop_lat"] = pd.to_numeric(work["stop_lat"], errors="coerce")
    work["stop_lon"] = pd.to_numeric(work["stop_lon"], errors="coerce")
    work = work.dropna(subset=["stop_lat", "stop_lon"])
    distances = haversine_miles(
        float(venue["lat"]), float(venue["lon"]), work["stop_lat"].to_numpy(), work["stop_lon"].to_numpy()
    )
    return {
        "stops_0_25mi": int((distances <= 0.25).sum()),
        "stops_0_5mi": int((distances <= 0.5).sum()),
        "stops_1mi": int((distances <= 1).sum()),
        "stops_2mi": int((distances <= 2).sum()),
        "stops_5mi": int((distances <= 5).sum()),
        "nearest_stop_mi": round(float(distances.min()), 3) if len(distances) else None,
        "stop_points_2mi": [
            {
                "stop_id": str(row.stop_id),
                "name": str(getattr(row, "stop_name", "") or "Unnamed stop"),
                "lat": round(float(row.stop_lat), 6),
                "lon": round(float(row.stop_lon), 6),
                "distance_mi": round(float(row.distance_mi), 3),
                "agency": str(getattr(row, "agency", "") or "Agency unavailable"),
                "route": ", ".join(getattr(row, "routes", ()) or ()) or "Route unavailable",
                "event_relevant": bool(getattr(row, "routes", ()) or ()),
                "status": "observed",
            }
            for row in nearby.itertuples(index=False)
        ],
    }


def _source_events(source: GtfsFeedSource, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = date.fromisoformat(source.valid_from) if source.valid_from else None
    end = date.fromisoformat(source.valid_to) if source.valid_to else None
    selected = []
    for event in events:
        event_date = datetime.fromisoformat(str(event["kickoff_local"])).date()
        if start and event_date < start:
            continue
        if end and event_date > end:
            continue
        selected.append(event)
    return selected


def fetch_city(city: str, feeds: list[GtfsFeedSource], events: list[dict[str, Any]]) -> dict[str, Any]:
    venue = HOST_CITIES[city]
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    feed_results = []
    all_stops = []
    totals: Counter[str] = Counter()
    route_keys: set[tuple[str, str]] = set()
    scheduled_by_agency: dict[str, int] = {}
    capacities: Counter[str] = Counter()
    calendars = []
    spans_after = []
    optional_presence: dict[str, bool] = defaultdict(bool)
    match_evidence: dict[str, dict[str, Any]] = {}
    route_shapes: list[dict[str, Any]] = []
    regional_hubs: list[dict[str, Any]] = []
    for source in feeds:
        agency = source.agency
        url = source.url
        assigned_events = _source_events(source, events)
        base = {
            "agency": agency,
            "url": url,
            "publisher_url": source.publisher_url,
            "archive_provider": source.archive_provider,
            "valid_from": source.valid_from,
            "valid_to": source.valid_to,
            "retrieved_at_utc": retrieved_at,
            "status": "unavailable",
            "sha256": None,
        }
        try:
            payload = _feed_payload(source)
            digest = hashlib.sha256(payload).hexdigest()
            extracted = extract_feed(payload, venue, assigned_events)
            complete = all(extracted["required_files"].values())
            assigned_match_ids = {str(event["match_id"]) for event in assigned_events}
            valid_match_ids = {
                str(row["match_id"]) for row in extracted["event_departures_by_match"] if row["calendar_valid"]
            }
            valid = bool(assigned_match_ids) and assigned_match_ids.issubset(valid_match_ids)
            status = "observed" if complete and valid else "partial"
            feed_results.append(
                {
                    **base,
                    "status": status,
                    "sha256": digest,
                    "bytes": len(payload),
                    "required_files": extracted["required_files"],
                    "optional_files": extracted["optional_files"],
                    "calendar_validity": extracted["calendar_validity"],
                    "service_span": extracted["service_span"],
                    "assigned_match_ids": sorted(assigned_match_ids),
                    "event_valid_match_ids": sorted(assigned_match_ids & valid_match_ids),
                }
            )
            feed_stops = extracted["stops"].copy()
            if not feed_stops.empty:
                feed_stops["agency"] = agency
                feed_stops["routes"] = (
                    feed_stops["stop_id"]
                    .astype(str)
                    .map(lambda stop_id: tuple(extracted["stop_routes"].get(stop_id, ())))
                )
            all_stops.append(feed_stops)
            route_shapes.extend({**shape, "agency": agency} for shape in extracted["route_shapes"])
            regional_hubs.extend({**hub, "agency": agency} for hub in extracted["regional_hubs"])
            route_keys.update((agency, str(route_id)) for route_id in extracted["route_ids"])
            scheduled_by_agency[agency] = max(
                scheduled_by_agency.get(agency, 0), int(extracted["scheduled_departures"])
            )
            totals.update(event_window_departures=extracted["event_window_departures"] or 0)
            capacities.update(extracted["capacity"])
            calendars.append(extracted["calendar_validity"])
            if extracted["service_span_after_match_min"] is not None:
                spans_after.append(extracted["service_span_after_match_min"])
            if valid:
                for event_row in extracted["event_departures_by_match"]:
                    if not event_row["calendar_valid"]:
                        continue
                    match_id = str(event_row["match_id"])
                    current = match_evidence.setdefault(
                        match_id,
                        {
                            "match_id": match_id,
                            "kickoff_local": event_row["kickoff_local"],
                            "event_window_departures": 0,
                            "event_capacity_low": 0,
                            "event_capacity_base": 0,
                            "event_capacity_high": 0,
                            "service_span_after_match_min": 0.0,
                            "event_window_hours": (WINDOW_BEFORE_MIN + WINDOW_AFTER_MIN) / 60.0,
                            "hourly_service": [],
                        },
                    )
                    current["event_window_departures"] += int(event_row["departures"])
                    for level in ("low", "base", "high"):
                        current[f"event_capacity_{level}"] += int(event_row[f"capacity_{level}"])
                    current["service_span_after_match_min"] = max(
                        float(current["service_span_after_match_min"]),
                        float(event_row["service_span_after_match_min"]),
                    )
                    current["hourly_service"].extend(event_row.get("hourly_service", []))
                    current["direction_basis"] = event_row.get("direction_basis")
            for name, present in extracted["optional_files"].items():
                optional_presence[name] |= present
        except (requests.RequestException, zipfile.BadZipFile, OSError, ValueError) as exc:
            feed_results.append({**base, "error": str(exc)[:500]})
    stops = (
        pd.concat(all_stops, ignore_index=True).drop_duplicates(["agency", "stop_id"]) if all_stops else pd.DataFrame()
    )
    status = (
        "observed"
        if feed_results and all(feed["status"] == "observed" for feed in feed_results)
        else "partial"
        if any(feed["status"] in {"observed", "partial"} for feed in feed_results)
        else "unavailable"
    )
    for row in match_evidence.values():
        row["status"] = "partial" if status == "partial" else "observed"
        row["hourly_service"] = sorted(
            row.get("hourly_service", []),
            key=lambda service: (
                str(service.get("hour_start_local", "")),
                str(service.get("direction", "")),
                str(service.get("mode", "")),
            ),
        )
    unique_shapes = {(str(row["agency"]), str(row["route_id"]), str(row["shape_id"])): row for row in route_shapes}
    ordered_shapes = [unique_shapes[key] for key in sorted(unique_shapes)]
    omitted_shapes = max(len(ordered_shapes) - 100, 0)
    ordered_shapes = ordered_shapes[:100]
    unique_hubs = {(str(row["agency"]), str(row["stop_id"])): row for row in regional_hubs}
    ordered_hubs = sorted(
        unique_hubs.values(),
        key=lambda row: (
            -float(row.get("hub_score", 0)),
            float(row.get("distance_mi", math.inf)),
            str(row.get("name", "")),
        ),
    )[:MAX_REGIONAL_HUBS]
    return {
        **count_near_venue(stops, venue),
        "city": city,
        "venue": venue["venue"],
        "venue_lat": venue["lat"],
        "venue_lon": venue["lon"],
        "agencies": list(dict.fromkeys(source.agency for source in feeds)),
        "total_agency_stops": len(stops),
        "route_count": len(route_keys),
        "scheduled_departures": sum(scheduled_by_agency.values()),
        "event_window_departures": totals["event_window_departures"] if status != "unavailable" else None,
        "service_span_after_match_min": max(spans_after) if spans_after else None,
        "calendar_validity": "valid" if "valid" in calendars else "unavailable",
        "optional_files": dict(optional_presence),
        "event_capacity_low": capacities["low"],
        "event_capacity_base": capacities["base"],
        "event_capacity_high": capacities["high"],
        "matches": match_evidence,
        "route_shapes": ordered_shapes,
        "route_shapes_omitted": omitted_shapes,
        "regional_hubs": ordered_hubs,
        "capacity_status": "scenario" if status != "unavailable" else "unavailable",
        "feed_status": status,
        "feeds": feed_results,
    }


def score_results(results: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    raw_values = {}
    for city, row in results.items():
        if "feeds" in row:
            valid_hashes = all(
                feed.get("status") == "unavailable"
                or (isinstance(feed.get("sha256"), str) and len(feed["sha256"]) == 64)
                for feed in row["feeds"]
            )
            if not valid_hashes:
                row["feed_status"] = "unavailable"
        raw_values[city] = (
            int(row.get("stops_0_25mi", 0)) * 20
            + int(row.get("stops_0_5mi", 0)) * 10
            + int(row.get("stops_1mi", 0)) * 5
            + int(row.get("stops_2mi", 0)) * 2
            + min(int(row.get("route_count", 0)), 20) * 2
        )
        row["raw_score"] = raw_values[city]
    maximum = max(
        (value for city, value in raw_values.items() if results[city].get("feed_status") != "unavailable"), default=0
    )
    for city, row in results.items():
        status = str(row.get("feed_status", "unavailable"))
        if status == "unavailable":
            row["gtfs_transit_score"] = None
            row["score_status"] = "unavailable"
        else:
            row["gtfs_transit_score"] = round(raw_values[city] / maximum * 100) if maximum else 0
            row["score_status"] = "partial" if status == "partial" else "observed"
    return results


def unavailable_fixture() -> dict[str, dict[str, Any]]:
    return {
        city: {
            "city": city,
            "venue": venue["venue"],
            "venue_lat": venue["lat"],
            "venue_lon": venue["lon"],
            "feed_status": "unavailable",
            "score_status": "unavailable",
            "gtfs_transit_score": None,
            "event_window_departures": None,
            "service_span_after_match_min": None,
            "event_capacity_low": None,
            "event_capacity_base": None,
            "event_capacity_high": None,
            "capacity_status": "unavailable",
            "regional_hubs": [],
            "feeds": [
                {
                    "agency": source.agency,
                    "url": source.url,
                    "publisher_url": source.publisher_url,
                    "archive_provider": source.archive_provider,
                    "valid_from": source.valid_from,
                    "valid_to": source.valid_to,
                    "status": "unavailable",
                    "sha256": None,
                    "retrieved_at_utc": None,
                }
                for source in GTFS_FEEDS[city]
            ],
            "warning": "Fixture only. Run the explicit refresh command before transportation ranking.",
        }
        for city, venue in HOST_CITIES.items()
    }


def write_snapshot(results: dict[str, dict[str, Any]], output: Path, generated_at: str, fixture: bool = False) -> str:
    snapshot = {
        "contract_version": CONTRACT_VERSION,
        "snapshot_kind": "gtfs_venue_access",
        "generated_at_utc": generated_at,
        "status": "unavailable"
        if fixture
        else (
            "observed"
            if all(row["feed_status"] == "observed" for row in results.values())
            else "partial"
            if any(row["feed_status"] != "unavailable" for row in results.values())
            else "unavailable"
        ),
        "fixture": fixture,
        "cities": results,
        "mode_capacity_ranges": MODE_CAPACITY_RANGES,
        "policy": {
            "legacy_cache": "never loaded or promoted",
            "observed_gate": "required files, event-valid calendar, retrieval timestamp, and feed SHA-256",
            "capacity_status": "scenario capacity range; not observed ridership",
            "peak_capacity": (
                "one vehicle per static trip_id or expanded frequency occurrence; "
                "nearest eligible venue stop only; exact local event hour and event phase"
            ),
            "event_window_minutes": {"before": WINDOW_BEFORE_MIN, "after": WINDOW_AFTER_MIN},
            "venue_radius_miles": VENUE_RADIUS_MILES,
            "service_capacity_radius_miles": SERVICE_RADIUS_MILES,
            "regional_hub_radius_miles": REGIONAL_HUB_RADIUS_MILES,
            "regional_hub_limit": MAX_REGIONAL_HUBS,
            "regional_hub_semantics": "event-valid scheduled connectivity candidates; not approved special-event transfer hubs",
        },
    }
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return write_json(output, snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Explicitly download and pin configured GTFS feeds")
    mode.add_argument(
        "--fixture", action="store_true", help="Write a deterministic unavailable fixture without network"
    )
    parser.add_argument("--schedule", type=Path, default=Path("data/snapshots/fifa/fifa_2026_us_schedule.json"))
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/gtfs/gtfs_venue_access.json"))
    parser.add_argument(
        "--city",
        action="append",
        choices=tuple(HOST_CITIES),
        help="Refresh only the selected city and preserve other cities from the current snapshot",
    )
    args = parser.parse_args()
    generated_at = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if args.refresh else "2026-08-01T00:00:00Z"
    )
    if args.fixture:
        results = unavailable_fixture()
    else:
        schedule = load_schedule_snapshot(args.schedule)
        by_city = {city: [event for event in schedule["events"] if event["city"] == city] for city in HOST_CITIES}
        selected = tuple(dict.fromkeys(args.city or GTFS_FEEDS))
        if args.city and args.output.exists():
            from dashboard.pipeline.public.loaders import load_gtfs_snapshot

            results = dict(load_gtfs_snapshot(args.output)["cities"])
        else:
            results = unavailable_fixture()
        results.update({city: fetch_city(city, GTFS_FEEDS[city], by_city[city]) for city in selected})
        results = score_results(results)
    digest = write_snapshot(results, args.output, generated_at, fixture=args.fixture)
    print(
        json.dumps(
            {"output": str(args.output), "status": "fixture" if args.fixture else "refreshed", "file_sha256": digest}
        )
    )


if __name__ == "__main__":
    main()
