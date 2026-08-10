"""Build and validate compact traffic-management source-audit overlays.

Published overlays preserve exact facilities, service windows, and controls
for provenance. They do not override the normalized generated strategy model.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.common import (
    artifact_hash,
    base_snapshot,
    read_json,
    sha256_bytes,
    validate_source,
    write_json,
)

SCHEMA_VERSION = "1.0.0"
DEFAULT_RAW_ROOT = Path("data/raw/operations")
DEFAULT_OUTPUT = Path("data/snapshots/operations/world_cup_2026_traffic_management.json")
HEADERS = {"User-Agent": "Mobility-Readiness-Platform/0.3 traffic-plan evidence refresh"}

SOURCE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "dallas_fwc26_transportation_plan": {
        "city": "Dallas",
        "source": "FIFA World Cup 26 Dallas Transportation & Mobility Plan",
        "url": "https://www.dallasfwc26.com/dallas-2026/transportation-mobility/",
        "publisher": "North Texas FIFA World Cup Organizing Committee",
        "version": "Published World Cup 2026 transportation plan; accessed 2026-08-09",
        "license": "Official public information; retain publisher attribution and source terms",
        "coverage_start": "2026-05-26",
        "coverage_end": "2026-07-23",
        "status": "observed",
        "raw_filename": "dallas_fwc26_transportation_mobility.html",
        "verification_terms": ("CentrePort", "Dynamic Charter Buses", "Griffin Street"),
    }
}

PUBLISHED_PLANS: dict[str, dict[str, Any]] = {
    "Dallas": {
        "city": "Dallas",
        "status": "observed",
        "primary_pattern": "Regional rail to charter-bus bridge",
        "modeled_measure": "Shuttle service",
        "arrival_window": "5 hours before kickoff through kickoff",
        "egress_window": "Match end through 3 hours after",
        "transfer_hubs": [
            {
                "name": "Victory Station",
                "role": "origin rail hub",
                "lat": 32.789607,
                "lon": -96.812513,
                "status": "observed",
            },
            {
                "name": "Fort Worth Central Station",
                "role": "origin rail hub",
                "lat": 32.751796,
                "lon": -97.325397,
                "status": "observed",
            },
            {
                "name": "TRE CentrePort/DFW Airport Station",
                "role": "primary transfer",
                "lat": 32.81701,
                "lon": -97.05294,
                "status": "observed",
            },
        ],
        "trunk_instruction": (
            "Route ticket holders by TRE from Victory Station or Fort Worth Central Station to "
            "CentrePort, then transfer to complimentary charter buses serving the stadium bus hub."
        ),
        "curb_location": "Arlington Esports Stadium rideshare and taxi lot",
        "curb_instruction": (
            "Keep rideshare and taxi loading in the published Arlington Esports Stadium lot; "
            "direct private cars and shuttles to their separate published operating area."
        ),
        "egress_instruction": (
            "Return ticket holders by charter bus to CentrePort for TRE service; preserve the "
            "published walk from the stadium to the bus hub and separate rideshare route."
        ),
        "overflow_trigger": (
            "Dispatch dynamic charter buses from Victory or Fort Worth Central when TRE reaches "
            "capacity and passenger lines form."
        ),
        "accessible_operations": ("ADA-accessible vans at CentrePort and accessible carts at the stadium bus hub"),
        "published_controls": [
            "AT&T Way closed from Cowboys Way to Randol Mill Road on match days",
            "Cowboys Way closed from North Collins Street to AT&T Way on match days",
            "A portion of Nolan Ryan Expressway closed from Road to Six Flags to the hotel south entrance",
            "A portion of Statler Boulevard closed near CentrePort Station",
            "Rideshare/taxi, private shuttle, charter bus, and pedestrian channels are separated",
        ],
        "source_ids": ["dallas_fwc26_transportation_plan"],
        "source_locators": [
            "Match Day Transit",
            "Dallas Stadium Road Closures",
            "Pedestrian Walking Routes",
            "CentrePort Station Road Closures",
        ],
    }
}


def missing_verification_terms(definition: dict[str, Any], payload: bytes) -> list[str]:
    text = payload.decode("utf-8", errors="ignore").casefold()
    return [str(term) for term in definition.get("verification_terms", ()) if str(term).casefold() not in text]


def _source_record(
    source_id: str,
    definition: dict[str, Any],
    payload: bytes,
    retrieved_at: str,
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        **{
            key: definition[key]
            for key in (
                "source",
                "url",
                "publisher",
                "version",
                "license",
                "coverage_start",
                "coverage_end",
                "status",
            )
        },
        "retrieved_at_utc": retrieved_at,
        "sha256": sha256_bytes(payload),
        "hash_scope": "Raw HTTP response bytes retained in ignored data/raw/operations",
        "verification_terms": list(definition.get("verification_terms", ())),
    }


def build_snapshot(raw_root: Path, *, refresh: bool) -> dict[str, Any]:
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    sources: dict[str, dict[str, Any]] = {}
    for source_id, definition in SOURCE_DEFINITIONS.items():
        raw_path = raw_root / str(definition["raw_filename"])
        if refresh:
            response = requests.get(str(definition["url"]), headers=HEADERS, timeout=120)
            response.raise_for_status()
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(response.content)
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing traffic-plan source response: {raw_path}")
        payload = raw_path.read_bytes()
        missing = missing_verification_terms(definition, payload)
        if missing:
            raise ValueError(f"Source review terms are missing for {source_id}: {', '.join(missing)}")
        sources[source_id] = _source_record(source_id, definition, payload, retrieved_at)

    coverage = {
        city: {
            "published_plan_available": city in PUBLISHED_PLANS,
            "source_ids": list(PUBLISHED_PLANS.get(city, {}).get("source_ids", [])),
            "fallback": (
                "common derived strategy; published facts retained for source audit"
                if city in PUBLISHED_PLANS
                else "derived strategy from pinned GTFS, movement, access, and intervention evidence"
            ),
        }
        for city in HOST_CITIES
    }
    snapshot = base_snapshot("world_cup_traffic_management_plans", retrieved_at)
    snapshot.update(
        {
            "schema_version": SCHEMA_VERSION,
            "status": "partial",
            "sources": sources,
            "plans": PUBLISHED_PLANS,
            "city_coverage": coverage,
            "policy": {
                "runtime": "cache-only; no source request during dashboard use",
                "precedence": "generated plans are never overridden by a city-specific source-audit overlay",
                "generated_locations": "candidate only; never an approved hub, curb, lot, or closure",
                "roadway_claims": "no speed, delay, signal, queue, or congestion claim without observed roadway evidence",
            },
        }
    )
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Traffic-management snapshot contract mismatch")
    if snapshot.get("snapshot_kind") != "world_cup_traffic_management_plans":
        raise ValueError("Unexpected traffic-management snapshot kind")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unexpected traffic-management schema version")
    if snapshot.get("artifact_sha256") != artifact_hash(snapshot):
        raise ValueError("Traffic-management snapshot content hash mismatch")
    if set(snapshot.get("city_coverage", {})) != set(HOST_CITIES):
        raise ValueError("Traffic-management coverage must include all host cities")
    sources = snapshot.get("sources")
    plans = snapshot.get("plans")
    if not isinstance(sources, dict) or not isinstance(plans, dict):
        raise ValueError("Traffic-management snapshot requires sources and plans")
    for source in sources.values():
        validate_source(source)
        if not source.get("verification_terms"):
            raise ValueError("Traffic-management sources require verification terms")
    for city, plan in plans.items():
        if city not in HOST_CITIES or str(plan.get("city")) != city:
            raise ValueError("Traffic-management plan city mismatch")
        source_ids = plan.get("source_ids")
        if (
            not isinstance(source_ids, list)
            or not source_ids
            or any(source_id not in sources for source_id in source_ids)
        ):
            raise ValueError(f"Traffic-management plan has invalid source references: {city}")
        if not plan.get("primary_pattern") or not plan.get("transfer_hubs"):
            raise ValueError(f"Traffic-management plan is incomplete: {city}")


def load_snapshot(path: Path | str = DEFAULT_OUTPUT) -> dict[str, Any]:
    snapshot = read_json(Path(path))
    validate_snapshot(snapshot)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--refresh", action="store_true", help="Fetch official sources and rebuild the snapshot")
    mode.add_argument("--validate", action="store_true", help="Validate the checked snapshot")
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    snapshot = build_snapshot(args.raw_root, refresh=True) if args.refresh else read_json(args.output)
    validate_snapshot(snapshot)
    digest = write_json(args.output, snapshot) if args.refresh else sha256_bytes(args.output.read_bytes())
    print({"status": snapshot["status"], "plans": len(snapshot["plans"]), "sha256": digest})


if __name__ == "__main__":
    main()
