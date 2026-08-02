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
from dashboard.pipeline.gtfs.config import GTFS_FEEDS, MODE_CAPACITY_RANGES
from dashboard.pipeline.public.common import artifact_hash, write_json
from dashboard.pipeline.public.loaders import load_schedule_snapshot

HEADERS = {"User-Agent": "Mobility-Readiness-Platform/0.3"}
EVENT_WINDOW_START = pd.Timestamp("2026-06-11")
EVENT_WINDOW_END = pd.Timestamp("2026-07-19")
REQUIRED_FILES = ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt")
VENUE_RADIUS_MILES = 2.0
SERVICE_RADIUS_MILES = 0.5
WINDOW_BEFORE_MIN = 240
WINDOW_AFTER_MIN = 240
ASSUMED_MATCH_MIN = 120


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
    return next((name for name in zf.namelist() if name.lower().endswith(filename)), None)


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
    work = stops[list(required)].copy()
    work["stop_lat"] = pd.to_numeric(work["stop_lat"], errors="coerce")
    work["stop_lon"] = pd.to_numeric(work["stop_lon"], errors="coerce")
    work = work.dropna(subset=["stop_lat", "stop_lon"])
    work["distance_mi"] = haversine_miles(
        float(venue["lat"]), float(venue["lon"]), work["stop_lat"].to_numpy(), work["stop_lon"].to_numpy()
    )
    nearby = work[work["distance_mi"] <= radius_miles].copy()
    return set(nearby["stop_id"].astype(str)), nearby


def _event_departures(
    stop_times: pd.DataFrame,
    trips: pd.DataFrame,
    routes: pd.DataFrame,
    frequencies: pd.DataFrame,
    services: dict[date, set[str]],
    venue_stop_ids: set[str],
    events: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], Counter[int]]:
    needed_st = {"trip_id", "stop_id", "departure_time"}
    needed_trips = {"trip_id", "service_id", "route_id"}
    if not needed_st.issubset(stop_times) or not needed_trips.issubset(trips):
        return [], Counter()
    relevant = stop_times[stop_times["stop_id"].astype(str).isin(venue_stop_ids)].copy()
    relevant["departure_seconds"] = relevant["departure_time"].map(_gtfs_seconds)
    relevant = relevant.dropna(subset=["departure_seconds"])
    relevant["departure_seconds"] = relevant["departure_seconds"].astype(int)
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
        departure_types: list[tuple[int, int]] = []
        for row in candidates.itertuples(index=False):
            seconds = int(row.departure_seconds)
            ranges = frequency_rows.get(str(row.trip_id), [])
            if ranges:
                for start, end, headway in ranges:
                    offset = seconds - min(
                        candidates.loc[candidates["trip_id"] == row.trip_id, "departure_seconds"].min(), seconds
                    )
                    occurrence = start + int(offset)
                    while occurrence < end + int(offset):
                        if window_start <= occurrence <= window_end:
                            departure_types.append((occurrence, int(row.route_type)))
                        occurrence += headway
            elif window_start <= seconds <= window_end:
                departure_types.append((seconds, int(row.route_type)))
        # A trip serving several nearby stops represents one vehicle departure.
        departure_types = sorted(set(departure_types))
        after_match = [seconds for seconds, _ in departure_types if seconds >= kickoff_seconds + ASSUMED_MATCH_MIN * 60]
        event_mode_counts: Counter[int] = Counter(route_type for _, route_type in departure_types)
        mode_counts.update(event_mode_counts)
        event_capacity = {
            band: sum(
                count * MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])[band]
                for mode, count in event_mode_counts.items()
            )
            for band in ("low", "base", "high")
        }
        results.append(
            {
                "match_id": event["match_id"],
                "kickoff_local": event["kickoff_local"],
                "calendar_valid": bool(active),
                "departures": len(departure_types),
                "latest_departure_seconds": max((seconds for seconds, _ in departure_types), default=None),
                "service_span_after_match_min": round(
                    (max(after_match) - kickoff_seconds - ASSUMED_MATCH_MIN * 60) / 60, 1
                ) if after_match else 0.0,
                "mode_departures": {
                    MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])["mode"]: count
                    for mode, count in sorted(event_mode_counts.items())
                },
                "capacity_low": event_capacity["low"],
                "capacity_base": event_capacity["base"],
                "capacity_high": event_capacity["high"],
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
            venue_ids, _ = _venue_stop_ids(stops, venue, SERVICE_RADIUS_MILES)
            rows, counts = _event_departures(
                stop_times, trips, routes, optional["frequencies.txt"], services, venue_ids, events
            )
            event_rows.extend(rows)
            mode_counts.update(counts)
    stops = pd.concat(aggregate_stops, ignore_index=True).drop_duplicates("stop_id") if aggregate_stops else pd.DataFrame()
    venue_ids, nearby = _venue_stop_ids(stops, venue)
    capacity = {
        band: sum(count * MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])[band] for mode, count in mode_counts.items())
        for band in ("low", "base", "high")
    }
    if not events:
        event_departures: int | None = scheduled_departures if "valid" in validities else None
    else:
        event_departures = sum(row["departures"] for row in event_rows) if "valid" in validities else None
    return {
        "stops": stops,
        "route_count": len(route_ids),
        "scheduled_departures": scheduled_departures,
        "event_window_departures": event_departures,
        "event_departures_by_match": event_rows,
        "service_span_after_match_min": max((row["service_span_after_match_min"] for row in event_rows), default=None),
        "calendar_validity": "valid" if "valid" in validities else ("outside_event_window" if validities else "unavailable"),
        "service_span": {
            "start_date": min(calendar_starts) if calendar_starts else None,
            "end_date": max(calendar_ends) if calendar_ends else None,
        },
        "required_files": required_status,
        "optional_files": optional_status,
        "venue_stop_count": len(venue_ids),
        "nearest_stop_mi": round(float(nearby["distance_mi"].min()), 3) if not nearby.empty else None,
        "mode_departures": {
            MODE_CAPACITY_RANGES.get(mode, MODE_CAPACITY_RANGES[3])["mode"]: count for mode, count in sorted(mode_counts.items())
        },
        "capacity": capacity,
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
    distances = haversine_miles(float(venue["lat"]), float(venue["lon"]), work["stop_lat"].to_numpy(), work["stop_lon"].to_numpy())
    return {
        "stops_0_25mi": int((distances <= 0.25).sum()),
        "stops_0_5mi": int((distances <= 0.5).sum()),
        "stops_1mi": int((distances <= 1).sum()),
        "stops_2mi": int((distances <= 2).sum()),
        "stops_5mi": int((distances <= 5).sum()),
        "nearest_stop_mi": round(float(distances.min()), 3) if len(distances) else None,
        "stop_points_2mi": [
            {"lat": round(float(row.stop_lat), 6), "lon": round(float(row.stop_lon), 6)}
            for row in nearby.itertuples(index=False)
        ],
    }


def fetch_city(city: str, feeds: list[tuple[str, str]], events: list[dict[str, Any]]) -> dict[str, Any]:
    venue = HOST_CITIES[city]
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    feed_results = []
    all_stops = []
    totals: Counter[str] = Counter()
    capacities: Counter[str] = Counter()
    calendars = []
    spans_after = []
    optional_presence: dict[str, bool] = defaultdict(bool)
    match_evidence: dict[str, dict[str, Any]] = {}
    for agency, url in feeds:
        base = {"agency": agency, "url": url, "retrieved_at_utc": retrieved_at, "status": "unavailable", "sha256": None}
        try:
            response = requests.get(url, headers=HEADERS, timeout=120)
            response.raise_for_status()
            payload = response.content
            extracted = extract_feed(payload, venue, events)
            complete = all(extracted["required_files"].values())
            valid = extracted["calendar_validity"] == "valid"
            status = "observed" if complete and valid else "partial"
            feed_results.append(
                {
                    **base,
                    "status": status,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "required_files": extracted["required_files"],
                    "optional_files": extracted["optional_files"],
                    "calendar_validity": extracted["calendar_validity"],
                    "service_span": extracted["service_span"],
                }
            )
            all_stops.append(extracted["stops"])
            totals.update(
                route_count=extracted["route_count"],
                scheduled_departures=extracted["scheduled_departures"],
                event_window_departures=extracted["event_window_departures"] or 0,
            )
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
                        },
                    )
                    current["event_window_departures"] += int(event_row["departures"])
                    for level in ("low", "base", "high"):
                        current[f"event_capacity_{level}"] += int(event_row[f"capacity_{level}"])
                    current["service_span_after_match_min"] = max(
                        float(current["service_span_after_match_min"]),
                        float(event_row["service_span_after_match_min"]),
                    )
            for name, present in extracted["optional_files"].items():
                optional_presence[name] |= present
        except (requests.RequestException, zipfile.BadZipFile, OSError, ValueError) as exc:
            feed_results.append({**base, "error": str(exc)[:500]})
    stops = pd.concat(all_stops, ignore_index=True).drop_duplicates("stop_id") if all_stops else pd.DataFrame()
    status = (
        "observed" if feed_results and all(feed["status"] == "observed" for feed in feed_results)
        else "partial" if any(feed["status"] in {"observed", "partial"} for feed in feed_results)
        else "unavailable"
    )
    for row in match_evidence.values():
        row["status"] = "partial" if status == "partial" else "observed"
    return {
        **count_near_venue(stops, venue),
        "city": city,
        "venue": venue["venue"],
        "venue_lat": venue["lat"],
        "venue_lon": venue["lon"],
        "agencies": [agency for agency, _ in feeds],
        "total_agency_stops": len(stops),
        "route_count": totals["route_count"],
        "scheduled_departures": totals["scheduled_departures"],
        "event_window_departures": totals["event_window_departures"] if status != "unavailable" else None,
        "service_span_after_match_min": max(spans_after) if spans_after else None,
        "calendar_validity": "valid" if "valid" in calendars else "unavailable",
        "optional_files": dict(optional_presence),
        "event_capacity_low": capacities["low"],
        "event_capacity_base": capacities["base"],
        "event_capacity_high": capacities["high"],
        "matches": match_evidence,
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
    maximum = max((value for city, value in raw_values.items() if results[city].get("feed_status") != "unavailable"), default=0)
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
            "feeds": [
                {"agency": agency, "url": url, "status": "unavailable", "sha256": None, "retrieved_at_utc": None}
                for agency, url in GTFS_FEEDS[city]
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
        "status": "unavailable" if fixture else (
            "observed" if all(row["feed_status"] == "observed" for row in results.values())
            else "partial" if any(row["feed_status"] != "unavailable" for row in results.values())
            else "unavailable"
        ),
        "fixture": fixture,
        "cities": results,
        "mode_capacity_ranges": MODE_CAPACITY_RANGES,
        "policy": {
            "legacy_cache": "never loaded or promoted",
            "observed_gate": "required files, event-valid calendar, retrieval timestamp, and feed SHA-256",
            "capacity_status": "scenario capacity range; not observed ridership",
            "event_window_minutes": {"before": WINDOW_BEFORE_MIN, "after": WINDOW_AFTER_MIN},
            "venue_radius_miles": VENUE_RADIUS_MILES,
            "service_capacity_radius_miles": SERVICE_RADIUS_MILES,
        },
    }
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return write_json(output, snapshot)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Explicitly download and pin configured GTFS feeds")
    mode.add_argument("--fixture", action="store_true", help="Write a deterministic unavailable fixture without network")
    parser.add_argument("--schedule", type=Path, default=Path("data/snapshots/fifa/fifa_2026_us_schedule.json"))
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/gtfs/gtfs_venue_access.json"))
    args = parser.parse_args()
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") if args.refresh else "2026-08-01T00:00:00Z"
    if args.fixture:
        results = unavailable_fixture()
    else:
        schedule = load_schedule_snapshot(args.schedule)
        by_city = {city: [event for event in schedule["events"] if event["city"] == city] for city in HOST_CITIES}
        results = score_results({city: fetch_city(city, feeds, by_city[city]) for city, feeds in GTFS_FEEDS.items()})
    digest = write_snapshot(results, args.output, generated_at, fixture=args.fixture)
    print(json.dumps({"output": str(args.output), "status": "fixture" if args.fixture else "refreshed", "file_sha256": digest}))


if __name__ == "__main__":
    main()
