"""Reusable data-quality checks used by ETL and the Methods view."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .contracts import DataQualityReport


def quality_report(checks: list[dict[str, Any]], errors: list[str] | None = None, warnings: list[str] | None = None) -> DataQualityReport:
    return DataQualityReport(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        checks=tuple(checks),
        errors=tuple(errors or []),
        warnings=tuple(warnings or []),
    )


def require_columns(df: pd.DataFrame, required: set[str], label: str) -> tuple[list[str], list[str]]:
    missing = sorted(required.difference(df.columns))
    errors = [f"{label}: missing required columns: {', '.join(missing)}"] if missing else []
    return missing, errors


def check_numeric_range(df: pd.DataFrame, column: str, minimum: float, maximum: float, label: str) -> str | None:
    if column not in df.columns:
        return f"{label}: missing column {column}"
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return f"{label}: no numeric values in {column}"
    if (values < minimum).any() or (values > maximum).any():
        return f"{label}: {column} contains values outside [{minimum}, {maximum}]"
    return None
