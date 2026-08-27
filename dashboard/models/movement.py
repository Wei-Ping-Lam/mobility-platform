"""Match-specific, auditable movement planning scenarios.

The functions in this module are pure: callers provide match records and assumptions,
and receive contract-0.3 ``MovementScenario`` objects or tabular views. Commercial
activity observations are intentionally not interpreted as stadium attendance.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from math import isfinite
from typing import Any

import pandas as pd

from dashboard.mobility_platform.contracts import (
    EvidenceStatus,
    MatchEvent,
    MovementScenario,
)

DEFAULT_ATTENDANCE_RATES = {"low": 0.85, "base": 0.95, "high": 1.0}
DEFAULT_ARRIVAL_PROFILE = {-4: 0.05, -3: 0.15, -2: 0.30, -1: 0.35, 0: 0.10, 1: 0.05}
DEFAULT_DEPARTURE_PROFILE = {-1: 0.02, 0: 0.43, 1: 0.35, 2: 0.15, 3: 0.05}
VALIDATED_BASELINE = "validated baseline"
PLANNING_SCENARIO = "planning scenario"


def validation_label(
    validation: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    city: str | None = None,
    required_years: tuple[int, ...] = (2023, 2024),
) -> str:
    """Return ``validated baseline`` only when every required holdout is a win.

    A duplicate holdout is conservative: all rows for that year must report a win.
    Missing years, missing columns, null values, and empty inputs remain planning
    scenarios.
    """

    frame = _as_frame(validation)
    required = {"holdout_year", "outperforms_seasonal_naive"}
    if frame.empty or not required.issubset(frame.columns):
        return PLANNING_SCENARIO
    if city is not None:
        if "city" not in frame.columns:
            return PLANNING_SCENARIO
        frame = frame[frame["city"] == city]
    years = pd.to_numeric(frame["holdout_year"], errors="coerce")
    frame = frame.assign(_holdout_year=years).dropna(subset=["_holdout_year"])
    for year in required_years:
        outcomes = frame.loc[frame["_holdout_year"] == year, "outperforms_seasonal_naive"]
        if outcomes.empty or not outcomes.map(_strict_bool).all():
            return PLANNING_SCENARIO
    return VALIDATED_BASELINE


def baseline_validation_status(
    validation: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
    city: str | None = None,
) -> str:
    """Public integration alias for the strict 2023/2024 validation rule."""

    return validation_label(validation, city=city)


def build_movement_scenario(
    match: MatchEvent | Mapping[str, Any] | pd.Series,
    attendance: Mapping[str, Any] | pd.Series | None = None,
    arrival_profile: Mapping[int, float] | pd.DataFrame | None = None,
    departure_profile: Mapping[int, float] | pd.DataFrame | None = None,
    *,
    match_duration_min: int = 120,
    validation_status: str = PLANNING_SCENARIO,
) -> MovementScenario:
    """Build one match-specific hourly arrival/departure planning scenario.

    Profiles map an integer hour offset to a share. Arrival offsets are relative to
    kickoff; departure offsets are relative to the assumed match end. Shares are
    normalized explicitly and integer allocations use a largest-remainder method,
    so each low/base/high arrival and departure total exactly equals attendance.
    """

    record = _as_mapping(match)
    match_id = _required_text(record, "match_id")
    city = _required_text(record, "city")
    try:
        kickoff = pd.Timestamp(_required_text(record, "kickoff_local"))
    except (TypeError, ValueError) as exc:
        raise ValueError("kickoff_local must be a valid timestamp") from exc
    if pd.isna(kickoff) or kickoff.tzinfo is None:
        raise ValueError("kickoff_local must include its local UTC offset or timezone")
    capacity = _nonnegative_int(record.get("capacity"), "capacity")
    if match_duration_min < 0:
        raise ValueError("match_duration_min must be nonnegative")

    attendance_values, attendance_note = _resolve_attendance(capacity, attendance)
    arrivals, arrival_normalized = _resolve_profile(
        DEFAULT_ARRIVAL_PROFILE if arrival_profile is None else arrival_profile,
        "arrival_profile",
    )
    departures, departure_normalized = _resolve_profile(
        DEFAULT_DEPARTURE_PROFILE if departure_profile is None else departure_profile,
        "departure_profile",
    )

    event_end = kickoff + pd.Timedelta(minutes=match_duration_min)
    buckets: dict[pd.Timestamp, dict[str, Any]] = {}
    for level, total in attendance_values.items():
        for offset, count in _allocate_integer_total(total, arrivals).items():
            timestamp = kickoff + pd.Timedelta(hours=offset)
            row = buckets.setdefault(timestamp, _empty_hourly_row(timestamp, kickoff))
            row[f"arrivals_{level}"] += count
        for offset, count in _allocate_integer_total(total, departures).items():
            timestamp = event_end + pd.Timedelta(hours=offset)
            row = buckets.setdefault(timestamp, _empty_hourly_row(timestamp, kickoff))
            row[f"departures_{level}"] += count

    hourly_rows = []
    for timestamp in sorted(buckets):
        row = buckets[timestamp]
        for level in ("low", "base", "high"):
            row[f"total_movement_{level}"] = row[f"arrivals_{level}"] + row[f"departures_{level}"]
        hourly_rows.append(row)

    label = validation_status if validation_status == VALIDATED_BASELINE else PLANNING_SCENARIO
    assumptions = [
        attendance_note,
        f"Arrivals are distributed relative to kickoff using {dict(arrivals)}.",
        f"Departures are distributed relative to an assumed {match_duration_min}-minute match end using {dict(departures)}.",
        f"Historical baseline label: {label}; event movement remains scenario evidence.",
    ]
    if arrival_normalized:
        assumptions.append("Arrival profile shares were normalized to sum to 1.0.")
    if departure_normalized:
        assumptions.append("Departure profile shares were normalized to sum to 1.0.")

    return MovementScenario(
        city=city,
        match_id=match_id,
        status=EvidenceStatus.SCENARIO,
        uncertainty_type="planning range",
        attendance_low=attendance_values["low"],
        attendance_base=attendance_values["base"],
        attendance_high=attendance_values["high"],
        hourly_rows=tuple(hourly_rows),
        assumptions=tuple(assumptions),
    )


def generate_movement_scenarios(
    matches: pd.DataFrame | Mapping[str, Any] | MatchEvent | Sequence[Mapping[str, Any] | MatchEvent],
    attendance_assumptions: pd.DataFrame | Mapping[str, Mapping[str, Any]] | None = None,
    arrival_profile: Mapping[int, float] | pd.DataFrame | None = None,
    departure_profile: Mapping[int, float] | pd.DataFrame | None = None,
    *,
    match_duration_min: int = 120,
    validation: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
) -> list[MovementScenario]:
    """Build scenarios for a match table; an empty table returns an empty list."""

    records = _records(matches)
    scenarios: list[MovementScenario] = []
    for record in records:
        match_id = _required_text(record, "match_id")
        city = _required_text(record, "city")
        attendance = _attendance_for_match(attendance_assumptions, match_id)
        label = validation_label([] if validation is None else validation, city=city)
        scenarios.append(
            build_movement_scenario(
                record,
                attendance,
                arrival_profile,
                departure_profile,
                match_duration_min=match_duration_min,
                validation_status=label,
            )
        )
    return scenarios


def movement_hourly_frame(
    scenarios: MovementScenario | Mapping[str, Any] | Iterable[MovementScenario | Mapping[str, Any]],
) -> pd.DataFrame:
    """Flatten one or more movement contracts into a display/export DataFrame."""

    if isinstance(scenarios, (MovementScenario, Mapping)):
        items = [scenarios]
    else:
        items = list(scenarios)
    rows: list[dict[str, Any]] = []
    for item in items:
        data = item.to_dict() if isinstance(item, MovementScenario) else dict(item)
        for hourly in data.get("hourly_rows", []):
            rows.append(
                {
                    "city": data.get("city"),
                    "match_id": data.get("match_id"),
                    "status": str(data.get("status", EvidenceStatus.SCENARIO)),
                    **dict(hourly),
                }
            )
    return pd.DataFrame(rows)


def _resolve_attendance(
    capacity: int, attendance: Mapping[str, Any] | pd.Series | None
) -> tuple[dict[str, int], str]:
    values = _as_mapping(attendance) if attendance is not None else {}
    explicit_keys = {f"attendance_{level}" for level in ("low", "base", "high")}
    supplied_explicit = explicit_keys.intersection(values)
    if supplied_explicit and supplied_explicit != explicit_keys:
        raise ValueError("explicit attendance requires low, base, and high counts")
    if explicit_keys.issubset(values):
        resolved = {
            level: _nonnegative_int(values[f"attendance_{level}"], f"attendance_{level}")
            for level in ("low", "base", "high")
        }
        note = "Attendance uses explicit low/base/high planning counts."
    else:
        rates = {
            level: _nonnegative_float(
                values.get(f"occupancy_{level}", DEFAULT_ATTENDANCE_RATES[level]),
                f"occupancy_{level}",
            )
            for level in ("low", "base", "high")
        }
        if any(rate > 1 for rate in rates.values()):
            raise ValueError("occupancy rates must be between 0 and 1")
        resolved = {level: int(round(capacity * rate)) for level, rate in rates.items()}
        note = f"Attendance equals venue capacity times occupancy assumptions {rates}."
    if not resolved["low"] <= resolved["base"] <= resolved["high"]:
        raise ValueError("attendance must be ordered low <= base <= high")
    if any(value > capacity for value in resolved.values()):
        raise ValueError("attendance cannot exceed venue capacity")
    return resolved, note


def _resolve_profile(
    profile: Mapping[int, float] | pd.DataFrame, name: str
) -> tuple[dict[int, float], bool]:
    if isinstance(profile, pd.DataFrame):
        if not {"relative_hour", "share"}.issubset(profile.columns):
            raise ValueError(f"{name} DataFrame requires relative_hour and share columns")
        pairs = zip(profile["relative_hour"], profile["share"])
    else:
        pairs = profile.items()
    aggregated: dict[int, float] = {}
    for raw_offset, raw_share in pairs:
        offset_value = float(raw_offset)
        if not offset_value.is_integer():
            raise ValueError(f"{name} offsets must be whole hours")
        offset = int(offset_value)
        share = _nonnegative_float(raw_share, f"{name} share")
        aggregated[offset] = aggregated.get(offset, 0.0) + share
    total = sum(aggregated.values())
    if not aggregated or total <= 0:
        raise ValueError(f"{name} must contain positive shares")
    normalized = abs(total - 1.0) > 1e-9
    return {offset: share / total for offset, share in sorted(aggregated.items())}, normalized


def _allocate_integer_total(total: int, profile: Mapping[int, float]) -> dict[int, int]:
    exact = {offset: total * share for offset, share in profile.items()}
    allocated = {offset: int(value) for offset, value in exact.items()}
    remainder = total - sum(allocated.values())
    order = sorted(exact, key=lambda offset: (-(exact[offset] - allocated[offset]), offset))
    for offset in order[:remainder]:
        allocated[offset] += 1
    return allocated


def _empty_hourly_row(timestamp: pd.Timestamp, kickoff: pd.Timestamp) -> dict[str, Any]:
    return {
        "timestamp_local": timestamp.isoformat(),
        "hours_from_kickoff": float((timestamp - kickoff) / pd.Timedelta(hours=1)),
        "arrivals_low": 0,
        "arrivals_base": 0,
        "arrivals_high": 0,
        "departures_low": 0,
        "departures_base": 0,
        "departures_high": 0,
    }


def _attendance_for_match(
    assumptions: pd.DataFrame | Mapping[str, Mapping[str, Any]] | None, match_id: str
) -> Mapping[str, Any] | None:
    if assumptions is None:
        return None
    if isinstance(assumptions, pd.DataFrame):
        if "match_id" not in assumptions.columns:
            raise ValueError("attendance assumptions DataFrame requires match_id")
        rows = assumptions[assumptions["match_id"] == match_id]
        if rows.empty:
            return None
        if len(rows) > 1:
            raise ValueError(f"duplicate attendance assumptions for {match_id}")
        return rows.iloc[0]
    return assumptions.get(match_id)


def _records(
    matches: pd.DataFrame | Mapping[str, Any] | MatchEvent | Sequence[Mapping[str, Any] | MatchEvent],
) -> list[Mapping[str, Any]]:
    if isinstance(matches, pd.DataFrame):
        return matches.to_dict("records")
    if isinstance(matches, MatchEvent):
        return [matches.to_dict()]
    if isinstance(matches, Mapping):
        return [dict(matches)]
    return [match.to_dict() if isinstance(match, MatchEvent) else dict(match) for match in matches]


def _as_frame(
    value: pd.DataFrame | Mapping[str, Any] | Sequence[Mapping[str, Any]],
) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, Mapping):
        return pd.DataFrame([dict(value)])
    return pd.DataFrame(value)


def _as_mapping(value: MatchEvent | Mapping[str, Any] | pd.Series) -> Mapping[str, Any]:
    if isinstance(value, MatchEvent):
        return value.to_dict()
    return value.to_dict() if isinstance(value, pd.Series) else value


def _required_text(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if value is None or not str(value).strip():
        raise ValueError(f"{key} is required")
    return str(value)


def _nonnegative_float(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if pd.isna(number) or not isfinite(number) or number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _nonnegative_int(value: Any, name: str) -> int:
    number = _nonnegative_float(value, name)
    if not number.is_integer():
        raise ValueError(f"{name} must be a whole number")
    return int(number)


def _strict_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    return str(value).strip().lower() == "true"
