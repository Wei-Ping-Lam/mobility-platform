"""Fetch pinned GTFS snapshots and compute venue-level access evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from dashboard.mobility_platform.mappings import HOST_CITIES


GTFS_FEEDS = {
    "Atlanta": [("MARTA", "https://www.itsmarta.com/google_transit_feed/google_transit.zip")],
    "Boston": [("MBTA", "https://cdn.mbta.com/MBTA_GTFS.zip")],
    "Dallas": [("DART", "https://www.dart.org/transitdata/latest/google_transit.zip")],
    "Houston": [("METRO Houston", "https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip")],
    "Kansas City": [("RideKC/KCATA", "http://www.kc-metro.com/gtf/google_transit.zip")],
    "Los Angeles": [
        ("LA Metro Rail", "https://gitlab.com/LACMTA/gtfs_rail/raw/master/gtfs_rail.zip"),
        ("LA Metro Bus", "https://gitlab.com/LACMTA/gtfs_bus/-/raw/master/gtfs_bus.zip"),
    ],
    "Miami": [("MDT", "https://www.miamidade.gov/transit/googletransit/current/google_transit.zip")],
    "New York/NJ": [("NJ Transit", "https://www.njtransit.com/rail_data.zip")],
    "Philadelphia": [
        ("SEPTA Rail", "https://github.com/septadev/GTFS/releases/latest/download/google_rail.zip"),
        ("SEPTA Bus", "https://github.com/septadev/GTFS/releases/latest/download/google_bus.zip"),
    ],
    "San Francisco": [("VTA", "https://gtfs.vta.org/gtfs_vta.zip")],
    "Seattle": [
        ("Sound Transit", "https://gtfs.sound.obaweb.org/prod/40_gtfs.zip"),
        ("King Co Metro", "https://metro.kingcounty.gov/GTFS/google_transit.zip"),
    ],
}

HEADERS = {"User-Agent": "Mobility-Readiness-Platform/0.2"}
EVENT_WINDOW_START = pd.Timestamp("2026-06-11")
EVENT_WINDOW_END = pd.Timestamp("2026-07-19")


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
                continue
    return result


def _find_member(zf: zipfile.ZipFile, filename: str) -> str | None:
    return next((name for name in zf.namelist() if name.lower().endswith(filename)), None)


def _read_table(zf: zipfile.ZipFile, filename: str, usecols: list[str] | None = None) -> pd.DataFrame:
    member = _find_member(zf, filename)
    if member is None:
        return pd.DataFrame()
    try:
        return pd.read_csv(zf.open(member), usecols=usecols)
    except (OSError, ValueError, pd.errors.ParserError):
        return pd.DataFrame()


def _parse_gtfs_dates(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_datetime(frame[column].astype(str), format="%Y%m%d", errors="coerce")


def _calendar_details(zf: zipfile.ZipFile) -> dict[str, object]:
    calendar = _read_table(zf, "calendar.txt", ["service_id", "start_date", "end_date"])
    calendar_dates = _read_table(zf, "calendar_dates.txt", ["service_id", "date", "exception_type"])
    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp] = []
    event_services: set[object] = set()

    if not calendar.empty:
        calendar["start"] = _parse_gtfs_dates(calendar, "start_date")
        calendar["end"] = _parse_gtfs_dates(calendar, "end_date")
        valid_rows = calendar.dropna(subset=["start", "end"])
        starts.extend(valid_rows["start"].tolist())
        ends.extend(valid_rows["end"].tolist())
        event_services.update(
            valid_rows.loc[
                (valid_rows["start"] <= EVENT_WINDOW_END) & (valid_rows["end"] >= EVENT_WINDOW_START),
                "service_id",
            ].tolist()
        )

    if not calendar_dates.empty:
        calendar_dates["service_date"] = _parse_gtfs_dates(calendar_dates, "date")
        valid_dates = calendar_dates.dropna(subset=["service_date"])
        starts.extend(valid_dates["service_date"].tolist())
        ends.extend(valid_dates["service_date"].tolist())
        event_dates = valid_dates[
            valid_dates["service_date"].between(EVENT_WINDOW_START, EVENT_WINDOW_END, inclusive="both")
        ]
        for _, row in event_dates.iterrows():
            exception_type = int(pd.to_numeric(pd.Series([row.get("exception_type")]), errors="coerce").fillna(0).iloc[0])
            if exception_type == 1:
                event_services.add(row["service_id"])
            elif exception_type == 2:
                event_services.discard(row["service_id"])

    if not starts or not ends:
        validity = "unavailable"
        start_date = end_date = None
    else:
        validity = "valid" if event_services else "outside_event_window"
        start_date = min(starts).date().isoformat()
        end_date = max(ends).date().isoformat()
    return {
        "calendar_validity": validity,
        "calendar_start": start_date,
        "calendar_end": end_date,
        "event_service_ids": event_services,
    }
def extract_feed(payload: bytes) -> dict[str, object]:
    stops: list[pd.DataFrame] = []
    route_count = 0
    departures = 0
    event_window_departures: int | None = 0
    service_hours: set[int] = set()
    required_status: dict[str, bool] = {}
    calendar_validities: list[str] = []
    calendar_starts: list[str] = []
    calendar_ends: list[str] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as outer:
        for zf in _nested_zips(outer):
            stop_df = _read_table(zf, "stops.txt", ["stop_lat", "stop_lon", "stop_id"])
            if not stop_df.empty:
                stops.append(stop_df.dropna(subset=["stop_lat", "stop_lon"])[["stop_lat", "stop_lon"]])
            routes = _read_table(zf, "routes.txt", ["route_id"])
            route_count += int(routes["route_id"].nunique()) if not routes.empty else 0
            calendar = _calendar_details(zf)
            calendar_validities.append(str(calendar["calendar_validity"]))
            if calendar["calendar_start"]:
                calendar_starts.append(str(calendar["calendar_start"]))
            if calendar["calendar_end"]:
                calendar_ends.append(str(calendar["calendar_end"]))
            stop_times = _read_table(zf, "stop_times.txt", ["trip_id", "departure_time"])
            if not stop_times.empty and "departure_time" in stop_times:
                parsed = stop_times["departure_time"].astype(str).str.extract(r"^(\d+):")[0]
                hours = pd.to_numeric(parsed, errors="coerce").dropna().astype(int) % 24
                departures += len(hours)
                service_hours.update(hours.tolist())
                if calendar["event_service_ids"]:
                    trips = _read_table(zf, "trips.txt", ["trip_id", "service_id"])
                    if not trips.empty and "trip_id" in stop_times and not trips.empty:
                        event_trip_ids = set(trips.loc[trips["service_id"].isin(calendar["event_service_ids"]), "trip_id"])
                        event_window_departures += int(stop_times["trip_id"].isin(event_trip_ids).sum())
                else:
                    event_window_departures = None
            for required in ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt"):
                required_status[required] = required_status.get(required, False) or _find_member(zf, required) is not None
    combined = pd.concat(stops, ignore_index=True).drop_duplicates().reset_index(drop=True) if stops else pd.DataFrame(columns=["stop_lat", "stop_lon"])
    return {
        "stops": combined,
        "route_count": route_count,
        "departures": departures,
        "service_hours": sorted(service_hours),
        "event_window_departures": event_window_departures,
        "calendar_validity": "valid" if "valid" in calendar_validities else ("outside_event_window" if calendar_validities and "unavailable" not in calendar_validities else "unavailable"),
        "service_span": {
            "start_date": min(calendar_starts) if calendar_starts else None,
            "end_date": max(calendar_ends) if calendar_ends else None,
        },
        "required_files": required_status,
    }


def count_near_venue(stops: pd.DataFrame, venue: dict[str, object]) -> dict[str, object]:
    if stops.empty:
        return {
            "stops_0_25mi": 0, "stops_0_5mi": 0, "stops_1mi": 0, "stops_2mi": 0,
            "stops_5mi": 0, "nearest_stop_mi": None,
        }
    distances = haversine_miles(float(venue["lat"]), float(venue["lon"]), stops["stop_lat"].to_numpy(), stops["stop_lon"].to_numpy())
    return {
        "stops_0_25mi": int((distances <= 0.25).sum()),
        "stops_0_5mi": int((distances <= 0.5).sum()),
        "stops_1mi": int((distances <= 1.0).sum()),
        "stops_2mi": int((distances <= 2.0).sum()),
        "stops_5mi": int((distances <= 5.0).sum()),
        "nearest_stop_mi": round(float(distances.min()), 3),
    }


def points_near_venue(stops: pd.DataFrame, venue: dict[str, object], radius_miles: float = 2.0) -> list[dict[str, float]]:
    if stops.empty:
        return []
    distances = haversine_miles(float(venue["lat"]), float(venue["lon"]), stops["stop_lat"].to_numpy(), stops["stop_lon"].to_numpy())
    nearby = stops.loc[distances <= radius_miles, ["stop_lat", "stop_lon"]]
    return [{"lat": round(float(row.stop_lat), 6), "lon": round(float(row.stop_lon), 6)} for row in nearby.itertuples(index=False)]


def fetch_city(city: str, feeds: list[tuple[str, str]]) -> dict[str, object]:
    feed_results = []
    all_stops = []
    route_count = 0
    departures = 0
    event_window_departures: int | None = 0
    service_hours: set[int] = set()
    calendar_validities: list[str] = []
    service_starts: list[str] = []
    service_ends: list[str] = []
    for agency, url in feeds:
        result: dict[str, object] = {"agency": agency, "url": url, "status": "unavailable"}
        try:
            response = requests.get(url, headers=HEADERS, timeout=120)
            response.raise_for_status()
            payload = response.content
            extracted = extract_feed(payload)
            required_complete = all(
                bool(extracted["required_files"].get(required))
                for required in ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt")
            )
            feed_results.append({
                **result,
                "status": "observed" if required_complete else "partial",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "required_files": extracted["required_files"],
                "calendar_validity": extracted["calendar_validity"],
                "service_span": extracted["service_span"],
                "event_window_departures": extracted["event_window_departures"],
            })
            if not extracted["stops"].empty:
                all_stops.append(extracted["stops"])
            route_count += int(extracted["route_count"])
            departures += int(extracted["departures"])
            if extracted["event_window_departures"] is None:
                event_window_departures = None
            elif event_window_departures is not None:
                event_window_departures += int(extracted["event_window_departures"])
            service_hours.update(extracted["service_hours"])
            calendar_validities.append(str(extracted["calendar_validity"]))
            span = extracted["service_span"]
            if span["start_date"]:
                service_starts.append(str(span["start_date"]))
            if span["end_date"]:
                service_ends.append(str(span["end_date"]))
        except (requests.RequestException, zipfile.BadZipFile, OSError, ValueError) as exc:
            feed_results.append({**result, "error": str(exc)})
    stops = pd.concat(all_stops, ignore_index=True).drop_duplicates() if all_stops else pd.DataFrame(columns=["stop_lat", "stop_lon"])
    venue = HOST_CITIES[city]
    score_parts = count_near_venue(stops, venue)
    score_parts["stop_points_2mi"] = points_near_venue(stops, venue)
    score_parts.update({
        "city": city,
        "venue": venue["venue"],
        "venue_lat": venue["lat"],
        "venue_lon": venue["lon"],
        "agencies": [agency for agency, _ in feeds],
        "total_agency_stops": int(len(stops)),
        "route_count": int(route_count),
        "scheduled_departures": int(departures),
        "event_window_departures": event_window_departures,
        "service_hours": sorted(service_hours),
        "calendar_validity": "valid" if "valid" in calendar_validities else ("outside_event_window" if calendar_validities and "unavailable" not in calendar_validities else "unavailable"),
        "service_span": {
            "start_date": min(service_starts) if service_starts else None,
            "end_date": max(service_ends) if service_ends else None,
        },
        "feed_status": (
            "observed" if feed_results and all(feed["status"] == "observed" for feed in feed_results)
            else "partial" if any(feed["status"] in {"observed", "partial"} for feed in feed_results)
            else "unavailable"
        ),
        "feeds": feed_results,
    })
    return score_parts


def score_results(results: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    raw_values = {}
    for city, row in results.items():
        raw = (
            int(row.get("stops_0_25mi", 0)) * 20
            + int(row.get("stops_0_5mi", 0)) * 10
            + int(row.get("stops_1mi", 0)) * 5
            + int(row.get("stops_2mi", 0)) * 2
            + min(int(row.get("route_count", 0)), 20) * 2
        )
        raw_values[city] = raw
        row["raw_score"] = raw
    maximum = max(raw_values.values(), default=0)
    for city, row in results.items():
        feed_status = str(row.get("feed_status", "unavailable"))
        if feed_status == "unavailable":
            row["gtfs_transit_score"] = None
            row["score_status"] = "unavailable"
        else:
            row["gtfs_transit_score"] = round(raw_values[city] / maximum * 100) if maximum else 0
            row["score_status"] = "partial" if feed_status == "partial" else "observed"
    return results


def write_snapshot(results: dict[str, dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cities": results,
        "policy": {
            "score_formula": "20*stops_0_25mi + 10*stops_0_5mi + 5*stops_1mi + 2*stops_2mi + 2*min(route_count,20), normalized to observed maximum",
            "missing_feed_policy": "unavailable; never replaced with expert score",
            "event_window": {"start": EVENT_WINDOW_START.date().isoformat(), "end": EVENT_WINDOW_END.date().isoformat()},
        },
    }
    (output_dir / "gtfs_transit_scores.json").write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    rows = []
    for city, result in results.items():
        row = {key: value for key, value in result.items() if key not in {"feeds", "service_hours"}}
        row["agencies"] = ", ".join(result["agencies"])
        rows.append(row)
    pd.DataFrame(rows).to_csv(output_dir / "gtfs_transit_scores.csv", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data")
    args = parser.parse_args()
    results = {city: fetch_city(city, feeds) for city, feeds in GTFS_FEEDS.items()}
    write_snapshot(score_results(results), Path(args.output))
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
