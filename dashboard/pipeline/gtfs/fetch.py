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


def extract_feed(payload: bytes) -> dict[str, object]:
    stops: list[pd.DataFrame] = []
    route_count = 0
    departures = 0
    service_hours: set[int] = set()
    required_status: dict[str, bool] = {}
    with zipfile.ZipFile(io.BytesIO(payload)) as outer:
        for zf in _nested_zips(outer):
            stop_df = _read_table(zf, "stops.txt", ["stop_lat", "stop_lon", "stop_id"])
            if not stop_df.empty:
                stops.append(stop_df.dropna(subset=["stop_lat", "stop_lon"])[["stop_lat", "stop_lon"]])
            routes = _read_table(zf, "routes.txt", ["route_id"])
            route_count += int(routes["route_id"].nunique()) if not routes.empty else 0
            stop_times = _read_table(zf, "stop_times.txt", ["departure_time"])
            if not stop_times.empty and "departure_time" in stop_times:
                parsed = stop_times["departure_time"].astype(str).str.extract(r"^(\d+):")[0]
                hours = pd.to_numeric(parsed, errors="coerce").dropna().astype(int) % 24
                departures += len(hours)
                service_hours.update(hours.tolist())
            for required in ("stops.txt", "routes.txt", "trips.txt", "stop_times.txt"):
                required_status[required] = required_status.get(required, False) or _find_member(zf, required) is not None
    combined = pd.concat(stops, ignore_index=True).drop_duplicates().reset_index(drop=True) if stops else pd.DataFrame(columns=["stop_lat", "stop_lon"])
    return {
        "stops": combined,
        "route_count": route_count,
        "departures": departures,
        "service_hours": sorted(service_hours),
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


def fetch_city(city: str, feeds: list[tuple[str, str]]) -> dict[str, object]:
    feed_results = []
    all_stops = []
    route_count = 0
    departures = 0
    service_hours: set[int] = set()
    for agency, url in feeds:
        result: dict[str, object] = {"agency": agency, "url": url, "status": "unavailable"}
        try:
            response = requests.get(url, headers=HEADERS, timeout=120)
            response.raise_for_status()
            payload = response.content
            extracted = extract_feed(payload)
            feed_results.append({**result, "status": "observed", "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload), "required_files": extracted["required_files"]})
            if not extracted["stops"].empty:
                all_stops.append(extracted["stops"])
            route_count += int(extracted["route_count"])
            departures += int(extracted["departures"])
            service_hours.update(extracted["service_hours"])
        except (requests.RequestException, zipfile.BadZipFile, OSError, ValueError) as exc:
            feed_results.append({**result, "error": str(exc)})
    stops = pd.concat(all_stops, ignore_index=True).drop_duplicates() if all_stops else pd.DataFrame(columns=["stop_lat", "stop_lon"])
    venue = HOST_CITIES[city]
    score_parts = count_near_venue(stops, venue)
    score_parts.update({
        "city": city,
        "venue": venue["venue"],
        "venue_lat": venue["lat"],
        "venue_lon": venue["lon"],
        "agencies": [agency for agency, _ in feeds],
        "total_agency_stops": int(len(stops)),
        "route_count": int(route_count),
        "scheduled_departures": int(departures),
        "service_hours": sorted(service_hours),
        "feed_status": "observed" if any(feed["status"] == "observed" for feed in feed_results) else "unavailable",
        "feeds": feed_results,
    })
    return score_parts


def score_results(results: dict[str, dict[str, object]]) -> dict[str, dict[str, object]]:
    raw_values = {}
    for city, row in results.items():
        raw = (
            int(row["stops_0_25mi"]) * 20
            + int(row["stops_0_5mi"]) * 10
            + int(row["stops_1mi"]) * 5
            + int(row["stops_2mi"]) * 2
            + min(int(row["route_count"]), 20) * 2
        )
        raw_values[city] = raw
        row["raw_score"] = raw
    maximum = max(raw_values.values(), default=0)
    for city, row in results.items():
        if row["feed_status"] == "unavailable":
            row["gtfs_transit_score"] = None
            row["score_status"] = "unavailable"
        else:
            row["gtfs_transit_score"] = round(raw_values[city] / maximum * 100) if maximum else 0
            row["score_status"] = "observed"
    return results


def write_snapshot(results: dict[str, dict[str, object]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cities": results,
        "policy": {
            "score_formula": "20*stops_0_25mi + 10*stops_0_5mi + 5*stops_1mi + 2*stops_2mi + 2*min(route_count,20), normalized to observed maximum",
            "missing_feed_policy": "unavailable; never replaced with expert score",
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
