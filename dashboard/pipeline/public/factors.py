"""Versioned planning-factor registry with primary-source attribution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dashboard.mobility_platform.contracts import EvidenceStatus, SourceReference
from dashboard.pipeline.public.common import artifact_hash, base_snapshot, sha256_bytes, write_json

RETRIEVED_AT = "2026-08-01T00:00:00Z"

SOURCE_DEFINITIONS = {
    "epa": {
        "source": "EPA Greenhouse Gas Equivalencies Calculator methodology",
        "url": "https://www.epa.gov/energy/greenhouse-gas-equivalencies-calculator-calculations-and-references",
        "publisher": "U.S. Environmental Protection Agency",
        "version": "2024-methodology",
        "license": "U.S. federal government public information",
        "notes": "EPA publishes 0.393 kg CO2e/mile for a typical gasoline passenger vehicle and 10.180 kg CO2/gallon diesel.",
    },
    "fta_ntd": {
        "source": "2024 National Transit Database annual data products",
        "url": "https://www.transit.dot.gov/ntd",
        "publisher": "Federal Transit Administration",
        "version": "report-year-2024",
        "license": "U.S. Department of Transportation public data",
        "notes": "Planning ranges must be calibrated against agency operating expense and vehicle revenue hour records.",
    },
    "fta_ccd": {
        "source": "FTA Capital Cost Database",
        "url": "https://www.transit.dot.gov/capital-cost-database",
        "publisher": "Federal Transit Administration",
        "version": "2024-09-update",
        "license": "U.S. Department of Transportation public data",
        "notes": "FTA states that the database supports conceptual, order-of-magnitude estimates, not detailed estimates.",
    },
    "fhwa": {
        "source": "FHWA Traffic Calming ePrimer, Module 3",
        "url": "https://highways.dot.gov/safety/speed-management/traffic-calming-eprimer/module-3-part-1",
        "publisher": "Federal Highway Administration",
        "version": "accessed-2026-08-01",
        "license": "U.S. Department of Transportation public information",
        "notes": "Published ranges include $4,000-$8,000 per raised crosswalk and broader active-transport references.",
    },
}


def _source(key: str) -> SourceReference:
    row = SOURCE_DEFINITIONS[key]
    citation_payload = json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    return SourceReference(
        **row,
        retrieved_at_utc=RETRIEVED_AT,
        sha256=sha256_bytes(citation_payload),
        status=EvidenceStatus.DERIVED,
    )


def build_factor_registry() -> dict[str, Any]:
    sources = {key: _source(key).to_dict() for key in SOURCE_DEFINITIONS}
    for source in sources.values():
        source["hash_scope"] = "canonical pinned citation descriptor; not remote page bytes"
    factors = {
        "passenger_vehicle_kg_co2e_per_vehicle_mile": {
            "unit": "kg CO2e / vehicle-mile",
            "low": 0.25,
            "base": 0.393,
            "high": 0.55,
            "status": "scenario",
            "source_ids": ["epa"],
            "basis": "EPA national typical gasoline vehicle is the base; low/high are planning sensitivity bounds.",
        },
        "diesel_shuttle_kg_co2_per_vehicle_mile": {
            "unit": "kg CO2 / vehicle-mile",
            "low": 1.2725,
            "base": 1.6967,
            "high": 2.545,
            "status": "scenario",
            "source_ids": ["epa"],
            "basis": "EPA 10.180 kg CO2/gallon divided by 8/6/4 mpg sensitivity assumptions; excludes upstream emissions.",
        },
        "bus_operation_usd_per_vehicle_hour": {
            "unit": "2026 planning USD / vehicle-hour",
            "low": 100.0,
            "base": 180.0,
            "high": 300.0,
            "status": "estimated",
            "source_ids": ["fta_ntd"],
            "basis": "Order-of-magnitude range; replace with agency NTD operating expense divided by vehicle revenue hours.",
        },
        "transit_priority_capital_usd_per_route_mile": {
            "unit": "2026 planning USD / route-mile",
            "low": 1_000_000.0,
            "base": 5_000_000.0,
            "high": 15_000_000.0,
            "status": "estimated",
            "source_ids": ["fta_ccd"],
            "basis": "Conceptual allowance only; local scope and Standard Cost Categories are required before investment use.",
        },
        "raised_crosswalk_usd_each": {
            "unit": "published USD / installation",
            "low": 4_000.0,
            "base": 6_000.0,
            "high": 8_000.0,
            "status": "derived",
            "source_ids": ["fhwa"],
            "basis": "Midpoint calculated from FHWA's published $4,000-$8,000 typical range; excludes right-of-way.",
        },
    }
    snapshot = base_snapshot("planning_factor_registry", RETRIEVED_AT)
    snapshot.update(
        {
            "status": "scenario",
            "sources": sources,
            "factors": factors,
            "policy": {
                "use": "Planning sensitivity only; not engineering estimates or a local emissions inventory",
                "range_order": "low <= base <= high",
                "currency": "Values are not automatically escalated; registry version must state the planning year",
            },
        }
    )
    snapshot["artifact_sha256"] = artifact_hash(snapshot)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/snapshots/factors/planning_factors.json"))
    args = parser.parse_args()
    snapshot = build_factor_registry()
    digest = write_json(args.output, snapshot)
    print(json.dumps({"output": str(args.output), "file_sha256": digest}))


if __name__ == "__main__":
    main()
