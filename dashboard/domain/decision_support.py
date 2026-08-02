"""Compose contract-0.3 transportation decisions from compact cached evidence."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

import pandas as pd

from dashboard.mobility_platform.contracts import EvidenceStatus, MatchEvent, SourceReference
from dashboard.models.access import build_access_gap_result
from dashboard.models.demand import validation_metrics
from dashboard.models.interventions import (
    CityInterventionInputs,
    evaluate_intervention,
    named_packages,
    pareto_recommendations,
)
from dashboard.models.movement import build_movement_scenario, validation_label


def _status(value: Any, default: EvidenceStatus = EvidenceStatus.UNAVAILABLE) -> EvidenceStatus:
    try:
        return EvidenceStatus(str(value))
    except ValueError:
        return default


def _source_reference(raw: Mapping[str, Any]) -> SourceReference:
    return SourceReference(
        source=str(raw.get("source") or "Source unavailable"),
        url=str(raw.get("url") or ""),
        publisher=str(raw.get("publisher") or "Publisher unavailable"),
        retrieved_at_utc=str(raw.get("retrieved_at_utc") or ""),
        version=str(raw.get("version") or "unversioned"),
        sha256=str(raw.get("sha256") or "unavailable"),
        license=str(raw.get("license") or "License unavailable"),
        coverage_start=raw.get("coverage_start"),
        coverage_end=raw.get("coverage_end"),
        status=_status(raw.get("status")),
        notes=str(raw.get("notes") or ""),
    )


def _match(raw: Mapping[str, Any]) -> MatchEvent:
    return MatchEvent(
        match_id=str(raw["match_id"]),
        city=str(raw["city"]),
        venue=str(raw["venue"]),
        kickoff_local=str(raw["kickoff_local"]),
        stage=str(raw.get("stage") or "Stage unavailable"),
        capacity=int(raw["capacity"]),
        source=_source_reference(raw.get("source", {})),
    )


def _event_service(city_gtfs: Mapping[str, Any], match_id: str) -> list[dict[str, Any]]:
    """Adapt one match in a pinned GTFS city record to the access-model contract."""

    matches = city_gtfs.get("matches", {})
    match_service = matches.get(match_id, {}) if isinstance(matches, Mapping) else {}
    status = _status(match_service.get("status"))
    departures = match_service.get("event_window_departures")
    capacities = {
        level: match_service.get(f"event_capacity_{level}") for level in ("low", "base", "high")
    }
    if status == EvidenceStatus.UNAVAILABLE or departures is None or any(value is None for value in capacities.values()):
        return [
            {
                "departures_per_hour": 0,
                "vehicle_capacity_low": 0,
                "vehicle_capacity_base": 0,
                "vehicle_capacity_high": 0,
                "status": EvidenceStatus.UNAVAILABLE.value,
            }
        ]
    if float(departures) == 0:
        return [
            {
                "departures_per_hour": 0,
                "vehicle_capacity_low": 0,
                "vehicle_capacity_base": 0,
                "vehicle_capacity_high": 0,
                "status": status.value,
                "service_span_after_match_min": match_service.get("service_span_after_match_min"),
            }
        ]
    event_window_hours = float(match_service.get("event_window_hours") or 8.0)
    departures_per_hour = float(departures) / event_window_hours
    return [
        {
            "departures_per_hour": departures_per_hour,
            "vehicle_capacity_low": float(capacities["low"]) / float(departures),
            "vehicle_capacity_base": float(capacities["base"]) / float(departures),
            "vehicle_capacity_high": float(capacities["high"]) / float(departures),
            "status": status.value,
            "service_span_after_match_min": match_service.get("service_span_after_match_min"),
        }
    ]


def _origin_share(artifacts: Mapping[str, Any], city: str) -> float:
    rows = artifacts.get("origin_flows", [])
    if isinstance(rows, pd.DataFrame):
        frame = rows[rows["city"] == city] if "city" in rows else pd.DataFrame()
        if not frame.empty and "city_customer_share" in frame:
            largest = pd.to_numeric(frame["city_customer_share"], errors="coerce").max()
            return max(0.0, min(1.0, 1.0 - float(largest))) if pd.notna(largest) else 0.25
    return 0.25


def build_transportation_bundle(metrics: pd.DataFrame, artifacts: Mapping[str, Any]) -> dict[str, Any]:
    """Build display-ready contracts without external or raw-data access.

    Public schedule records are observed. Attendance, capacity, intervention, cost,
    and emissions outputs remain planning scenarios. Missing GTFS remains missing;
    its zero capacity values are explicit sentinels, not observed service.
    """

    event_rows = artifacts.get("match_events", [])
    if not event_rows:
        return {}
    metric_rows = metrics.set_index("city").to_dict("index") if not metrics.empty else {}
    gtfs = artifacts.get("gtfs", {}) if isinstance(artifacts.get("gtfs"), Mapping) else {}
    walking = artifacts.get("walking_networks", {}) if isinstance(artifacts.get("walking_networks"), Mapping) else {}
    validation = validation_metrics(artifacts.get("visits", pd.DataFrame()))

    movements = []
    access_results = []
    outcomes = []
    recommendations = []
    for raw_event in event_rows:
        match = _match(raw_event)
        city_metric = metric_rows.get(match.city, {})
        historical_label = validation_label(validation, city=match.city)
        movement = build_movement_scenario(match, validation_status=historical_label)
        city_walk = walking.get(match.city, {}) if isinstance(walking.get(match.city, {}), Mapping) else {}
        route_heat = city_metric.get("heat_index_c_p90")
        walk_metrics = {
            "network_walk_distance_m": city_walk.get("network_distance_m"),
            "straight_line_distance_m": city_walk.get("straight_distance_m"),
            "route_heat_exposure_c": route_heat,
            "status": city_walk.get("status", EvidenceStatus.UNAVAILABLE.value),
        }
        city_gtfs = gtfs.get(match.city, {}) if isinstance(gtfs.get(match.city, {}), Mapping) else {}
        match_service = city_gtfs.get("matches", {}).get(match.match_id, {}) if isinstance(city_gtfs.get("matches", {}), Mapping) else {}
        access = build_access_gap_result(
            movement,
            _event_service(city_gtfs, match.match_id),
            walk_metrics,
            service_span_after_match_min=match_service.get("service_span_after_match_min"),
            route_heat_exposure_c=route_heat,
        )

        transit_score = city_metric.get("transit_score")
        private_share = 0.60 if transit_score is None or pd.isna(transit_score) else max(0.25, min(0.75, 0.75 - float(transit_score) / 200))
        external_share = _origin_share(artifacts, match.city)
        average_trip = 12.0 + 18.0 * external_share
        network_distance = float(city_walk.get("network_distance_m") or 1200.0)
        city_inputs = CityInterventionInputs(
            city=match.city,
            match_id=match.match_id,
            private_vehicle_share=private_share,
            average_vehicle_occupancy=2.2,
            average_private_trip_miles=average_trip,
            venue_area_leg_miles=min(5.0, average_trip * 0.35),
            shuttle_round_trip_miles=12.0 + 2.0 * network_distance / 1609.344,
            transit_round_trip_miles=18.0,
            park_ride_feeder_round_trip_miles=16.0,
            bike_access_distance_m=max(network_distance, 250.0),
            walk_corridor_length_km=max(1.0, network_distance * 3.0 / 1000.0),
        )
        city_outcomes = [
            evaluate_intervention(package, match, movement, access, city_inputs)
            for package in named_packages().values()
        ]
        city_recommendations = pareto_recommendations(match, movement, access, city_inputs)
        if access.status == EvidenceStatus.UNAVAILABLE:
            city_recommendations = [
                replace(
                    item,
                    status=EvidenceStatus.PARTIAL,
                    rationale="Screening option under unavailable event-transit evidence. " + item.rationale,
                    dependencies=("Pinned event-window GTFS capacity", *item.dependencies),
                )
                for item in city_recommendations
            ]

        movements.append(movement.to_dict())
        access_results.append(access.to_dict())
        outcomes.extend(item.to_dict() for item in city_outcomes)
        recommendations.extend(item.to_dict() for item in city_recommendations)

    return {
        "movement_scenarios": movements,
        "access_gaps": access_results,
        "intervention_outcomes": outcomes,
        "investment_recommendations": recommendations,
        "movement_validation": validation.to_dict("records"),
    }
