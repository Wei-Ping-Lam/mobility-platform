"""Exact-value table adapters for the five Portfolio objectives."""

from __future__ import annotations

import pandas as pd


def resilience_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(
        ["stress_coverage_pct", "city"], ascending=[False, True]
    ).copy()
    display = display[
        [
            "city",
            "strict_rank",
            "strict_score",
            "representative_match_id",
            "scheduled_coverage_pct",
            "stress_coverage_pct",
            "stress_gap_pph",
        ]
    ]
    display.columns = [
        "City",
        "Readiness rank",
        "Readiness score",
        "Representative match",
        "Baseline scheduled coverage",
        "Stress-test coverage",
        "Remaining stressed gap / hour",
    ]
    for column in ("Baseline scheduled coverage", "Stress-test coverage"):
        display[column] = display[column].map(
            lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available"
        )
    return display


def movement_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(
        ["forecast_non_host_attendees_base", "city"], ascending=[False, True]
    ).copy()
    display = display[
        [
            "city",
            "forecast_match_count",
            "forecast_anchor_match_id",
            "forecast_stage",
            "forecast_attendance_base",
            "forecast_non_host_attendees_base",
            "origin_host_market_share_pct",
            "origin_nearby_us_share_pct",
            "origin_long_distance_us_share_pct",
            "origin_international_share_pct",
            "mode_scheduled_transit_share_pct",
            "mode_shuttle_coach_share_pct",
            "mode_private_taxi_share_pct",
            "mode_walk_bike_share_pct",
            "forecast_arrival_peak_base",
            "forecast_arrival_peak_offset_hours",
            "forecast_departure_peak_base",
            "forecast_departure_peak_offset_hours",
            "forecast_status",
            "forecast_validation_status",
            "forecast_origin_prior_status",
        ]
    ]
    display.columns = [
        "City",
        "Hosted matches",
        "Peak forecast match",
        "Peak forecast stage",
        "Base tournament attendance",
        "Non-host-market attendees",
        "Host market share",
        "Nearby U.S. share",
        "Long-distance U.S. share",
        "International / unobserved share",
        "Scheduled transit demand",
        "Shuttle / coach demand",
        "Private vehicle / taxi demand",
        "Walk / bike demand",
        "Arrival peak base",
        "Arrival peak vs kickoff (h)",
        "Departure peak base",
        "Departure peak vs kickoff (h)",
        "Forecast status",
        "Validation status",
        "Domestic origin prior",
    ]
    for column in (
        "Host market share",
        "Nearby U.S. share",
        "Long-distance U.S. share",
        "International / unobserved share",
        "Scheduled transit demand",
        "Shuttle / coach demand",
        "Private vehicle / taxi demand",
        "Walk / bike demand",
    ):
        display[column] = display[column].map(
            lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available"
        )
    return display


def access_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(
        ["capacity_qualified_gap_pph", "city"], ascending=[False, True]
    ).copy()
    display = display[
        [
            "city",
            "venue",
            "representative_match_id",
            "peak_direction",
            "peak_demand_pph",
            "scheduled_transit_capacity_pph",
            "scheduled_coverage_pct",
            "capacity_qualified_gap_pph",
            "zero_capacity_matches",
            "city_match_count",
            "target_stop_name",
            "target_route",
            "network_walk_distance_m",
            "walk_detour_ratio",
            "walking_status",
            "accessibility_status",
        ]
    ]
    display.columns = [
        "City",
        "Venue",
        "Representative match",
        "Peak direction",
        "Peak movement / hour",
        "Scheduled transit capacity / hour",
        "Scheduled coverage",
        "Remaining peak gap / hour",
        "Zero-capacity matches",
        "City matches",
        "Event-relevant stop",
        "Route",
        "Network walk (m)",
        "Walk detour ratio",
        "Walking evidence",
        "Accessibility audit",
    ]
    display["Scheduled coverage"] = display["Scheduled coverage"].map(
        lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available"
    )
    return display


def actions_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(
        ["top_gap_resolved", "city"], ascending=[False, True]
    ).copy()
    display = display[
        [
            "city",
            "representative_match_id",
            "top_intervention",
            "priority_reason",
            "top_scope",
            "top_gap_resolved",
            "top_cost_low",
            "top_cost_base",
            "top_cost_high",
            "top_lead_time",
            "top_responsible_actor",
            "top_dependencies",
            "top_evidence_quality",
            "exploratory_interventions",
        ]
    ]
    display.columns = [
        "City",
        "Representative match",
        "Priority screen",
        "Why this bottleneck",
        "Proposed scale",
        "Peak demand addressed / hour",
        "Cost low",
        "Cost base",
        "Cost high",
        "Lead time",
        "Delivery owner",
        "Dependencies",
        "Evidence quality",
        "Exploratory alternatives",
    ]
    return display


def outcomes_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(
        ["top_gap_resolved", "city"], ascending=[False, True]
    ).copy()
    display = display[
        [
            "city",
            "top_intervention",
            "top_gap_resolved",
            "top_vehicle_trips_avoided",
            "top_net_vmt_base",
            "top_net_co2e_kg",
            "top_cost_base",
            "top_evidence_quality",
        ]
    ]
    display.columns = [
        "City",
        "Priority single measure",
        "Peak passengers addressed / hour",
        "Venue-area vehicle trips avoided",
        "Net VMT avoided",
        "Net CO2e avoided (kg)",
        "Planning cost",
        "Evidence quality",
    ]
    return display
