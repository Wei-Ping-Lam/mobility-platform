"""World Cup visitor-flow scenario forecasts with explicit evidence boundaries.

The model is deliberately pure and deterministic. Official match context and the
existing attendance scenarios define the total. Supplied commercial customer-origin
shares shape the domestic origin prior, but are never described as observed fans.
Mode demand is a transparent planning response to transit readiness, exact-hour
scheduled coverage, and venue-side walking evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import floor, isfinite, sqrt
from typing import Any

import pandas as pd

from dashboard.mobility_platform.contracts import AccessGapResult, MatchEvent, MovementScenario

CASES = ("low", "base", "high")
ORIGIN_TYPES = (
    "Host market",
    "Nearby U.S.",
    "Long-distance U.S.",
    "International / unobserved",
)
MODE_TYPES = (
    "Scheduled transit",
    "Event shuttle / coach",
    "Private vehicle / taxi",
    "Walk / bike to venue",
)

# These are transparent scenario groupings, not inferred fan catchments.
HOST_MARKET_STATES = {
    "Atlanta": {"GA"},
    "Boston": {"MA", "RI"},
    "Dallas": {"TX"},
    "Houston": {"TX"},
    "Kansas City": {"KS", "MO"},
    "Los Angeles": {"CA"},
    "Miami": {"FL"},
    "New York/NJ": {"CT", "NJ", "NY"},
    "Philadelphia": {"DE", "NJ", "PA"},
    "San Francisco": {"CA"},
    "Seattle": {"WA"},
}
NEARBY_STATES = {
    "Atlanta": {"AL", "FL", "NC", "SC", "TN"},
    "Boston": {"CT", "ME", "NH", "NY", "VT"},
    "Dallas": {"AR", "LA", "NM", "OK"},
    "Houston": {"AR", "LA", "MS", "OK"},
    "Kansas City": {"AR", "IA", "NE", "OK"},
    "Los Angeles": {"AZ", "NV"},
    "Miami": {"AL", "GA"},
    "New York/NJ": {"DE", "MA", "MD", "PA", "RI", "VA"},
    "Philadelphia": {"MD", "NY", "VA", "WV"},
    "San Francisco": {"NV", "OR"},
    "Seattle": {"ID", "OR"},
}

INTERNATIONAL_SHARE_BY_STAGE = {
    "group": {"low": 0.10, "base": 0.20, "high": 0.30},
    "round_of_32": {"low": 0.12, "base": 0.22, "high": 0.32},
    "round_of_16": {"low": 0.14, "base": 0.24, "high": 0.34},
    "quarter_final": {"low": 0.16, "base": 0.27, "high": 0.38},
    "semi_final": {"low": 0.18, "base": 0.30, "high": 0.42},
    "bronze_final": {"low": 0.18, "base": 0.30, "high": 0.42},
    "final": {"low": 0.22, "base": 0.35, "high": 0.48},
}


def build_visitor_flow_forecast(
    match: MatchEvent | Mapping[str, Any],
    movement: MovementScenario | Mapping[str, Any],
    origin_flows: pd.DataFrame | Sequence[Mapping[str, Any]],
    *,
    transit_score: float | None,
    access: AccessGapResult | Mapping[str, Any],
) -> dict[str, Any]:
    """Forecast attendee origin types and mode demand for one World Cup match.

    This is a scenario forecast rather than a trained behavioral prediction. It
    is suitable for comparing planning cases and locating evidence gaps, not for
    operations control or a positive claim about observed FIFA fan behavior.
    """

    event = match.to_dict() if isinstance(match, MatchEvent) else dict(match)
    movement_data = (
        movement.to_dict() if isinstance(movement, MovementScenario) else dict(movement)
    )
    access_data = access.to_dict() if isinstance(access, AccessGapResult) else dict(access)
    city = _required_text(event, "city")
    match_id = _required_text(event, "match_id")
    if str(movement_data.get("city")) != city or str(movement_data.get("match_id")) != match_id:
        raise ValueError("movement scenario must match the supplied city and match_id")
    if str(access_data.get("city")) != city or str(access_data.get("match_id")) != match_id:
        raise ValueError("access result must match the supplied city and match_id")

    attendance = {
        case: _nonnegative_int(movement_data.get(f"attendance_{case}"), f"attendance_{case}")
        for case in CASES
    }
    if not attendance["low"] <= attendance["base"] <= attendance["high"]:
        raise ValueError("attendance cases must be ordered low <= base <= high")

    domestic_prior, prior_status, prior_coverage = _domestic_origin_prior(
        city, origin_flows
    )
    international_shares = INTERNATIONAL_SHARE_BY_STAGE[_stage_key(event.get("stage"))]
    origin_rows = _origin_forecast_rows(
        attendance,
        domestic_prior,
        international_shares,
    )
    mode_rows, flow_rows, mode_inputs = _mode_forecast_rows(
        origin_rows,
        transit_score=transit_score,
        access=access_data,
    )

    origin_totals = {
        case: sum(int(row[f"attendees_{case}"]) for row in origin_rows)
        for case in CASES
    }
    mode_totals = {
        case: sum(int(row[f"attendees_{case}"]) for row in mode_rows)
        for case in CASES
    }
    if origin_totals != attendance or mode_totals != attendance:
        raise AssertionError("forecast allocations must reconcile exactly to attendance")

    external_base = sum(
        int(row["attendees_base"])
        for row in origin_rows
        if row["origin_type"] != "Host market"
    )
    peak = _movement_peaks(movement_data.get("hourly_rows", []))
    return {
        "city": city,
        "match_id": match_id,
        "stage": str(event.get("stage") or "Stage unavailable"),
        "kickoff_local": str(event.get("kickoff_local") or ""),
        "status": "scenario",
        "uncertainty_type": "stage-conditioned planning range",
        "validation_status": "not calibrated to observed FIFA fan origin or mode behavior",
        "attendance_low": attendance["low"],
        "attendance_base": attendance["base"],
        "attendance_high": attendance["high"],
        "non_host_market_attendees_base": external_base,
        "non_host_market_share_base": round(
            external_base / attendance["base"] if attendance["base"] else 0.0, 6
        ),
        "origin_prior_status": prior_status,
        "origin_prior_coverage_pct": round(prior_coverage * 100.0, 2),
        "international_share_low": international_shares["low"],
        "international_share_base": international_shares["base"],
        "international_share_high": international_shares["high"],
        "origin_rows": origin_rows,
        "mode_rows": mode_rows,
        "flow_rows": flow_rows,
        **peak,
        **mode_inputs,
        "equation_ids": ["EQ-VISITOR-FLOW-01", "EQ-MODE-SPLIT-01"],
        "assumptions": [
            "Official FIFA match timing and the existing low/base/high attendance scenarios define the total movement envelope.",
            "Supplied spend-panel customer origins shape only the relative U.S. origin prior; they are not ticket-holder or FIFA fan observations.",
            "International attendance is unobserved and uses an explicit stage-conditioned scenario range.",
            "Mode demand responds to transit readiness, exact-hour scheduled coverage, and venue-side walking evidence; it is not calibrated mode choice.",
            "Forecasts allocate attendees to origin types and broad modes, not to exact home locations, road links, transit lines, or travel times.",
        ],
    }


def _domestic_origin_prior(
    city: str,
    origin_flows: pd.DataFrame | Sequence[Mapping[str, Any]],
) -> tuple[dict[str, float], str, float]:
    frame = origin_flows.copy() if isinstance(origin_flows, pd.DataFrame) else pd.DataFrame(origin_flows)
    required = {"city", "home_state"}
    if frame.empty or not required.issubset(frame.columns):
        return {"Host market": 0.50, "Nearby U.S.": 0.20, "Long-distance U.S.": 0.30}, "unavailable", 0.0
    frame = frame[frame["city"].astype(str) == city].copy()
    if frame.empty:
        return {"Host market": 0.50, "Nearby U.S.": 0.20, "Long-distance U.S.": 0.30}, "unavailable", 0.0
    value_column = "customer_count" if "customer_count" in frame else "city_customer_share"
    values = pd.to_numeric(frame.get(value_column), errors="coerce")
    frame = frame.assign(_value=values).dropna(subset=["_value"])
    frame = frame[frame["_value"] >= 0]
    total = float(frame["_value"].sum())
    if total <= 0:
        return {"Host market": 0.50, "Nearby U.S.": 0.20, "Long-distance U.S.": 0.30}, "unavailable", 0.0

    host = HOST_MARKET_STATES.get(city, set())
    nearby = NEARBY_STATES.get(city, set())
    grouped = {"Host market": 0.0, "Nearby U.S.": 0.0, "Long-distance U.S.": 0.0}
    known_total = 0.0
    for item in frame.to_dict("records"):
        state = str(item.get("home_state") or "").strip().upper()
        value = float(item["_value"])
        if len(state) != 2:
            continue
        known_total += value
        if state in host:
            grouped["Host market"] += value
        elif state in nearby:
            grouped["Nearby U.S."] += value
        else:
            grouped["Long-distance U.S."] += value
    if known_total <= 0:
        return {"Host market": 0.50, "Nearby U.S.": 0.20, "Long-distance U.S.": 0.30}, "unavailable", 0.0
    prior = {name: value / known_total for name, value in grouped.items()}
    statuses = set(frame.get("evidence_status", pd.Series("derived", index=frame.index)).astype(str))
    status = "partial" if "partial" in statuses or "unavailable" in statuses else "context_only"
    return prior, status, known_total / total


def _origin_forecast_rows(
    attendance: Mapping[str, int],
    domestic_prior: Mapping[str, float],
    international_shares: Mapping[str, float],
) -> list[dict[str, Any]]:
    rows = {name: {"origin_type": name} for name in ORIGIN_TYPES}
    for case in CASES:
        international = round(attendance[case] * float(international_shares[case]))
        domestic = attendance[case] - international
        allocated = _allocate_integer(domestic, domestic_prior)
        allocated["International / unobserved"] = international
        for name in ORIGIN_TYPES:
            count = int(allocated.get(name, 0))
            rows[name][f"attendees_{case}"] = count
            rows[name][f"share_{case}"] = round(
                count / attendance[case] if attendance[case] else 0.0, 6
            )
    return [rows[name] for name in ORIGIN_TYPES]


def _mode_forecast_rows(
    origin_rows: Sequence[Mapping[str, Any]],
    *,
    transit_score: float | None,
    access: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, float]]:
    readiness = _bounded(transit_score, default=35.0) / 100.0
    demand = _nonnegative_float(access.get("peak_demand_per_hour"), default=0.0)
    capacity = _nonnegative_float(access.get("transit_capacity_base"), default=0.0)
    coverage = min(capacity / demand, 1.0) if demand > 0 else 0.0
    gap_ratio = 1.0 - coverage
    walk_distance = _optional_nonnegative(access.get("network_walk_distance_m"))
    walk_factor = (
        max(0.0, 1.0 - walk_distance / 2400.0)
        if walk_distance is not None
        else 0.0
    )
    transit_service_factor = 0.05 if capacity <= 0 else 0.25 + 0.75 * sqrt(coverage)

    conditional: dict[str, dict[str, float]] = {}
    for origin in ORIGIN_TYPES:
        transit_base = {
            "Host market": 0.18,
            "Nearby U.S.": 0.12,
            "Long-distance U.S.": 0.20,
            "International / unobserved": 0.24,
        }[origin]
        transit_gain = {
            "Host market": 0.32,
            "Nearby U.S.": 0.23,
            "Long-distance U.S.": 0.30,
            "International / unobserved": 0.34,
        }[origin]
        transit = min((transit_base + transit_gain * readiness) * transit_service_factor, 0.62)
        shuttle = {
            "Host market": 0.06,
            "Nearby U.S.": 0.12,
            "Long-distance U.S.": 0.18,
            "International / unobserved": 0.20,
        }[origin] + 0.10 * gap_ratio
        active = {
            "Host market": 0.08,
            "Nearby U.S.": 0.03,
            "Long-distance U.S.": 0.02,
            "International / unobserved": 0.04,
        }[origin] * walk_factor
        committed = min(transit + shuttle + active, 0.82)
        private = 1.0 - committed
        conditional[origin] = {
            "Scheduled transit": transit,
            "Event shuttle / coach": shuttle,
            "Private vehicle / taxi": private,
            "Walk / bike to venue": active,
        }

    mode_totals = {
        mode: {f"attendees_{case}": 0 for case in CASES} for mode in MODE_TYPES
    }
    flow_rows: list[dict[str, Any]] = []
    for origin_row in origin_rows:
        origin = str(origin_row["origin_type"])
        allocated_by_case: dict[str, dict[str, int]] = {}
        for case in CASES:
            allocated_by_case[case] = _allocate_integer(
                int(origin_row[f"attendees_{case}"]), conditional[origin]
            )
        for mode in MODE_TYPES:
            flow = {"origin_type": origin, "mode": mode}
            for case in CASES:
                count = allocated_by_case[case][mode]
                flow[f"attendees_{case}"] = count
                mode_totals[mode][f"attendees_{case}"] += count
            flow_rows.append(flow)

    mode_rows: list[dict[str, Any]] = []
    total_by_case = {
        case: sum(int(row[f"attendees_{case}"]) for row in origin_rows)
        for case in CASES
    }
    for mode in MODE_TYPES:
        row: dict[str, Any] = {"mode": mode, **mode_totals[mode]}
        for case in CASES:
            row[f"share_{case}"] = round(
                row[f"attendees_{case}"] / total_by_case[case]
                if total_by_case[case]
                else 0.0,
                6,
            )
        mode_rows.append(row)
    return mode_rows, flow_rows, {
        "transit_readiness_input": round(readiness, 4),
        "scheduled_peak_coverage_input": round(coverage, 4),
        "walking_path_factor_input": round(walk_factor, 4),
    }


def _movement_peaks(hourly_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not hourly_rows:
        empty: dict[str, Any] = {}
        for direction in ("arrival", "departure"):
            for case in CASES:
                empty[f"{direction}_peak_{case}"] = 0
            empty[f"{direction}_peak_offset_hours"] = None
        return empty
    peaks: dict[str, Any] = {}
    for source, direction in (("arrivals", "arrival"), ("departures", "departure")):
        for case in CASES:
            field = f"{source}_{case}"
            peak = max(
                hourly_rows,
                key=lambda row: _nonnegative_float(row.get(field), 0.0),
            )
            peaks[f"{direction}_peak_{case}"] = int(
                _nonnegative_float(peak.get(field), 0.0)
            )
            if case == "base":
                peaks[f"{direction}_peak_offset_hours"] = _optional_float(
                    peak.get("hours_from_kickoff")
                )
    return peaks


def _stage_key(value: Any) -> str:
    stage = str(value or "group").strip().lower()
    if stage.startswith("group"):
        return "group"
    return {
        "round of 32": "round_of_32",
        "round of 16": "round_of_16",
        "quarter-final": "quarter_final",
        "semi-final": "semi_final",
        "bronze final": "bronze_final",
        "final": "final",
    }.get(stage, "group")


def _allocate_integer(total: int, shares: Mapping[str, float]) -> dict[str, int]:
    if total < 0:
        raise ValueError("allocation total must be nonnegative")
    cleaned = {str(name): max(float(value), 0.0) for name, value in shares.items()}
    share_total = sum(cleaned.values())
    if not isfinite(share_total) or share_total <= 0:
        raise ValueError("allocation shares must contain a positive finite value")
    normalized = {name: value / share_total for name, value in cleaned.items()}
    raw = {name: total * value for name, value in normalized.items()}
    allocated = {name: floor(value) for name, value in raw.items()}
    remainder = total - sum(allocated.values())
    order = sorted(raw, key=lambda name: (-(raw[name] - allocated[name]), name))
    for name in order[:remainder]:
        allocated[name] += 1
    return allocated


def _required_text(record: Mapping[str, Any], name: str) -> str:
    value = str(record.get(name) or "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    number = _nonnegative_float(value, default=-1.0)
    if number < 0 or not float(number).is_integer():
        raise ValueError(f"{name} must be a nonnegative integer")
    return int(number)


def _nonnegative_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if isfinite(number) and number >= 0 else default


def _optional_nonnegative(value: Any) -> float | None:
    number = _nonnegative_float(value, default=-1.0)
    return number if number >= 0 else None


def _optional_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _bounded(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    if not isfinite(number):
        number = default
    return max(0.0, min(100.0, number))
