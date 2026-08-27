"""Exact-value table adapters for the Portfolio comparisons."""

from __future__ import annotations

import pandas as pd


def resilience_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["stress_coverage_pct", "city"], ascending=[False, True]).copy()
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
        display[column] = display[column].map(lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available")
    return display


def movement_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["forecast_non_host_attendees_base", "city"], ascending=[False, True]).copy()
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
        display[column] = display[column].map(lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available")
    return display


def access_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["capacity_qualified_gap_pph", "city"], ascending=[False, True]).copy()
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
            "transit_score",
            "parking_score",
            "first_last_mile_gap",
            "transit_stops_0_5mi",
            "gtfs_stops_1mi",
            "gtfs_stops_2mi",
            "nearest_stop_mi",
            "gtfs_agencies",
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
        "Transit score",
        "Parking score",
        "First/last-mile gap score",
        "Stops <=0.5mi",
        "Stops <=1mi",
        "Stops <=2mi",
        "Nearest stop (mi)",
        "GTFS agencies",
    ]
    display["Scheduled coverage"] = display["Scheduled coverage"].map(
        lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available"
    )
    return display
