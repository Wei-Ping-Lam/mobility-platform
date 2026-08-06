"""Dynamic competition-criteria and deliverable evidence records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

CRITERIA = (
    ("Impact", 25),
    ("Data Analytics", 20),
    ("Innovation", 15),
    ("Feasibility", 15),
    ("Legacy", 10),
    ("Visualization", 10),
    ("Presentation", 5),
)


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, pd.DataFrame):
        return value.to_dict("records")
    if isinstance(value, (list, tuple)):
        return [dict(row) for row in value if isinstance(row, Mapping)]
    return []


def build_deliverable_evidence(
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    comparison: pd.DataFrame,
) -> pd.DataFrame:
    movements = _records(artifacts.get("movement_scenarios"))
    access = _records(artifacts.get("access_gaps"))
    outcomes = _records(artifacts.get("intervention_outcomes"))
    recommendations = _records(artifacts.get("investment_recommendations"))
    operational = _records(artifacts.get("operational_metrics"))
    qualified = sum(
        bool(row.get("capacity_qualified", str(row.get("status")) in {"observed", "derived", "scenario"}))
        for row in access
    )
    route_cities = sum(
        bool(row.get("route_geometry"))
        for row in (artifacts.get("walking_networks") or {}).values()
        if isinstance(row, Mapping)
    )
    match_scoped = sum(bool(row.get("match_id")) for row in recommendations)
    evidence_qualified_options = sum(bool(row.get("evidence_qualified")) for row in recommendations)
    strict_count = int(comparison["strict_rankable"].sum()) if not comparison.empty else 0
    if not comparison.empty and "access_priority_order" in comparison:
        access_ranked = int(comparison["access_priority_order"].notna().sum())
    elif not comparison.empty and "capacity_qualified_gap_pph" in comparison:
        access_ranked = int(comparison["capacity_qualified_gap_pph"].notna().sum())
    else:
        access_ranked = 0
    rows = [
        {
            "Deliverable": "Visitor movement",
            "Status": "scenario" if movements else "unavailable",
            "Visible proof": f"{len(movements)} match-specific hourly low/base/high scenarios plus {len(operational)} official post-event benchmarks",
            "Limitation": "Planning scenario; published aggregates do not yet qualify match-hour calibration.",
            "Workspace": "Scenario Explorer / Movement",
        },
        {
            "Deliverable": "First/last-mile gaps",
            "Status": "partial" if qualified < len(access) else "derived",
            "Visible proof": f"{qualified}/{len(access)} matches capacity-qualified; {route_cities}/11 cities have stop-route paths",
            "Limitation": (
                "All scheduled-capacity gaps are qualified; cities without a serving stop-route path retain a separate walking-evidence warning."
                if qualified == len(access)
                else "Missing event-window service is withheld, never treated as zero service."
            ),
            "Workspace": "Scenario Explorer / Access map",
        },
        {
            "Deliverable": "Compare resilience",
            "Status": "derived" if access_ranked == len(comparison) else "partial",
            "Visible proof": f"All {access_ranked}/{len(comparison)} cities have a physical access-gap priority; {strict_count} have strict secondary MRS ranks",
            "Limitation": "Access-gap priority, evidence screening, and strict MRS are intentionally separate.",
            "Workspace": "Portfolio",
        },
        {
            "Deliverable": "Recommend investments",
            "Status": "scenario" if recommendations and match_scoped == len(recommendations) else "unavailable",
            "Visible proof": f"{match_scoped}/{len(recommendations)} nondominated options tied to exact matches; {evidence_qualified_options} pass the current screening evidence gate",
            "Limitation": "Exploratory sensitivities are separated from evidence-qualified screens; neither is an agency commitment or one optimal answer.",
            "Workspace": "Portfolio / Scenario Explorer",
        },
        {
            "Deliverable": "Sustainability outcomes",
            "Status": "scenario" if outcomes else "unavailable",
            "Visible proof": f"{len(outcomes)} package outcomes include VMT, net CO2e, heat, and cost",
            "Limitation": "Planning factors; not observed mode shift or a local MOVES inventory.",
            "Workspace": "Portfolio / Scenario Explorer / Scenarios",
        },
        {
            "Deliverable": "Outcomes over time",
            "Status": "scenario" if outcomes else "unavailable",
            "Visible proof": "Match, city-tournament, and U.S.-tournament cumulative ledgers",
            "Limitation": "Capital is counted once per city; operations recur per event.",
            "Workspace": "City Action Plan / Tournament horizon",
        },
    ]
    return pd.DataFrame(rows)


def build_criteria_evidence(
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    comparison: pd.DataFrame,
) -> pd.DataFrame:
    deliverables = build_deliverable_evidence(metrics, artifacts, comparison)
    access = _records(artifacts.get("access_gaps"))
    outcomes = _records(artifacts.get("intervention_outcomes"))
    recommendations = _records(artifacts.get("investment_recommendations"))
    validation = _records(artifacts.get("movement_validation"))
    sources = _records(artifacts.get("source_references"))
    operational = _records(artifacts.get("operational_metrics"))
    operational_cities = len({row.get("city") for row in operational if row.get("city")})
    qualified = sum(
        bool(row.get("capacity_qualified", str(row.get("status")) in {"observed", "derived", "scenario"}))
        for row in access
    )
    full_hashes = bool(sources) and all(str(row.get("sha256") or "") for row in sources)
    match_scoped = recommendations and all(row.get("match_id") for row in recommendations)
    visual_review = bool(artifacts.get("visual_review_passed", False))
    submission_metadata = bool(artifacts.get("submission_metadata_complete", False))
    definitions = {
        "Impact": (
            "partial",
            f"{len(outcomes)} modeled package outcomes across {qualified} capacity-qualified matches.",
            "Benefits are scenario estimates, not observed impacts.",
            "Portfolio / City Action Plan",
        ),
        "Data Analytics": (
            "derived" if validation and full_hashes else "partial",
            f"{len(validation)} holdouts and {len(operational)} source-located operational benchmarks across {operational_cities} cities, plus pinned Rice, FIFA, GTFS, OSM, and factors.",
            "Published operational aggregates do not supply complete match-hour arrival, mode, load, curb, parking, and roadway records.",
            "Methods",
        ),
        "Innovation": (
            "derived" if match_scoped else "unavailable",
            "Match-specific access gaps and nondominated tradeoffs preserve total and comparison cost, emissions, heat, lead time, and evidence quality.",
            "Novelty is a decision-support method, not a claim of predictive accuracy.",
            "Portfolio / Scenario Explorer / Tradeoffs",
        ),
        "Feasibility": (
            "partial",
            f"Candidate actors, dependencies, lead times, costs, and {len(operational)} official implementation/throughput benchmarks are visible.",
            "Local fleet, labor, right-of-way, and agency budget constraints require confirmation.",
            "Portfolio / Scenario Explorer / Implementation",
        ),
        "Legacy": (
            "partial",
            f"Reusable event inputs, city/tournament horizons, and post-event evidence for {operational_cities} cities extend beyond a single match.",
            "All cities have at least one published outcome benchmark, but no city has a complete interval-level operational validation set.",
            "City Action Plan / Tournament horizon",
        ),
        "Visualization": (
            "derived" if visual_review else "partial",
            f"{len(deliverables)} deliverables have explicit proof locations, charts, and table equivalents.",
            "Desktop and narrow-screen screenshot review remains open." if not visual_review else "Visual review passed.",
            "All workspaces",
        ),
        "Presentation": (
            "derived" if submission_metadata else "partial",
            "The guided proof sequence maps spoken claims to visible metrics and limitations.",
            "Team/contact metadata remains a submission blocker." if not submission_metadata else "Submission metadata complete.",
            "Overview",
        ),
    }
    return pd.DataFrame(
        [
            {
                "Criterion": name,
                "Weight": weight,
                "Status": definitions[name][0],
                "Visible proof": definitions[name][1],
                "Current limitation": definitions[name][2],
                "Open in": definitions[name][3],
            }
            for name, weight in CRITERIA
        ]
    )
