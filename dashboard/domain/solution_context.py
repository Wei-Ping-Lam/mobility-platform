"""Reviewed strategy overlap with the four illustrative comparison scenarios.

Labels refer to the repository's evidence snapshot, not live operating status.
In particular, agency electric buses are not assumed assigned to venue service.
"""

from collections.abc import Mapping
from typing import Any

LANES = "Dedicated event bus/shuttle lanes"
HUBS = "Remote park-and-ride + shuttle hubs"
FREQUENCY = "Increase rail/transit frequency"
ELECTRIC = "Electric shuttle/bus fleet"

# Each entry names the evidence section supporting the reviewed relationship.
_SERVICE_CONTEXT = {
    "Atlanta": {
        FREQUENCY: ("Existing approach", "MARTA match-day headways and post-match egress trains."),
    },
    "Boston": {
        HUBS: ("Related approach", "Express-bus pickup points; parking at those origins is not established here."),
        FREQUENCY: ("Existing approach", "Dedicated commuter-rail trains for matches."),
    },
    "Dallas": {
        HUBS: ("Related approach", "TRE-to-charter-bus transfer hubs, rather than the modeled remote parking scheme."),
        FREQUENCY: ("Related approach", "Regional rail and reactive overflow buses; not the modeled frequency increase."),
    },
    "Houston": {
        HUBS: ("Related approach", "Fannin South park-and-ride feeds rail, not the modeled shuttle service."),
        FREQUENCY: ("Published plan", "Two-car METRORail trains and five-minute peak tournament headways."),
    },
    "Kansas City": {
        HUBS: ("Existing approach", "Stadium Direct shuttles from four park-and-ride locations."),
    },
    "Los Angeles": {
        LANES: ("Published plan", "Dedicated connector bus lanes; enforcement is the recommended improvement."),
        HUBS: ("Related approach", "Regional park-and-ride connections are documented, not this scenario's fleet or capacity."),
        FREQUENCY: ("Published plan", "Enhanced Metro match-day service."),
    },
    "Miami": {
        HUBS: ("Related approach", "Four Game Day Express shuttle hubs; this scenario's parking supply is not documented."),
        FREQUENCY: ("Related approach", "Continuous post-match shuttle returns, not a rail-frequency expansion."),
    },
    "New York/NJ": {
        HUBS: ("Related approach", "Direct shuttles from named origins; not the modeled remote parking scheme."),
        FREQUENCY: ("Existing approach", "Dedicated Meadowlands rail service and a published match-day rider commitment."),
    },
    "Philadelphia": {
        FREQUENCY: ("Existing approach", "Frequent Broad Street Line service and late-night trains after matches."),
    },
    "San Francisco": {
        FREQUENCY: ("Existing approach", "VTA deploys additional light-rail cars for stadium events."),
    },
    "Seattle": {
        FREQUENCY: ("Related approach", "Stadium-adjacent light rail; a frequency increase is not established by this evidence."),
    },
}


def solution_context(city: str, benchmark: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    """Attach reviewed labels only when the supporting evidence is available."""
    result = {}
    for solution in (LANES, HUBS, FREQUENCY, ELECTRIC):
        status, note = _SERVICE_CONTEXT.get(city, {}).get(
            solution, ("Not documented", "No matching approach documented in the available snapshot.")
        )
        evidence = benchmark.get("dedicated_service_evidence", {})
        if solution == ELECTRIC:
            evidence = benchmark.get("sustainability_evidence", {})
            # Boston's cited fleet evidence concerns diesel rail, not electric buses.
            if city in _SERVICE_CONTEXT and city != "Boston":
                status = "Related approach"
                note = "Agency fleet electrification exists or is underway; event-shuttle assignment is not established."
        field = "fleet_electrification_basis" if solution == ELECTRIC else "basis"
        source = evidence.get("source_url", "") if isinstance(evidence, Mapping) else ""
        if not isinstance(evidence, Mapping) or not evidence.get(field) or not source.startswith("https://"):
            status, note, source = "Not documented", "Supporting evidence is unavailable in this snapshot.", ""
        result[solution] = {"city_context": status, "context_note": note, "context_source": source}
    return result
