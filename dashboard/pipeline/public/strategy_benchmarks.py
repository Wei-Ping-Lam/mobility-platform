"""Validate analyst-coded official-plan strategy benchmarks.

These labels are deliberately separate from published operating overlays.  The
runtime model predicts first, then compares its broad strategy family with the
benchmark.  Exact service commitments, hubs, and controls still require a
content-pinned overlay such as the Dallas plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dashboard.mobility_platform.contracts import CONTRACT_VERSION
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.models.strategy_calibration import STRATEGY_FAMILIES
from dashboard.pipeline.public.common import artifact_hash, read_json

SCHEMA_VERSION = "1.0.0"
SNAPSHOT_KIND = "world_cup_strategy_benchmarks"
DEFAULT_OUTPUT = Path("data/snapshots/operations/world_cup_2026_strategy_benchmarks.json")
EVIDENCE_LEVELS = {"full operating", "strong partial", "strategy level"}


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    if snapshot.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("Strategy benchmark contract mismatch")
    if snapshot.get("snapshot_kind") != SNAPSHOT_KIND:
        raise ValueError("Unexpected strategy benchmark snapshot kind")
    if snapshot.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unexpected strategy benchmark schema version")
    if snapshot.get("artifact_sha256") != artifact_hash(snapshot):
        raise ValueError("Strategy benchmark content hash mismatch")
    benchmarks = snapshot.get("benchmarks")
    if not isinstance(benchmarks, dict) or set(benchmarks) != set(HOST_CITIES):
        raise ValueError("Strategy benchmarks must cover all host cities")
    for city, row in benchmarks.items():
        if not isinstance(row, dict) or str(row.get("city")) != city:
            raise ValueError(f"Strategy benchmark city mismatch: {city}")
        if row.get("strategy_family") not in STRATEGY_FAMILIES:
            raise ValueError(f"Unknown benchmark strategy family: {city}")
        if row.get("evidence_level") not in EVIDENCE_LEVELS:
            raise ValueError(f"Unknown benchmark evidence level: {city}")
        if not str(row.get("source_url") or "").startswith("https://"):
            raise ValueError(f"Strategy benchmark requires an official HTTPS source: {city}")
        if not str(row.get("source_title") or "").strip() or not str(row.get("publisher") or "").strip():
            raise ValueError(f"Strategy benchmark requires source attribution: {city}")
        signals = row.get("official_service_signals")
        if not isinstance(signals, list) or not signals or any(not str(value).strip() for value in signals):
            raise ValueError(f"Strategy benchmark requires reviewed service signals: {city}")


def load_snapshot(path: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    snapshot = read_json(Path(path))
    validate_snapshot(snapshot)
    return snapshot


__all__ = ["DEFAULT_OUTPUT", "EVIDENCE_LEVELS", "SCHEMA_VERSION", "load_snapshot", "validate_snapshot"]
