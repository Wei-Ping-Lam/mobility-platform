"""Deterministic presentation adapters for contract 0.3 and legacy artifacts.

The view layer accepts dataclasses, dictionaries, lists, and data frames so W3-W5
can integrate independently. Missing evidence remains unavailable; adapters never
promote an absent upstream result to observed evidence.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Iterable, Mapping

import pandas as pd

from dashboard.domain.scoring import DEFAULT_WEIGHTS, intervention_result
from dashboard.mobility_platform.contracts import ScenarioConfig

NAMED_SCENARIOS = ("Baseline", "Operational Package", "Capital Package")
ELIGIBLE_STATUSES = {"observed", "derived"}


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (date, datetime, pd.Timestamp)):
        return value.isoformat()
    if hasattr(value, "item"):
        try:
            return value.item()
        except (TypeError, ValueError):
            pass
    if not isinstance(value, (dict, list, tuple)):
        try:
            if bool(pd.isna(value)):
                return None
        except (TypeError, ValueError):
            pass
    return value


def _record(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "to_dict") and not isinstance(value, (dict, pd.Series, pd.DataFrame)):
        return _json_value(value.to_dict())
    if is_dataclass(value):
        return _json_value(asdict(value))
    if isinstance(value, pd.Series):
        return _json_value(value.to_dict())
    if isinstance(value, Mapping):
        return _json_value(dict(value))
    return {}


def records(value: Any) -> list[dict[str, Any]]:
    """Normalize a contract collection without depending on its container type."""

    if value is None:
        return []
    if isinstance(value, pd.DataFrame):
        return [_json_value(item) for item in value.to_dict("records")]
    if isinstance(value, (list, tuple)):
        return [item for raw in value if (item := _record(raw))]
    direct = _record(value)
    if any(key in direct for key in ("city", "match_id", "source", "dataset", "name")):
        return [direct]
    flattened: list[dict[str, Any]] = []
    if isinstance(value, Mapping):
        for key, raw in value.items():
            if isinstance(raw, (list, tuple)):
                for item in records(raw):
                    item.setdefault("city", str(key))
                    flattened.append(item)
            else:
                item = _record(raw)
                if item:
                    item.setdefault("city", str(key))
                    flattened.append(item)
    return flattened


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _integer(value: Any) -> int | None:
    parsed = _number(value)
    return int(round(parsed)) if parsed is not None else None


def _status(value: Any, default: str = "unavailable") -> str:
    normalized = str(getattr(value, "value", value) or default).lower()
    return normalized if normalized in {"observed", "derived", "partial", "estimated", "unavailable", "scenario"} else default


def _scenario_name(name: Any) -> str | None:
    normalized = str(name or "").strip().lower()
    if "baseline" in normalized or normalized in {"zero", "no intervention"}:
        return "Baseline"
    if "operational" in normalized or "operation" in normalized:
        return "Operational Package"
    if "capital" in normalized:
        return "Capital Package"
    return None


@dataclass(frozen=True)
class MatchView:
    match_id: str
    city: str
    venue: str
    kickoff_local: str | None
    stage: str
    capacity: int | None
    status: str
    label: str


@dataclass(frozen=True)
class MovementView:
    status: str = "unavailable"
    uncertainty_type: str = "not available"
    attendance_low: int | None = None
    attendance_base: int | None = None
    attendance_high: int | None = None
    hourly_rows: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    assumptions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class AccessView:
    status: str = "unavailable"
    peak_demand_per_hour: float | None = None
    transit_capacity_low: float | None = None
    transit_capacity_base: float | None = None
    transit_capacity_high: float | None = None
    residual_passengers: float | None = None
    network_walk_distance_m: float | None = None
    service_span_after_match_min: float | None = None
    route_heat_exposure_c: float | None = None
    assumptions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ScenarioView:
    name: str
    status: str = "unavailable"
    gap_resolved_passengers: float | None = None
    venue_vehicle_trips_low: float | None = None
    venue_vehicle_trips_base: float | None = None
    venue_vehicle_trips_high: float | None = None
    net_vmt_low: float | None = None
    net_vmt_base: float | None = None
    net_vmt_high: float | None = None
    net_co2e_kg_low: float | None = None
    net_co2e_kg_base: float | None = None
    net_co2e_kg_high: float | None = None
    heat_exposure_person_hours_avoided: float | None = None
    cost_low: float | None = None
    cost_base: float | None = None
    cost_high: float | None = None
    lead_time_band: str = "Not available"
    basis: str = "contract 0.3"
    package: dict[str, Any] = field(default_factory=dict)
    assumptions: tuple[str, ...] = field(default_factory=tuple)

    @property
    def cost_per_passenger(self) -> float | None:
        if self.cost_base is None or not self.gap_resolved_passengers:
            return None
        return self.cost_base / self.gap_resolved_passengers

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["cost_per_passenger"] = self.cost_per_passenger
        return _json_value(data)


@dataclass(frozen=True)
class RecommendationView:
    intervention: str
    rationale: str
    status: str = "unavailable"
    cost_low: float | None = None
    cost_base: float | None = None
    cost_high: float | None = None
    gap_resolved_passengers: float | None = None
    cost_per_passenger: float | None = None
    net_co2e_kg: float | None = None
    lead_time_band: str = "Not available"
    responsible_actor: str = "Not assigned"
    dependencies: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CityDecisionView:
    city: str
    venue: str
    lat: float | None
    lon: float | None
    matches: tuple[MatchView, ...]
    movements: dict[str, MovementView]
    access_gaps: dict[str, AccessView]
    scenarios: dict[str, tuple[ScenarioView, ...]]
    recommendations: dict[str, tuple[RecommendationView, ...]]
    metric: dict[str, Any]

    def match(self, match_id: str | None = None) -> MatchView:
        if match_id:
            for item in self.matches:
                if item.match_id == match_id:
                    return item
        return self.matches[0]

    def movement(self, match_id: str) -> MovementView:
        return self.movements.get(match_id, MovementView())

    def access(self, match_id: str) -> AccessView:
        return self.access_gaps.get(match_id, AccessView())

    def scenario_set(self, match_id: str) -> tuple[ScenarioView, ...]:
        return self.scenarios.get(match_id, tuple(ScenarioView(name=name) for name in NAMED_SCENARIOS))

    def recommendation_set(self, match_id: str) -> tuple[RecommendationView, ...]:
        return self.recommendations.get(match_id, ())


@dataclass(frozen=True)
class PlatformPresentation:
    cities: dict[str, CityDecisionView]
    source_rows: tuple[dict[str, Any], ...]
    factor_rows: tuple[dict[str, Any], ...]
    network_rows: tuple[dict[str, Any], ...]
    validation_rows: tuple[dict[str, Any], ...]
    sensitivity_rows: tuple[dict[str, Any], ...]

    def city(self, name: str) -> CityDecisionView:
        return self.cities[name if name in self.cities else sorted(self.cities)[0]]

    def scenario_json(self, city: str, match_id: str) -> str:
        decision = self.city(city)
        match = decision.match(match_id)
        payload = {
            "city": decision.city,
            "venue": decision.venue,
            "match": asdict(match),
            "movement": asdict(decision.movement(match.match_id)),
            "access_gap": asdict(decision.access(match.match_id)),
            "scenarios": [item.to_dict() for item in decision.scenario_set(match.match_id)],
        }
        return json.dumps(_json_value(payload), indent=2, sort_keys=True)


def _first_collection(artifacts: Mapping[str, Any], keys: Iterable[str]) -> list[dict[str, Any]]:
    for key in keys:
        if key in artifacts and artifacts[key] is not None:
            parsed = records(artifacts[key])
            if parsed:
                return parsed
    return []


def _legacy_scenarios(metric: Mapping[str, Any]) -> tuple[ScenarioView, ...]:
    city = str(metric.get("city", ""))
    configs = {
        "Baseline": ScenarioConfig(city=city, shuttle_buses_per_hour=0, park_ride_spaces=0, bike_stations=0, pedestrian_upgrade_pct=0),
        "Operational Package": ScenarioConfig(city=city, shuttle_buses_per_hour=20, park_ride_spaces=2000, bike_stations=8, pedestrian_upgrade_pct=0),
        "Capital Package": ScenarioConfig(city=city, shuttle_buses_per_hour=35, park_ride_spaces=7000, bike_stations=20, pedestrian_upgrade_pct=0),
    }
    row = pd.Series(metric)
    output: list[ScenarioView] = []
    for name, config in configs.items():
        result = intervention_result(row, config)
        output.append(
            ScenarioView(
                name=name,
                status="scenario",
                gap_resolved_passengers=float(result.potential_mode_shift),
                venue_vehicle_trips_base=float(result.residual_vehicle_trips),
                net_vmt_base=float(result.vehicle_km_avoided),
                net_co2e_kg_base=float(result.emissions_avoided_kg),
                cost_base=float(result.capital_cost + result.operating_cost_per_match),
                basis="legacy compatibility model",
                package=_json_value(asdict(config)),
                assumptions=tuple(result.assumptions) + ("Compatibility output; replace with contract 0.3 intervention evidence for decisions.",),
            )
        )
    return tuple(output)


def _adapt_scenario(raw: Mapping[str, Any], name: str) -> ScenarioView:
    package = _record(raw.get("package"))
    return ScenarioView(
        name=name,
        status=_status(raw.get("status"), "scenario"),
        gap_resolved_passengers=_number(raw.get("gap_resolved_passengers")),
        venue_vehicle_trips_low=_number(raw.get("venue_vehicle_trips_low")),
        venue_vehicle_trips_base=_number(raw.get("venue_vehicle_trips_base")),
        venue_vehicle_trips_high=_number(raw.get("venue_vehicle_trips_high")),
        net_vmt_low=_number(raw.get("net_vmt_low")),
        net_vmt_base=_number(raw.get("net_vmt_base")),
        net_vmt_high=_number(raw.get("net_vmt_high")),
        net_co2e_kg_low=_number(raw.get("net_co2e_kg_low")),
        net_co2e_kg_base=_number(raw.get("net_co2e_kg_base")),
        net_co2e_kg_high=_number(raw.get("net_co2e_kg_high")),
        heat_exposure_person_hours_avoided=_number(raw.get("heat_exposure_person_hours_avoided")),
        cost_low=_number(raw.get("cost_low")),
        cost_base=_number(raw.get("cost_base")),
        cost_high=_number(raw.get("cost_high")),
        lead_time_band=str(raw.get("lead_time_band") or package.get("lead_time_band") or "Not available"),
        package=package,
        assumptions=tuple(str(item) for item in raw.get("assumptions", ()) or ()),
    )


def _sensitivity(metrics: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    components = {
        "transit": ("transit_score", "transit_status"),
        "heat": ("heat_score", "heat_status"),
        "uhi": ("uhi_score", "uhi_status"),
        "access": ("access_score", "access_status"),
    }
    for profile, weights in DEFAULT_WEIGHTS.items():
        scored: list[dict[str, Any]] = []
        for raw in metrics.to_dict("records"):
            weighted = 0.0
            eligible_weight = 0.0
            required_missing = False
            for component, weight in weights.items():
                value_col, status_col = components[component]
                value = _number(raw.get(value_col))
                status = _status(raw.get(status_col))
                if weight > 0 and (value is None or status not in ELIGIBLE_STATUSES):
                    required_missing = True
                if value is not None and status in ELIGIBLE_STATUSES:
                    weighted += value * weight
                    eligible_weight += weight
            score = weighted / eligible_weight if eligible_weight else None
            scored.append({"city": raw.get("city"), "score": score, "rankable": not required_missing})
        rankable = sorted((item for item in scored if item["rankable"] and item["score"] is not None), key=lambda item: (-item["score"], str(item["city"])))
        ranks = {str(item["city"]): rank for rank, item in enumerate(rankable, 1)}
        for item in scored:
            rows.append(
                {
                    "Profile": profile,
                    "City": item["city"],
                    "MRS": round(item["score"], 1) if item["score"] is not None else None,
                    "Rank": ranks.get(str(item["city"])),
                    "Rankable": item["rankable"],
                }
            )
    return rows


def build_presentation(metrics: pd.DataFrame, artifacts: Mapping[str, Any]) -> PlatformPresentation:
    """Build a stable decision-oriented presentation model from old or 0.3 inputs."""

    metric_records = metrics.to_dict("records") if isinstance(metrics, pd.DataFrame) else records(metrics)
    matches = _first_collection(artifacts, ("match_events", "matches", "fifa_schedule"))
    movements = _first_collection(artifacts, ("movement_scenarios", "movements", "movement"))
    access_rows = _first_collection(artifacts, ("access_gaps", "access_gap_results", "access"))
    outcome_rows = _first_collection(artifacts, ("intervention_outcomes", "outcomes", "scenario_outcomes"))
    recommendation_rows = _first_collection(artifacts, ("investment_recommendations", "recommendations"))

    cities: dict[str, CityDecisionView] = {}
    for metric in metric_records:
        city = str(metric.get("city", ""))
        if not city:
            continue
        city_matches = [item for item in matches if str(item.get("city")) == city]
        if not city_matches:
            city_matches = [
                {
                    "match_id": f"{city.lower().replace(' ', '-')}-portfolio",
                    "city": city,
                    "venue": metric.get("venue", "Venue unavailable"),
                    "kickoff_local": None,
                    "stage": "Schedule unavailable",
                    "capacity": metric.get("capacity"),
                    "status": "unavailable",
                }
            ]
        match_views: list[MatchView] = []
        movement_views: dict[str, MovementView] = {}
        access_views: dict[str, AccessView] = {}
        scenario_views: dict[str, tuple[ScenarioView, ...]] = {}
        recommendation_views: dict[str, tuple[RecommendationView, ...]] = {}
        for raw_match in city_matches:
            match_id = str(raw_match.get("match_id"))
            kickoff = raw_match.get("kickoff_local")
            stage = str(raw_match.get("stage") or "Stage unavailable")
            label = f"{match_id} · {stage}"
            if kickoff:
                label += f" · {kickoff}"
            match_views.append(
                MatchView(
                    match_id=match_id,
                    city=city,
                    venue=str(raw_match.get("venue") or metric.get("venue") or "Venue unavailable"),
                    kickoff_local=str(kickoff) if kickoff else None,
                    stage=stage,
                    capacity=_integer(raw_match.get("capacity")),
                    status=_status(raw_match.get("status") or _record(raw_match.get("source")).get("status")),
                    label=label,
                )
            )

            raw_movement = next((item for item in movements if str(item.get("city")) == city and str(item.get("match_id")) == match_id), {})
            movement_views[match_id] = MovementView(
                status=_status(raw_movement.get("status")),
                uncertainty_type=str(raw_movement.get("uncertainty_type") or "not available"),
                attendance_low=_integer(raw_movement.get("attendance_low")),
                attendance_base=_integer(raw_movement.get("attendance_base")),
                attendance_high=_integer(raw_movement.get("attendance_high")),
                hourly_rows=tuple(records(raw_movement.get("hourly_rows", []))),
                assumptions=tuple(str(item) for item in raw_movement.get("assumptions", ()) or ()),
            )

            raw_access = next((item for item in access_rows if str(item.get("city")) == city and str(item.get("match_id")) == match_id), {})
            access_views[match_id] = AccessView(
                status=_status(raw_access.get("status")),
                peak_demand_per_hour=_number(raw_access.get("peak_demand_per_hour")),
                transit_capacity_low=_number(raw_access.get("transit_capacity_low")),
                transit_capacity_base=_number(raw_access.get("transit_capacity_base")),
                transit_capacity_high=_number(raw_access.get("transit_capacity_high")),
                residual_passengers=_number(raw_access.get("residual_passengers")),
                network_walk_distance_m=_number(raw_access.get("network_walk_distance_m")),
                service_span_after_match_min=_number(raw_access.get("service_span_after_match_min")),
                route_heat_exposure_c=_number(raw_access.get("route_heat_exposure_c")),
                assumptions=tuple(str(item) for item in raw_access.get("assumptions", ()) or ()),
            )

            city_outcomes = [
                item for item in outcome_rows
                if str(item.get("city")) == city and str(item.get("match_id")) == match_id
            ]
            by_name = {
                name: _adapt_scenario(item, name)
                for item in city_outcomes
                if (name := _scenario_name(_record(item.get("package")).get("name") or item.get("name")))
            }
            if by_name:
                scenario_views[match_id] = tuple(by_name.get(name, ScenarioView(name=name)) for name in NAMED_SCENARIOS)
            else:
                scenario_views[match_id] = _legacy_scenarios(metric)

            city_recommendations = [
                item for item in recommendation_rows
                if str(item.get("city")) == city and str(item.get("match_id")) == match_id
            ]
            recommendation_views[match_id] = tuple(
                RecommendationView(
                    intervention=str(item.get("intervention") or "Investment unavailable"),
                    rationale=str(item.get("rationale") or "No rationale supplied."),
                    status=_status(item.get("status")),
                    cost_low=_number(item.get("cost_low")),
                    cost_base=_number(item.get("cost_base")),
                    cost_high=_number(item.get("cost_high")),
                    gap_resolved_passengers=_number(item.get("gap_resolved_passengers")),
                    cost_per_passenger=_number(item.get("cost_per_passenger")),
                    net_co2e_kg=_number(item.get("net_co2e_kg")),
                    lead_time_band=str(item.get("lead_time_band") or "Not available"),
                    responsible_actor=str(item.get("responsible_actor") or "Not assigned"),
                    dependencies=tuple(str(value) for value in item.get("dependencies", ()) or ()),
                )
                for item in city_recommendations
            )

        cities[city] = CityDecisionView(
            city=city,
            venue=str(metric.get("venue") or match_views[0].venue),
            lat=_number(metric.get("lat")),
            lon=_number(metric.get("lon")),
            matches=tuple(match_views),
            movements=movement_views,
            access_gaps=access_views,
            scenarios=scenario_views,
            recommendations=recommendation_views,
            metric=_json_value(metric),
        )

    manifest = artifacts.get("manifest", {}) if isinstance(artifacts.get("manifest", {}), Mapping) else {}
    source_rows = _first_collection(artifacts, ("source_references", "sources"))
    source_rows.extend(records(manifest.get("datasets", [])))
    factor_rows = _first_collection(artifacts, ("factor_registry", "factors"))
    network_rows = _first_collection(artifacts, ("network_coverage", "networks"))
    validation_rows = _first_collection(artifacts, ("movement_validation", "validation"))
    sensitivity_rows = _first_collection(artifacts, ("mrs_sensitivity", "sensitivity")) or _sensitivity(metrics)
    return PlatformPresentation(
        cities=cities,
        source_rows=tuple(source_rows),
        factor_rows=tuple(factor_rows),
        network_rows=tuple(network_rows),
        validation_rows=tuple(validation_rows),
        sensitivity_rows=tuple(sensitivity_rows),
    )


def city_layer_records(artifacts: Mapping[str, Any], city: str, layer: str) -> list[dict[str, Any]]:
    """Return coordinate-ready layer rows from contract bundles or legacy caches."""

    aliases = {
        "gtfs": ("gtfs_stops", "stops"),
        "gtfs_routes": ("route_shapes", "gtfs_lines"),
        "walk": ("walk_layers", "walking_networks", "osm_layers"),
        "uhi": ("uhi_points", "uhi_layers"),
        "poi": ("poi_points", "poi_layers"),
        "origin": ("origin_flows", "origin_layers"),
    }
    map_layers = artifacts.get("map_layers", {})
    if isinstance(map_layers, Mapping):
        city_layers = map_layers.get(city, {})
        if isinstance(city_layers, Mapping):
            for key in (layer, *aliases.get(layer, ())):
                if key in city_layers:
                    return records(city_layers[key])
    for key in aliases.get(layer, ()):
        raw = artifacts.get(key)
        parsed = records(raw)
        selected = [item for item in parsed if str(item.get("city", city)) == city]
        if selected:
            return selected
    if layer == "gtfs":
        raw_city = artifacts.get("gtfs", {}).get(city, {}) if isinstance(artifacts.get("gtfs", {}), Mapping) else {}
        return records(raw_city.get("stop_points_2mi", [])) if isinstance(raw_city, Mapping) else []
    if layer == "gtfs_routes":
        raw_city = artifacts.get("gtfs", {}).get(city, {}) if isinstance(artifacts.get("gtfs", {}), Mapping) else {}
        return records(raw_city.get("route_shapes", [])) if isinstance(raw_city, Mapping) else []
    return []
