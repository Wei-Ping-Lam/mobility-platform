"""Artifact loading and explicit cache status handling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ProjectPaths


def artifact_path(paths: ProjectPaths, name: str) -> Path:
    return paths.artifact_root / name


def read_manifest(paths: ProjectPaths) -> dict[str, Any]:
    path = artifact_path(paths, "manifest.json")
    if not path.exists():
        return {"status": "unavailable", "warnings": ["Offline ETL has not produced dashboard/cache/manifest.json."]}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "unavailable", "errors": [f"Could not read manifest: {exc}"]}


def read_parquet(paths: ProjectPaths, name: str, columns: list[str] | None = None) -> pd.DataFrame:
    path = artifact_path(paths, name)
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_parquet(path, columns=columns)
    except Exception:
        return pd.DataFrame()


def read_json(paths: ProjectPaths, name: str, default: Any) -> Any:
    path = artifact_path(paths, name)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def artifact_inventory(paths: ProjectPaths) -> list[dict[str, Any]]:
    if not paths.artifact_root.exists():
        return []
    rows = []
    for path in sorted(paths.artifact_root.iterdir()):
        if path.is_file():
            rows.append({"name": path.name, "bytes": path.stat().st_size})
    return rows
