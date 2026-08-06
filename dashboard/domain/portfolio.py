"""Tournament and reusable-event portfolio aggregation without capex double counting."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

import pandas as pd

from dashboard.models.interventions import InterventionFactorRegistry

SCOPES = ("match", "city_tournament", "us_tournament")


def _number(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return parsed if pd.notna(parsed) else 0.0


def _cost_components(
    package: Mapping[str, Any],
    arrival_window_hours: float,
    factors: InterventionFactorRegistry,
    case: str,
) -> tuple[float, float]:
    """Return one-time capital and per-event operating cost for one package."""

    capital = (
        _number(package.get("park_ride_spaces")) * factors.park_ride_cost_per_space.value(case)
        + _number(package.get("bike_hub_spaces")) * factors.bike_hub_cost_per_space.value(case)
        + _number(package.get("cooled_walkway_km")) * factors.cooled_walkway_cost_per_km.value(case)
    )
    operating = (
        _number(package.get("shuttle_buses_per_hour"))
        * arrival_window_hours
        * factors.shuttle_cost_per_bus_hour.value(case)
        + _number(package.get("added_transit_departures_per_hour"))
        * arrival_window_hours
        * factors.transit_cost_per_departure.value(case)
        + _number(package.get("park_ride_feeder_departures_per_hour"))
        * arrival_window_hours
        * factors.shuttle_cost_per_bus_hour.value(case)
        + _number(package.get("arrival_spreading_pct"))
        * factors.arrival_management_cost_per_pct.value(case)
    )
    return capital, operating


def _selected_events(
    events: Sequence[Mapping[str, Any]],
    *,
    scope: str,
    city: str | None,
    match_id: str | None,
) -> list[Mapping[str, Any]]:
    if scope not in SCOPES:
        raise ValueError(f"Unknown portfolio scope: {scope}")
    if scope == "match":
        selected = [event for event in events if str(event.get("match_id")) == str(match_id)]
    elif scope == "city_tournament":
        selected = [event for event in events if str(event.get("city")) == str(city)]
    else:
        selected = list(events)
    return sorted(selected, key=lambda row: str(row.get("kickoff_local") or row.get("match_id") or ""))


def build_portfolio_timeline(
    events: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    intervention_inputs: Sequence[Mapping[str, Any]],
    factors: InterventionFactorRegistry,
    *,
    package_name: str,
    scope: str,
    city: str | None = None,
    match_id: str | None = None,
    access_rows: Sequence[Mapping[str, Any]] = (),
    include_partial: bool = False,
) -> pd.DataFrame:
    """Aggregate one package over a selected horizon.

    Infrastructure capital is incurred on the first selected event for each city.
    Event operations recur for every match. This is a planning ledger, not a
    budget commitment or a causal forecast.
    """

    selected_scope = _selected_events(events, scope=scope, city=city, match_id=match_id)
    access_by_match = {str(row.get("match_id")): row for row in access_rows}
    if access_by_match and not include_partial:
        selected = [
            event
            for event in selected_scope
            if bool(
                access_by_match.get(str(event.get("match_id")), {}).get(
                    "capacity_qualified",
                    str(access_by_match.get(str(event.get("match_id")), {}).get("status"))
                    in {"observed", "derived", "scenario"},
                )
            )
        ]
    else:
        selected = selected_scope
    outcomes_by_match = {
        str(row.get("match_id")): row
        for row in outcomes
        if str((row.get("package") or {}).get("name")) == package_name
    }
    inputs_by_match = {str(row.get("match_id")): row for row in intervention_inputs}
    cumulative = {
        "gap_resolved_passengers": 0.0,
        "net_vmt": 0.0,
        "net_co2e_kg": 0.0,
        "heat_person_hours_avoided": 0.0,
        "capital_cost_low": 0.0,
        "capital_cost_base": 0.0,
        "capital_cost_high": 0.0,
        "operating_cost_low": 0.0,
        "operating_cost_base": 0.0,
        "operating_cost_high": 0.0,
    }
    capitalized_cities: set[str] = set()
    rows: list[dict[str, Any]] = []
    for event in selected:
        event_match = str(event.get("match_id"))
        outcome = outcomes_by_match.get(event_match)
        if not outcome:
            continue
        event_city = str(event.get("city"))
        package = outcome.get("package") or {}
        city_inputs = inputs_by_match.get(event_match, {})
        arrival_hours = max(_number(city_inputs.get("arrival_window_hours")), 0.0) or 3.0
        event_capital: dict[str, float] = {}
        event_operating: dict[str, float] = {}
        for case in ("low", "base", "high"):
            capital, operating = _cost_components(package, arrival_hours, factors, case)
            event_capital[case] = capital if event_city not in capitalized_cities else 0.0
            event_operating[case] = operating
            cumulative[f"capital_cost_{case}"] += event_capital[case]
            cumulative[f"operating_cost_{case}"] += operating
        capitalized_cities.add(event_city)
        cumulative["gap_resolved_passengers"] += _number(outcome.get("gap_resolved_passengers"))
        cumulative["net_vmt"] += _number(outcome.get("net_vmt_base"))
        cumulative["net_co2e_kg"] += _number(outcome.get("net_co2e_kg_base"))
        cumulative["heat_person_hours_avoided"] += _number(outcome.get("heat_exposure_person_hours_avoided"))
        kickoff = str(event.get("kickoff_local") or "")
        try:
            event_date = datetime.fromisoformat(kickoff).date().isoformat()
        except ValueError:
            event_date = kickoff[:10] or event_match
        rows.append(
            {
                "event_date": event_date,
                "city": event_city,
                "match_id": event_match,
                "package": package_name,
                "event_capital_cost_base": round(event_capital["base"], 2),
                "event_operating_cost_base": round(event_operating["base"], 2),
                **{key: round(value, 3) for key, value in cumulative.items()},
                "total_cost_low": round(cumulative["capital_cost_low"] + cumulative["operating_cost_low"], 2),
                "total_cost_base": round(cumulative["capital_cost_base"] + cumulative["operating_cost_base"], 2),
                "total_cost_high": round(cumulative["capital_cost_high"] + cumulative["operating_cost_high"], 2),
                "evidence_status": str(outcome.get("status") or "scenario"),
                "access_evidence_status": str(access_by_match.get(event_match, {}).get("status") or "not supplied"),
                "scope_selected_matches": len(selected_scope),
                "omitted_matches": len(selected_scope) - len(selected),
            }
        )
    return pd.DataFrame(rows)


def portfolio_summary(timeline: pd.DataFrame) -> dict[str, Any]:
    if timeline.empty:
        return {"match_count": 0, "city_count": 0, "status": "unavailable"}
    final = timeline.iloc[-1].to_dict()
    final.update(
        {
            "match_count": int(timeline["match_id"].nunique()),
            "city_count": int(timeline["city"].nunique()),
            "status": "scenario",
        }
    )
    return final
