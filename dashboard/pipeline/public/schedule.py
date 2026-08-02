"""Build a compact U.S. host-city schedule from FIFA's pinned public API response."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dateutil.tz import gettz

from dashboard.mobility_platform.contracts import EvidenceStatus, MatchEvent, SourceReference
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import artifact_hash, base_snapshot, sha256_bytes, write_json

FIFA_SEASON_ID = "285023"
FIFA_API_URL = (
    "https://api.fifa.com/api/v3/calendar/matches?language=en&count=500&idSeason=" + FIFA_SEASON_ID
)
FIFA_SCHEDULE_URL = (
    "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/"
    "articles/match-schedule-fixtures-results-teams-stadiums"
)

CITY_ALIASES = {
    "Atlanta": "Atlanta",
    "Boston": "Boston",
    "Dallas": "Dallas",
    "Houston": "Houston",
    "Kansas City": "Kansas City",
    "Los Angeles": "Los Angeles",
    "Miami": "Miami",
    "New Jersey": "New York/NJ",
    "New York New Jersey": "New York/NJ",
    "Philadelphia": "Philadelphia",
    "San Francisco Bay Area": "San Francisco",
    "Seattle": "Seattle",
}

CITY_TIMEZONES = {
    "Atlanta": "America/New_York",
    "Boston": "America/New_York",
    "Dallas": "America/Chicago",
    "Houston": "America/Chicago",
    "Kansas City": "America/Chicago",
    "Los Angeles": "America/Los_Angeles",
    "Miami": "America/New_York",
    "New York/NJ": "America/New_York",
    "Philadelphia": "America/New_York",
    "San Francisco": "America/Los_Angeles",
    "Seattle": "America/Los_Angeles",
}


def _description(value: object) -> str:
    if not isinstance(value, list):
        return ""
    english = next(
        (row for row in value if isinstance(row, dict) and str(row.get("Locale", "")).lower().startswith("en")),
        None,
    )
    row = english or next((row for row in value if isinstance(row, dict)), {})
    return str(row.get("Description", ""))


def _stage(row: dict[str, Any]) -> str:
    group = _description(row.get("GroupName"))
    if group:
        return group
    stage = _description(row.get("StageName"))
    return stage.replace("First Stage", "Group stage") or "Unknown"


def build_schedule(raw_payload: bytes, retrieved_at_utc: str) -> dict[str, Any]:
    raw = json.loads(raw_payload)
    rows = raw.get("Results")
    if not isinstance(rows, list):
        raise ValueError("FIFA response does not contain a Results list")

    source = SourceReference(
        source="FIFA World Cup 2026 official match API",
        url=FIFA_API_URL,
        publisher="Fédération Internationale de Football Association (FIFA)",
        retrieved_at_utc=retrieved_at_utc,
        version=f"season-{FIFA_SEASON_ID}",
        sha256=sha256_bytes(raw_payload),
        license="FIFA terms of use; schedule facts retained for attribution and planning",
        coverage_start="2026-06-11",
        coverage_end="2026-07-19",
        status=EvidenceStatus.OBSERVED,
        notes=f"Human-readable official schedule: {FIFA_SCHEDULE_URL}",
    )
    source_dict = source.to_dict()
    source_dict["hash_scope"] = "raw FIFA API response bytes"
    events: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("IdSeason")) != FIFA_SEASON_ID:
            continue
        stadium = row.get("Stadium")
        if not isinstance(stadium, dict) or stadium.get("IdCountry") != "USA":
            continue
        city = CITY_ALIASES.get(_description(stadium.get("CityName")))
        if city is None:
            raise ValueError(f"Unmapped U.S. FIFA host city: {_description(stadium.get('CityName'))!r}")
        kickoff_utc = datetime.fromisoformat(str(row["Date"]).replace("Z", "+00:00"))
        venue_timezone = gettz(CITY_TIMEZONES[city])
        if venue_timezone is None:
            raise ValueError(f"IANA timezone is unavailable: {CITY_TIMEZONES[city]}")
        kickoff_local = kickoff_utc.astimezone(venue_timezone).isoformat()
        event = MatchEvent(
            match_id=f"M{int(row['MatchNumber']):03d}",
            city=city,
            venue=str(HOST_CITIES[city]["venue"]),
            kickoff_local=kickoff_local,
            stage=_stage(row),
            capacity=int(HOST_CITIES[city]["capacity"]),
            source=source,
        ).to_dict()
        event.update(
            {
                "fifa_match_id": str(row["IdMatch"]),
                "match_number": int(row["MatchNumber"]),
                "kickoff_utc": kickoff_utc.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                "timezone": CITY_TIMEZONES[city],
                "fifa_venue": _description(stadium.get("Name")),
            }
        )
        events.append(event)
    events.sort(key=lambda event: int(event["match_number"]))

    actual_counts = {city: sum(event["city"] == city for event in events) for city in HOST_CITIES}
    expected_counts = {city: int(metadata["games"]) for city, metadata in HOST_CITIES.items()}
    if actual_counts != expected_counts:
        raise ValueError(f"FIFA schedule city counts differ from frozen host mappings: {actual_counts}")

    snapshot = base_snapshot("fifa_schedule", retrieved_at_utc)
    snapshot.update(
        {
            "status": "observed",
            "source": source_dict,
            "event_count": len(events),
            "city_counts": actual_counts,
            "events": events,
            "policy": {
                "kickoff_policy": "UTC Date converted with IANA venue timezone; LocalDate is not used as an offset",
                "venue_policy": "FIFA host-city aliases map exactly to frozen platform city and venue names",
                "refresh_policy": "Dashboard reads this snapshot only; refresh is an explicit command",
            },
        }
    )
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Pinned FIFA API JSON to transform without network access")
    source.add_argument("--refresh", action="store_true", help="Explicitly fetch the official FIFA API")
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/fifa/fifa_2026_us_schedule.json"))
    parser.add_argument("--retrieved-at", help="Required for --input; ISO-8601 UTC retrieval timestamp")
    args = parser.parse_args()

    if args.refresh:
        response = requests.get(FIFA_API_URL, timeout=120, headers={"User-Agent": "MobilityPlatform/0.3"})
        response.raise_for_status()
        payload = response.content
        retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        if not args.retrieved_at:
            parser.error("--retrieved-at is required with --input for deterministic provenance")
        payload = args.input.read_bytes()
        retrieved_at = args.retrieved_at
    snapshot = build_schedule(payload, retrieved_at)
    file_hash = write_json(args.output, snapshot)
    print(json.dumps({"output": str(args.output), "events": snapshot["event_count"], "file_sha256": file_hash}))


if __name__ == "__main__":
    main()
