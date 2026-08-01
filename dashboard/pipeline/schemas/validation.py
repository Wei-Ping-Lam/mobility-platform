"""Chunk-level quality accounting for deterministic offline data builds."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable

import pandas as pd

from dashboard.mobility_platform.contracts import DataQualityReport


class QualityTracker:
    """Accumulate auditable validation results without retaining raw rows."""

    def __init__(self, dataset: str) -> None:
        self.dataset = dataset
        self.rows_read = 0
        self.rows_invalid = 0
        self.duplicate_keys = 0
        self.coverage_start: str | None = None
        self.coverage_end: str | None = None
        self._checks: dict[str, dict[str, int | str]] = defaultdict(dict)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def _message_once(self, collection: list[str], message: str) -> None:
        if message not in collection:
            collection.append(message)

    def _count(self, name: str, **values: int | str) -> None:
        current = self._checks[name]
        for key, value in values.items():
            if isinstance(value, int):
                current[key] = int(current.get(key, 0)) + value
            else:
                current[key] = value

    def observe(
        self,
        frame: pd.DataFrame,
        *,
        required: Iterable[str],
        key_columns: Iterable[str] = (),
        date_columns: Iterable[str] = (),
        numeric_ranges: dict[str, tuple[float, float]] | None = None,
        coordinate_columns: tuple[str, str] | None = None,
        sentinels: dict[str, set[float | int]] | None = None,
    ) -> bool:
        """Validate one input chunk and return whether it is processable."""

        rows = len(frame)
        self.rows_read += rows
        missing = sorted(set(required).difference(frame.columns))
        if missing:
            message = f"{self.dataset}: missing required columns: {', '.join(missing)}"
            self._message_once(self.errors, message)
            self._count("required_columns", rows=rows, missing_columns=len(missing))
            return False

        self._count("chunks", count=1, rows=rows)
        null_count = int(frame[list(required)].isna().sum().sum())
        if null_count:
            self._count("required_nulls", count=null_count)
            self.rows_invalid += null_count

        keys = list(key_columns)
        if keys:
            duplicate_count = int(frame.duplicated(keys, keep="first").sum())
            if duplicate_count:
                self.duplicate_keys += duplicate_count
                self._count("duplicate_keys", count=duplicate_count)
                self._message_once(self.warnings, f"{self.dataset}: duplicate key rows detected in input chunks.")

        for column in date_columns:
            parsed = pd.to_datetime(frame[column], errors="coerce")
            invalid = int(parsed.isna().sum())
            valid_dates = parsed.dropna()
            if not valid_dates.empty:
                start = valid_dates.min().date().isoformat()
                end = valid_dates.max().date().isoformat()
                self.coverage_start = min(value for value in (self.coverage_start, start) if value is not None)
                self.coverage_end = max(value for value in (self.coverage_end, end) if value is not None)
            if invalid:
                self.rows_invalid += invalid
                self._count(f"invalid_dates:{column}", column=column, count=invalid)
                self._message_once(self.warnings, f"{self.dataset}: invalid dates were detected in {column}.")

        for column, (minimum, maximum) in (numeric_ranges or {}).items():
            values = pd.to_numeric(frame[column], errors="coerce")
            invalid = int((frame[column].notna() & values.isna()).sum())
            outside = int(((values < minimum) | (values > maximum)).fillna(False).sum())
            if invalid:
                self.rows_invalid += invalid
                self._count(f"non_numeric_values:{column}", column=column, count=invalid)
                self._message_once(self.warnings, f"{self.dataset}: non-numeric values were detected in {column}.")
            if outside:
                self.rows_invalid += outside
                self._count(f"out_of_range_values:{column}", column=column, count=outside)
                self._message_once(self.warnings, f"{self.dataset}: out-of-range values were detected in {column}.")

        if coordinate_columns:
            latitude, longitude = coordinate_columns
            lat = pd.to_numeric(frame[latitude], errors="coerce")
            lon = pd.to_numeric(frame[longitude], errors="coerce")
            invalid_coordinates = int(((lat < -90) | (lat > 90) | (lon < -180) | (lon > 180)).fillna(False).sum())
            if invalid_coordinates:
                self.rows_invalid += invalid_coordinates
                self._count("invalid_coordinates", count=invalid_coordinates)
                self._message_once(self.warnings, f"{self.dataset}: invalid latitude/longitude values were detected.")

        for column, values in (sentinels or {}).items():
            numeric = pd.to_numeric(frame[column], errors="coerce")
            found = int(numeric.isin(values).sum())
            if found:
                self._count(f"sentinel_values:{column}", column=column, count=found)
                self._message_once(self.warnings, f"{self.dataset}: known sentinel values were detected in {column}.")

        return True

    def check_allowed_values(self, frame: pd.DataFrame, column: str, allowed: set[str]) -> None:
        if column not in frame:
            return
        observed = {str(value) for value in frame[column].dropna().unique()}
        unknown = sorted(observed.difference(allowed))
        if unknown:
            self._count("unknown_categories", count=len(unknown))
            self._message_once(self.warnings, f"{self.dataset}: unmapped {column} values: {', '.join(unknown[:10])}.")

    def report(self) -> DataQualityReport:
        checks = [{"name": name, **values} for name, values in sorted(self._checks.items())]
        checks.append({
            "name": "summary",
            "rows_read": self.rows_read,
            "rows_invalid": self.rows_invalid,
            "duplicate_keys": self.duplicate_keys,
        })
        return DataQualityReport(
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
            checks=tuple(checks),
            errors=tuple(self.errors),
            warnings=tuple(self.warnings),
        )
