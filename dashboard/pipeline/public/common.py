"""Shared deterministic serialization and provenance checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from dashboard.mobility_platform.contracts import CONTRACT_VERSION

VALID_STATUSES = {"observed", "derived", "partial", "estimated", "unavailable", "scenario"}


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON deterministically for hashes and checked-in artifacts."""
    # Normalize mapping keys exactly as a JSON reader will see them before
    # sorting; this keeps hashes stable when registries use integer code keys.
    normalized = json.loads(json.dumps(value, ensure_ascii=False))
    return (json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> str:
    payload = canonical_json_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def artifact_hash(value: dict[str, Any], excluded: tuple[str, ...] = ("artifact_sha256",)) -> str:
    hashable = {key: item for key, item in value.items() if key not in excluded}
    return sha256_bytes(canonical_json_bytes(hashable))


def validate_source(source: dict[str, Any], *, allow_unavailable_hash: bool = False) -> None:
    required = {"source", "url", "publisher", "retrieved_at_utc", "version", "sha256", "license", "status"}
    missing = sorted(required - set(source))
    if missing:
        raise ValueError(f"Source metadata is missing: {', '.join(missing)}")
    status = str(source["status"])
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported evidence status: {status}")
    digest = source.get("sha256")
    if status == "unavailable" and allow_unavailable_hash and digest is None:
        return
    if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("Available source evidence requires a lowercase SHA-256 digest")


def base_snapshot(kind: str, generated_at_utc: str) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "snapshot_kind": kind,
        "generated_at_utc": generated_at_utc,
    }
