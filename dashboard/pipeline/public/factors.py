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
    "scenario_assumptions": {
        "source": "Mobility Platform scenario assumption register",
        "url": "docs/MODEL_CARD.md",
        "publisher": "Mobility Platform project team",
        "version": "contract-0.3.0-assumptions-2",
        "license": "Project documentation",
        "notes": "Behavioral uptake, vehicle loading, heat-response, and screening-cost values are explicit planning assumptions, not observations.",
    },
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
    def factor(unit: str, low: float, base: float, high: float, status: str, source_ids: list[str], basis: str) -> dict[str, Any]:
        return {"unit": unit, "low": low, "base": base, "high": high, "status": status, "source_ids": source_ids, "basis": basis}

    scenario = ["scenario_assumptions"]
    factors = {
        "shuttle_passengers_per_bus": factor("passengers / bus", 35, 45, 55, "scenario", scenario, "Event shuttle seated/standing capacity sensitivity; verify against procured fleet."),
        "transit_passengers_per_departure": factor("passengers / departure", 90, 140, 200, "scenario", scenario, "Cross-mode planning capacity for added departures; scheduled capacity is not observed loading."),
        "service_load_factor": factor("fraction", 0.60, 0.75, 0.90, "scenario", scenario, "Share of nominal vehicle capacity assumed usable during event operations."),
        "park_ride_occupancy": factor("passengers / parked vehicle", 1.5, 1.8, 2.1, "scenario", scenario, "Vehicle occupancy sensitivity for event park-and-ride users."),
        "park_ride_utilization": factor("fraction", 0.55, 0.70, 0.85, "scenario", scenario, "Share of provided remote spaces assumed occupied."),
        "bike_hub_turnover": factor("passengers / space / event", 0.70, 0.90, 1.10, "scenario", scenario, "Completed event trips per installed bike or micromobility parking space."),
        "bike_uptake_share": factor("fraction of attendance", 0.01, 0.025, 0.05, "scenario", scenario, "Distance-limited active-mode uptake ceiling; not observed fan behavior."),
        "walk_uptake_per_covered_km": factor("fraction of attendance / covered km", 0.002, 0.005, 0.009, "scenario", scenario, "Incremental walking uptake sensitivity per covered corridor kilometer."),
        "maximum_new_walk_share": factor("fraction of attendance", 0.01, 0.03, 0.06, "scenario", scenario, "Upper bound on incremental walking uptake in the screening model."),
        "private_vehicle_co2e_kg_per_mile": factor("kg CO2e / vehicle-mile", 0.25, 0.393, 0.55, "scenario", ["epa"], "EPA national typical gasoline vehicle is the base; bounds are planning sensitivity values."),
        "service_vehicle_co2e_kg_per_mile": factor("kg CO2e / vehicle-mile", 1.2725, 1.6967, 2.545, "scenario", ["epa"], "EPA diesel CO2 factor divided by 8/6/4 mpg sensitivity assumptions; upstream emissions excluded."),
        "route_heat_reduction_c": factor("degrees C", 0.5, 1.5, 2.5, "scenario", scenario, "Screening response for shade/cooling treatment; replace with a designed corridor study."),
        "heat_exposure_hours_per_walker": factor("person-hours / walker", 0.25, 0.50, 0.75, "scenario", scenario, "Walking exposure-duration sensitivity for treated venue approaches."),
        "shuttle_cost_per_bus_hour": factor("2026 planning USD / bus-hour", 100, 180, 300, "estimated", ["fta_ntd"], "Order-of-magnitude bus operating range informed by NTD operating-expense categories."),
        "transit_cost_per_departure": factor("2026 planning USD / departure", 220, 396, 660, "estimated", ["fta_ntd"], "Two-point-two vehicle-hours per added departure multiplied by the bus-hour planning range."),
        "park_ride_cost_per_space": factor("2026 planning USD / space", 3500, 7000, 14000, "estimated", ["fta_ccd"], "Conceptual temporary/permanent remote-parking allowance; local scope is required."),
        "bike_hub_cost_per_space": factor("2026 planning USD / space", 350, 700, 1300, "estimated", ["fhwa"], "Order-of-magnitude installed secure parking and event operations allowance."),
        "cooled_walkway_cost_per_km": factor("2026 planning USD / km", 750000, 1600000, 3200000, "estimated", ["fhwa", "fta_ccd"], "Conceptual corridor allowance combining crossings, shade, cooling, and design contingency."),
        "arrival_management_cost_per_pct": factor("2026 planning USD / percentage point", 1200, 2500, 5000, "scenario", scenario, "Event communications, curb allocation, staffing, and enforcement screening allowance."),
        "arrival_eligible_share": factor("fraction of peak arrivals", 0.40, 0.65, 0.85, "scenario", scenario, "Share of peak arrivals assumed reachable and eligible for timed communications or curb controls; no FIFA response observations are supplied."),
        "arrival_compliance_rate": factor("fraction of eligible arrivals", 0.20, 0.45, 0.70, "scenario", scenario, "Share of eligible travelers assumed to change arrival time; no observed host-city compliance study is supplied."),
        "arrival_shoulder_capacity_share": factor("fraction of peak demand", 0.03, 0.08, 0.15, "scenario", scenario, "Maximum peak-equivalent demand that shoulder periods are assumed able to absorb without a local curb or holding-capacity study."),
        "park_ride_reuse_events": factor("event uses", 15, 30, 60, "scenario", scenario, "Planning event uses over which reusable park-and-ride capital is allocated for comparison; total project cost remains visible."),
        "bike_hub_reuse_events": factor("event uses", 20, 40, 80, "scenario", scenario, "Planning event uses over which reusable bike-hub capital is allocated for comparison; total project cost remains visible."),
        "cooled_walkway_reuse_events": factor("event uses", 30, 60, 120, "scenario", scenario, "Planning event uses over which reusable walking-corridor capital is allocated for comparison; total project cost remains visible."),
        "bike_max_distance_m": factor("meters", 3000, 5000, 8000, "scenario", scenario, "Maximum practical active-mode distance sensitivity; the model currently uses the base threshold."),
    }
    snapshot = base_snapshot("planning_factor_registry", RETRIEVED_AT)
    snapshot.update(
        {
            "schema_version": "1.1.0",
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
