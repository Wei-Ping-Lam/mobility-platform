"""
Fetch GTFS stop data for all 11 FIFA 2026 US host cities and compute
transit stop density within 0.5 / 1.0 / 2.0 miles of each venue.

Run once:  python fetch_gtfs.py
Output:    cache/gtfs_transit_scores.json
"""

import requests
import zipfile
import io
import json
import math
import numpy as np
import pandas as pd
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
OUT_FILE = CACHE_DIR / "gtfs_transit_scores.json"
# Permanent copy outside cache/ (won't be lost if cache is cleared)
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_FILE_PERMANENT = DATA_DIR / "gtfs_transit_scores.json"

# Precise venue coordinates
VENUES = {
    "Atlanta":       {"lat": 33.7554,  "lon": -84.4009,  "name": "Mercedes-Benz Stadium"},
    "Boston":        {"lat": 42.0909,  "lon": -71.2643,  "name": "Gillette Stadium, Foxborough"},
    "Dallas":        {"lat": 32.7480,  "lon": -97.0929,  "name": "AT&T Stadium, Arlington"},
    "Houston":       {"lat": 29.6851,  "lon": -95.4106,  "name": "NRG Stadium"},
    "Kansas City":   {"lat": 39.0489,  "lon": -94.4839,  "name": "Arrowhead Stadium"},
    "Los Angeles":   {"lat": 33.9534,  "lon": -118.3387, "name": "SoFi Stadium, Inglewood"},
    "Miami":         {"lat": 25.9579,  "lon": -80.2388,  "name": "Hard Rock Stadium, Miami Gardens"},
    "New York/NJ":   {"lat": 40.8135,  "lon": -74.0745,  "name": "MetLife Stadium, East Rutherford"},
    "Philadelphia":  {"lat": 39.9008,  "lon": -75.1675,  "name": "Lincoln Financial Field"},
    "San Francisco": {"lat": 37.4033,  "lon": -121.9700, "name": "Levi's Stadium, Santa Clara"},
    "Seattle":       {"lat": 47.5952,  "lon": -122.3316, "name": "Lumen Field"},
}

# Primary transit agency GTFS feeds (most relevant to each venue)
GTFS_FEEDS = {
    "Atlanta":       [("MARTA",         "https://www.itsmarta.com/google_transit_feed/google_transit.zip")],
    "Boston":        [("MBTA",          "https://cdn.mbta.com/MBTA_GTFS.zip")],
    "Dallas":        [("DART",          "https://www.dart.org/transitdata/latest/google_transit.zip")],
    "Houston":       [("METRO Houston", "https://metro.resourcespace.com/pages/download.php?ref=4835&ext=zip")],
    "Kansas City":   [("RideKC/KCATA",  "http://www.kc-metro.com/gtf/google_transit.zip")],
    "Los Angeles":   [("LA Metro Rail", "https://gitlab.com/LACMTA/gtfs_rail/raw/master/gtfs_rail.zip"),
                      ("LA Metro Bus",  "https://gitlab.com/LACMTA/gtfs_bus/-/raw/master/gtfs_bus.zip")],
    "Miami":         [("MDT",           "https://www.miamidade.gov/transit/googletransit/current/google_transit.zip")],
    "New York/NJ":   [("NJ Transit",    "https://www.njtransit.com/rail_data.zip")],
    "Philadelphia":  [("SEPTA Rail",    "https://github.com/septadev/GTFS/releases/latest/download/google_rail.zip"),
                      ("SEPTA Bus",     "https://github.com/septadev/GTFS/releases/latest/download/google_bus.zip")],
    "San Francisco": [("VTA",           "https://gtfs.vta.org/gtfs_vta.zip")],
    "Seattle":       [("Sound Transit", "https://gtfs.sound.obaweb.org/prod/40_gtfs.zip"),
                      ("King Co Metro", "https://metro.kingcounty.gov/GTFS/google_transit.zip")],
}

HEADERS = {"User-Agent": "Mozilla/5.0 (FIFA2026-Hackathon-Dashboard/1.0)"}


def haversine_miles(lat1, lon1, lat2_arr, lon2_arr):
    """Vectorized haversine distance in miles."""
    R = 3958.8
    phi1 = math.radians(lat1)
    phi2 = np.radians(lat2_arr)
    dphi = phi2 - phi1
    dlam = np.radians(lon2_arr - lon1)
    a = np.sin(dphi / 2) ** 2 + math.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def _read_stops_from_zip(zf):
    """Extract stops DataFrame from an open ZipFile, handling nested zips."""
    names = zf.namelist()
    stop_file = next((n for n in names if n.endswith("stops.txt")), None)
    if stop_file:
        stops = pd.read_csv(
            zf.open(stop_file),
            usecols=lambda c: c in ("stop_lat", "stop_lon", "stop_id"),
            dtype={"stop_id": str},
        )
        return stops.dropna(subset=["stop_lat", "stop_lon"])[["stop_lat", "stop_lon"]]

    # Handle zip-of-zips (e.g. SEPTA: google_rail.zip / google_bus.zip inside)
    inner_zips = [n for n in names if n.endswith(".zip")]
    frames = []
    for iz in inner_zips:
        try:
            inner = zipfile.ZipFile(io.BytesIO(zf.open(iz).read()))
            sf = next((n for n in inner.namelist() if n.endswith("stops.txt")), None)
            if sf:
                df = pd.read_csv(
                    inner.open(sf),
                    usecols=lambda c: c in ("stop_lat", "stop_lon", "stop_id"),
                    dtype={"stop_id": str},
                ).dropna(subset=["stop_lat", "stop_lon"])[["stop_lat", "stop_lon"]]
                frames.append(df)
        except Exception:
            continue
    if frames:
        return pd.concat(frames).drop_duplicates().reset_index(drop=True)
    return pd.DataFrame()


def fetch_stops_from_url(agency, url):
    """Download a GTFS zip and return stops DataFrame (stop_lat, stop_lon only)."""
    print("    Fetching %s ... " % agency, end="", flush=True)
    try:
        r = requests.get(url, headers=HEADERS, timeout=120, stream=True)
        r.raise_for_status()
        raw = b""
        for chunk in r.iter_content(chunk_size=1024 * 1024):
            raw += chunk
        zf = zipfile.ZipFile(io.BytesIO(raw))
        stops = _read_stops_from_zip(zf)
        if stops.empty:
            print("no stops.txt found")
            return pd.DataFrame()
        print("%s stops loaded" % f"{len(stops):,}")
        return stops
    except Exception as e:
        print("ERROR - %s" % e)
        return pd.DataFrame()


def count_stops_near_venue(stops_df, venue_lat, venue_lon):
    """Count stops within 0.5 / 1.0 / 2.0 / 5.0 miles of venue."""
    if stops_df.empty:
        return {"stops_0_5mi": 0, "stops_1mi": 0, "stops_2mi": 0,
                "stops_5mi": 0, "nearest_stop_mi": 99.0}
    dists = haversine_miles(
        venue_lat, venue_lon,
        stops_df["stop_lat"].values,
        stops_df["stop_lon"].values,
    )
    return {
        "stops_0_5mi": int((dists <= 0.5).sum()),
        "stops_1mi":   int((dists <= 1.0).sum()),
        "stops_2mi":   int((dists <= 2.0).sum()),
        "stops_5mi":   int((dists <= 5.0).sum()),
        "nearest_stop_mi": round(float(dists.min()), 3) if len(dists) else 99,
    }


def main():
    results = {}

    for city, venue in VENUES.items():
        print(f"\n{city} — {venue['name']}")
        feeds = GTFS_FEEDS[city]
        all_stops = []

        for agency, url in feeds:
            stops = fetch_stops_from_url(agency, url)
            if not stops.empty:
                all_stops.append(stops)

        if all_stops:
            combined = pd.concat(all_stops).drop_duplicates().reset_index(drop=True)
        else:
            combined = pd.DataFrame()

        counts = count_stops_near_venue(combined, venue["lat"], venue["lon"])
        counts["total_agency_stops"] = len(combined)
        counts["agencies"] = [a for a, _ in feeds]
        results[city] = counts

        print(f"  -> {counts['stops_0_5mi']} stops <=0.5mi | "
              f"{counts['stops_1mi']} <=1mi | "
              f"{counts['stops_2mi']} <=2mi | "
              f"nearest: {counts['nearest_stop_mi']}mi")

    # --- Derive 0-100 transit access score ---
    # Score = weighted sum of stop counts, normalized so the best city = 100
    for city in results:
        c = results[city]
        raw = (c["stops_0_5mi"] * 10 +
               c["stops_1mi"]   *  5 +
               c["stops_2mi"]   *  2)
        c["raw_score"] = raw

    max_raw = max(r["raw_score"] for r in results.values()) or 1
    for city in results:
        c = results[city]
        # Floor at 5 so even car-dependent venues get a minimal score
        c["gtfs_transit_score"] = max(5, round(c["raw_score"] / max_raw * 100))

    payload = json.dumps(results, indent=2)
    OUT_FILE.write_text(payload)
    OUT_FILE_PERMANENT.write_text(payload)
    print("\nSaved to " + str(OUT_FILE))
    print("       + " + str(OUT_FILE_PERMANENT))

    print("\n=== GTFS TRANSIT SCORES ===")
    ranked = sorted(results.items(), key=lambda x: x[1]["gtfs_transit_score"], reverse=True)
    for city, c in ranked:
        print("  %-20s  score=%3d  0.5mi=%3d  1mi=%3d  2mi=%3d  nearest=%.3fmi" % (
            city, c["gtfs_transit_score"], c["stops_0_5mi"],
            c["stops_1mi"], c["stops_2mi"], c["nearest_stop_mi"]))


if __name__ == "__main__":
    main()
