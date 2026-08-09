"""Portfolio-first landing page for all FIFA 2026 U.S. host cities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from dashboard.domain.overview import build_portfolio_overview
from dashboard.models.resilience import stress_access_capacity
from dashboard.ui.theme import metric_card, page_header, section_header
from dashboard.viz.portfolio import (
    portfolio_access_chart,
    portfolio_actions_chart,
    portfolio_climate_chart,
    portfolio_outcome_chart,
    portfolio_resilience_chart,
    portfolio_traffic_chart,
    portfolio_visitor_forecast_chart,
    readiness_components_chart,
    readiness_ranking_chart,
)


def _number(value: Any, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.{decimals}f}{suffix}"


def _metric_grid(items: list[tuple[str, str, str, str, str]]) -> None:
    for start in range(0, len(items), 2):
        for column, item in zip(st.columns(2), items[start : start + 2]):
            value, label, status, note, accent = item
            with column:
                st.markdown(metric_card(value, label, status, note=note, accent=accent), unsafe_allow_html=True)


def _navigate(workspace: str, city: str | None = None) -> None:
    st.session_state["workspace"] = workspace
    if city:
        st.session_state["city_focus"] = city
        st.session_state["selected_city_context"] = city


def _with_access_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    demand = pd.to_numeric(result.get("peak_demand_pph"), errors="coerce")
    gap = pd.to_numeric(result.get("capacity_qualified_gap_pph"), errors="coerce").clip(lower=0)
    result["scheduled_transit_capacity_pph"] = (demand - gap).clip(lower=0)
    result["scheduled_coverage_pct"] = np.where(
        demand > 0,
        result["scheduled_transit_capacity_pph"] / demand * 100,
        np.nan,
    )
    return result


def _direction_peak(
    rows: list[Mapping[str, Any]], direction: str, case: str
) -> tuple[float | None, float | None]:
    field = f"{direction}_{case}"
    candidates = [row for row in rows if pd.notna(pd.to_numeric(row.get(field), errors="coerce"))]
    if not candidates:
        return None, None
    peak = max(candidates, key=lambda row: float(row.get(field) or 0))
    return float(peak.get(field) or 0), float(peak.get("hours_from_kickoff") or 0)


def _with_track1_metrics(
    frame: pd.DataFrame, artifacts: Mapping[str, Any]
) -> pd.DataFrame:
    """Add auditable movement, access-leg, resilience, and outcome fields."""

    result = _with_access_metrics(frame)
    movements = {
        (str(row.get("city")), str(row.get("match_id"))): row
        for row in artifacts.get("movement_scenarios", [])
    }
    forecasts_by_city: dict[str, list[Mapping[str, Any]]] = {}
    for forecast_row in artifacts.get("visitor_flow_forecasts", []):
        forecasts_by_city.setdefault(str(forecast_row.get("city")), []).append(
            forecast_row
        )
    access_rows = list(artifacts.get("access_gaps", []))
    access = {
        (str(row.get("city")), str(row.get("match_id"))): row
        for row in access_rows
    }
    walking = artifacts.get("walking_networks", {})

    additions: list[dict[str, Any]] = []
    for row in result.to_dict("records"):
        city = str(row.get("city"))
        match_id = str(row.get("representative_match_id") or "")
        movement = movements.get((city, match_id), {})
        forecast = _city_forecast_summary(forecasts_by_city.get(city, []))
        hourly = list(movement.get("hourly_rows", []))
        movement_fields: dict[str, Any] = {
            "movement_status": str(movement.get("status") or "unavailable"),
            "movement_uncertainty": str(
                movement.get("uncertainty_type") or "not available"
            ),
        }
        for direction in ("arrivals", "departures"):
            prefix = "arrival" if direction == "arrivals" else "departure"
            for case in ("low", "base", "high"):
                value, offset = _direction_peak(hourly, direction, case)
                movement_fields[f"{prefix}_peak_{case}"] = value
                if case == "base":
                    movement_fields[f"{prefix}_peak_offset_hours"] = offset

        access_row = access.get((city, match_id), {})
        peak_row = max(
            hourly,
            key=lambda item: float(item.get("total_movement_base") or 0),
            default={},
        )
        arrivals = float(peak_row.get("arrivals_base") or 0)
        departures = float(peak_row.get("departures_base") or 0)
        peak_direction = "arrival" if arrivals > departures else "departure"
        if arrivals == departures:
            peak_direction = "both"

        city_access = [item for item in access_rows if str(item.get("city")) == city]
        zero_capacity_matches = sum(
            float(item.get("transit_capacity_base") or 0) <= 0
            and bool(item.get("capacity_qualified", False))
            for item in city_access
        )
        walk = walking.get(city, {}) if isinstance(walking, Mapping) else {}
        target = walk.get("target_stop") or {}
        demand_value = pd.to_numeric(row.get("peak_demand_pph"), errors="coerce")
        capacity_value = pd.to_numeric(
            row.get("scheduled_transit_capacity_pph"), errors="coerce"
        )
        resilience = (
            stress_access_capacity(demand_value, capacity_value)
            if pd.notna(demand_value) and pd.notna(capacity_value)
            else {
                "stressed_coverage_pct": None,
                "stressed_gap_pph": None,
                "stressed_demand_pph": None,
                "stressed_capacity_pph": None,
            }
        )
        additions.append(
            {
                **movement_fields,
                **_forecast_fields(forecast),
                "peak_direction": peak_direction,
                "peak_offset_hours": peak_row.get("hours_from_kickoff"),
                "zero_capacity_matches": zero_capacity_matches,
                "city_match_count": len(city_access),
                "network_walk_distance_m": access_row.get("network_walk_distance_m"),
                "walking_status": str(access_row.get("walking_status") or "unavailable"),
                "service_span_after_match_min": access_row.get(
                    "service_span_after_match_min"
                ),
                "route_heat_exposure_c": access_row.get("route_heat_exposure_c"),
                "target_stop_name": target.get("name") or "No event stop path",
                "target_route": target.get("route") or "Not established",
                "walk_detour_ratio": walk.get("detour_ratio"),
                "accessibility_status": str(
                    walk.get("accessibility_status") or "not measured"
                ),
                "stress_coverage_pct": resilience["stressed_coverage_pct"],
                "stress_gap_pph": resilience["stressed_gap_pph"],
                "stress_demand_pph": resilience["stressed_demand_pph"],
                "stress_capacity_pph": resilience["stressed_capacity_pph"],
            }
        )
    return pd.concat(
        [result.reset_index(drop=True), pd.DataFrame(additions)], axis=1
    )


def _city_forecast_summary(
    forecasts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate compatible match attendance flows into one city-tournament view."""

    if not forecasts:
        return {}
    anchor = max(
        forecasts,
        key=lambda row: float(row.get("non_host_market_attendees_base") or 0),
    )
    summary: dict[str, Any] = dict(anchor)
    summary["forecast_match_count"] = len(forecasts)
    for field in (
        "attendance_low",
        "attendance_base",
        "attendance_high",
        "non_host_market_attendees_base",
    ):
        summary[field] = sum(float(row.get(field) or 0) for row in forecasts)
    base_total = float(summary["attendance_base"] or 0)
    summary["non_host_market_share_base"] = (
        float(summary["non_host_market_attendees_base"]) / base_total
        if base_total
        else 0.0
    )
    for collection, key in (("origin_rows", "origin_type"), ("mode_rows", "mode")):
        names = {
            str(item.get(key))
            for forecast in forecasts
            for item in forecast.get(collection, [])
        }
        rows: list[dict[str, Any]] = []
        for name in sorted(names):
            combined: dict[str, Any] = {key: name}
            for case in ("low", "base", "high"):
                count = sum(
                    float(item.get(f"attendees_{case}") or 0)
                    for forecast in forecasts
                    for item in forecast.get(collection, [])
                    if str(item.get(key)) == name
                )
                total = float(summary[f"attendance_{case}"] or 0)
                combined[f"attendees_{case}"] = count
                combined[f"share_{case}"] = count / total if total else 0.0
            rows.append(combined)
        summary[collection] = rows
    return summary


def _forecast_fields(forecast: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the representative forecast without hiding its scenario status."""

    fields: dict[str, Any] = {
        "forecast_stage": forecast.get("stage"),
        "forecast_anchor_match_id": forecast.get("match_id"),
        "forecast_match_count": forecast.get("forecast_match_count"),
        "forecast_status": str(forecast.get("status") or "unavailable"),
        "forecast_validation_status": str(
            forecast.get("validation_status") or "not available"
        ),
        "forecast_attendance_base": forecast.get("attendance_base"),
        "forecast_non_host_attendees_base": forecast.get(
            "non_host_market_attendees_base"
        ),
        "forecast_non_host_share_pct": (
            float(forecast.get("non_host_market_share_base")) * 100
            if pd.notna(
                pd.to_numeric(
                    forecast.get("non_host_market_share_base"), errors="coerce"
                )
            )
            else None
        ),
        "forecast_origin_prior_status": str(
            forecast.get("origin_prior_status") or "unavailable"
        ),
        "forecast_origin_prior_coverage_pct": forecast.get(
            "origin_prior_coverage_pct"
        ),
        "forecast_arrival_peak_low": forecast.get("arrival_peak_low"),
        "forecast_arrival_peak_base": forecast.get("arrival_peak_base"),
        "forecast_arrival_peak_high": forecast.get("arrival_peak_high"),
        "forecast_arrival_peak_offset_hours": forecast.get(
            "arrival_peak_offset_hours"
        ),
        "forecast_departure_peak_low": forecast.get("departure_peak_low"),
        "forecast_departure_peak_base": forecast.get("departure_peak_base"),
        "forecast_departure_peak_high": forecast.get("departure_peak_high"),
        "forecast_departure_peak_offset_hours": forecast.get(
            "departure_peak_offset_hours"
        ),
    }
    origin_columns = {
        "Host market": "origin_host_market",
        "Nearby U.S.": "origin_nearby_us",
        "Long-distance U.S.": "origin_long_distance_us",
        "International / unobserved": "origin_international",
    }
    for row in forecast.get("origin_rows", []):
        prefix = origin_columns.get(str(row.get("origin_type")))
        if prefix:
            fields[f"{prefix}_attendees_base"] = row.get("attendees_base")
            fields[f"{prefix}_share_pct"] = (
                float(row.get("share_base")) * 100
                if pd.notna(pd.to_numeric(row.get("share_base"), errors="coerce"))
                else None
            )
    mode_columns = {
        "Scheduled transit": "mode_scheduled_transit",
        "Event shuttle / coach": "mode_shuttle_coach",
        "Private vehicle / taxi": "mode_private_taxi",
        "Walk / bike to venue": "mode_walk_bike",
    }
    for row in forecast.get("mode_rows", []):
        prefix = mode_columns.get(str(row.get("mode")))
        if prefix:
            fields[f"{prefix}_attendees_base"] = row.get("attendees_base")
            fields[f"{prefix}_share_pct"] = (
                float(row.get("share_base")) * 100
                if pd.notna(pd.to_numeric(row.get("share_base"), errors="coerce"))
                else None
            )
    return fields


def _readiness_table(frame: pd.DataFrame, metrics: pd.DataFrame) -> pd.DataFrame:
    components = metrics[
        ["city", "transit_score", "heat_score", "uhi_score", "access_score"]
    ].copy()
    display = frame[["city", "strict_rank", "strict_score"]].merge(components, on="city", how="left")
    display = display.sort_values(["strict_rank", "city"], na_position="last")
    display.columns = [
        "City",
        "Readiness rank",
        "Combined readiness",
        "Transit proximity",
        "Heat safety",
        "Urban heat safety",
        "Venue support",
    ]
    return display


def _access_table(frame: pd.DataFrame) -> pd.DataFrame:
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


def _resilience_table(frame: pd.DataFrame) -> pd.DataFrame:
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
        display[column] = display[column].map(
            lambda value: f"{value:.1f}%" if pd.notna(value) else "Not available"
        )
    return display


def _movement_table(frame: pd.DataFrame) -> pd.DataFrame:
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


def _actions_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["top_gap_resolved", "city"], ascending=[False, True]).copy()
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


def _outcomes_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["top_gap_resolved", "city"], ascending=[False, True]).copy()
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


def _traffic_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["baseline_vehicle_trips_base", "city"], ascending=[False, True]).copy()
    display = display[
        [
            "city",
            "representative_match_id",
            "baseline_vehicle_trips_low",
            "baseline_vehicle_trips_base",
            "baseline_vehicle_trips_high",
        ]
    ]
    display.columns = [
        "City",
        "Representative match",
        "Low input case",
        "Base input case",
        "High input case",
    ]
    return display


def _climate_table(frame: pd.DataFrame) -> pd.DataFrame:
    display = frame.sort_values(["top_net_co2e_kg", "city"], ascending=[False, True]).copy()
    display = display[
        [
            "city",
            "representative_match_id",
            "lowest_cost_intervention",
            "top_scope",
            "top_net_co2e_kg",
            "top_evidence_quality",
        ]
    ]
    display.columns = [
        "City",
        "Representative match",
        "Qualified single measure",
        "Proposed scale",
        "Net CO2e avoided (kg)",
        "Evidence quality",
    ]
    return display


def _render_home_legacy(metrics: pd.DataFrame, artifacts: Mapping[str, Any], weights: Mapping[str, float]) -> None:
    """Retain the previous portfolio presentation during the Track 1 transition."""

    page_header(
        "Transportation & access",
        "FIFA 2026 Host City Mobility Readiness",
        "Start with the overall readiness order, understand which criteria drive it, then move into narrower access, traffic, and climate questions.",
        ("11 U.S. host cities", "Rank → drivers → task evidence", "No city filter"),
    )
    frame = _with_access_metrics(
        build_portfolio_overview(
            metrics,
            artifacts.get("access_gaps", []),
            artifacts.get("investment_recommendations", []),
            artifacts.get("intervention_outcomes", []),
            weights=weights,
        )
    )
    ranked = frame.dropna(subset=["strict_rank", "strict_score"]).sort_values("strict_rank")
    highest = ranked.iloc[0] if not ranked.empty else None
    readiness_order = frame.dropna(subset=["strict_score"]).sort_values(["strict_score", "city"])["city"].tolist()

    section_header(
        "How do hosts rank on overall readiness?",
        "This is the high-level orientation across all 11 hosts. It combines four normalized criteria under the current sidebar weights; it is not an investment recommendation.",
        "1 · Readiness rank",
    )
    st.plotly_chart(
        readiness_ranking_chart(frame),
        width="stretch",
        config={"displayModeBar": False},
        key="overview_readiness_rank",
    )
    st.caption(
        f"{highest['city']} ranks first at {_number(highest['strict_score'], decimals=1)} under the current weights. "
        "Use the next figure to see why; do not interpret rank as the size of an access gap or expected return on investment."
        if highest is not None
        else "No city has enough eligible evidence for the current readiness ranking."
    )

    st.markdown("#### What drives the rank?")
    st.caption(
        "The grid decomposes the combined score. Darker cells mean a higher normalized criterion score, allowing a reader to distinguish transit proximity from heat and venue-support evidence."
    )
    st.plotly_chart(
        readiness_components_chart(metrics, readiness_order),
        width="stretch",
        config={"displayModeBar": False},
        key="overview_readiness_components",
    )

    with st.container(border=True):
        definitions = [
            ("Transit proximity", "Relative GTFS stops and routes near the venue. It does not measure event-hour capacity."),
            ("Heat safety", "Inverse of the June–July 90th-percentile heat index. Higher means less heat exposure."),
            ("Urban heat safety", "Inverse of the venue-area urban heat-island anomaly. Higher means less local heat amplification."),
            ("Venue support", "Nearby support destinations relative to other hosts. It is not a walking-safety or accessibility audit."),
        ]
        for start in range(0, len(definitions), 2):
            for column, (label, definition) in zip(st.columns(2), definitions[start : start + 2]):
                with column:
                    st.markdown(f"**{label}**")
                    st.caption(definition)
        weight_text = " · ".join(
            f"{label} {float(weights.get(key, 0)):.0%}"
            for label, key in (
                ("Transit", "transit"),
                ("Heat", "heat"),
                ("Urban heat", "uhi"),
                ("Venue support", "access"),
            )
        )
        st.caption(f"Current weight profile: {weight_text}. Scores are normalized 0–100 across these hosts.")

    with st.expander("Exact readiness scores", icon=":material/table_chart:"):
        st.dataframe(_readiness_table(frame, metrics), hide_index=True, width="stretch", height=455)

    largest_gap = frame.dropna(subset=["capacity_qualified_gap_pph"]).sort_values(
        "capacity_qualified_gap_pph", ascending=False
    )
    largest_gap_row = largest_gap.iloc[0] if not largest_gap.empty else None
    coverage = pd.to_numeric(frame["scheduled_coverage_pct"], errors="coerce").dropna()
    zero_capacity = int((pd.to_numeric(frame["scheduled_transit_capacity_pph"], errors="coerce").fillna(0) <= 0).sum())
    traffic = frame.dropna(subset=["baseline_vehicle_trips_base"]).sort_values(
        "baseline_vehicle_trips_base", ascending=False
    )
    highest_traffic = traffic.iloc[0] if not traffic.empty else None
    traffic_values = pd.to_numeric(frame["baseline_vehicle_trips_base"], errors="coerce").dropna()
    climate = frame.dropna(subset=["top_net_co2e_kg"]).sort_values("top_net_co2e_kg", ascending=False)
    highest_climate = climate.iloc[0] if not climate.empty else None
    climate_values = pd.to_numeric(frame["top_net_co2e_kg"], errors="coerce").dropna()

    section_header(
        "What does each transportation task show?",
        "Now narrow from the readiness screen to one task-specific question at a time. Each tab uses a different unit and answers a different decision question.",
        "2 · Task-specific evidence",
    )
    access_tab, traffic_tab, climate_tab = st.tabs(
        [
            ":material/train: Access shortfall",
            ":material/traffic: Traffic pressure",
            ":material/eco: Climate outcome",
        ]
    )
    with access_tab:
        st.markdown("#### Can scheduled transit cover the representative peak hour?")
        _metric_grid(
            [
                (
                    _number(largest_gap_row["capacity_qualified_gap_pph"], " pph")
                    if largest_gap_row is not None else "Not available",
                    f"Largest gap — {largest_gap_row['city']}" if largest_gap_row is not None else "Largest remaining peak gap",
                    "scenario",
                    "Scheduled transit shortfall in its representative peak hour",
                    "coral",
                ),
                (
                    f"{coverage.median():.1f}%" if not coverage.empty else "Not available",
                    "Median scheduled coverage",
                    "derived",
                    f"{zero_capacity} of {len(frame)} hosts have zero matched capacity in that hour",
                    "teal",
                ),
            ]
        )
        st.plotly_chart(
            portfolio_access_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="overview_access_coverage",
        )
        st.caption(
            "Scheduled coverage = event-valid scheduled passenger capacity in the matching hour ÷ modeled base peak arrivals. "
            "Each city uses its most constrained capacity-qualified match. The remaining gap is not roadway congestion, "
            "observed ridership, or a citywide daily total."
        )
        with st.expander("Exact access values", icon=":material/table_chart:"):
            st.dataframe(_access_table(frame), hide_index=True, width="stretch", height=455)

    with traffic_tab:
        st.markdown("#### How many venue-area vehicle trips does the base case imply?")
        _metric_grid(
            [
                (
                    _number(highest_traffic["baseline_vehicle_trips_base"], " trips")
                    if highest_traffic is not None else "Not available",
                    f"Highest base pressure — {highest_traffic['city']}" if highest_traffic is not None else "Highest base traffic pressure",
                    "scenario",
                    "Modeled private vehicle trips for the representative match",
                    "blue",
                ),
                (
                    _number(traffic_values.median(), " trips") if not traffic_values.empty else "Not available",
                    "Median base traffic pressure",
                    "scenario",
                    "Across the 11 representative match scenarios",
                    "blue",
                ),
            ]
        )
        st.plotly_chart(
            portfolio_traffic_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="overview_baseline_traffic",
        )
        st.caption(
            "Baseline vehicle trips = modeled attendance × assumed private-vehicle share ÷ 2.2 occupants per vehicle. "
            "Whiskers span the named low and high input cases. This is venue-area trip pressure, not measured roadway congestion, delay, or queue length."
        )
        with st.expander("Exact traffic values", icon=":material/table_chart:"):
            st.dataframe(_traffic_table(frame), hide_index=True, width="stretch", height=455)

    with climate_tab:
        st.markdown("#### What net CO2e benefit does the common qualified measure imply?")
        _metric_grid(
            [
                (
                    _number(highest_climate["top_net_co2e_kg"], " kg")
                    if highest_climate is not None else "Not available",
                    f"Largest modeled benefit — {highest_climate['city']}" if highest_climate is not None else "Largest modeled climate benefit",
                    "scenario",
                    "Base-case net CO2e avoided by the qualified single measure",
                    "teal",
                ),
                (
                    _number(climate_values.median(), " kg") if not climate_values.empty else "Not available",
                    "Median modeled climate benefit",
                    "scenario",
                    "Across the 11 representative match screens",
                    "teal",
                ),
            ]
        )
        st.plotly_chart(
            portfolio_climate_chart(frame),
            width="stretch",
            config={"displayModeBar": False},
            key="overview_single_measure_climate",
        )
        st.caption(
            "Every city's lowest-cost qualified screen is the same proposed scale: add 6 transit departures per hour in the event window. "
            "Net CO2e avoided subtracts added transit-service emissions from displaced private-vehicle emissions; positive values mean modeled avoidance. "
            "The result varies with modeled private trip distance. It is a base-case scenario—not an observed reduction, certified inventory, or package forecast."
        )
        with st.expander("Exact climate values", icon=":material/table_chart:"):
            st.dataframe(_climate_table(frame), hide_index=True, width="stretch", height=455)

    priority_city = str(largest_gap_row["city"]) if largest_gap_row is not None else None
    section_header(
        "Open the priority case",
        "Continue with the largest documented representative peak gap. The action plan shows concrete investment screens, scope, cost, owner, dependencies, and evidence limits.",
        "3 · Drill down",
    )
    st.button(
        f"Open {priority_city} action plan" if priority_city else "Open priority city action plan",
        key="overview_open_city",
        on_click=_navigate,
        args=("City Brief", priority_city),
        disabled=priority_city is None,
        width="stretch",
    )
    st.button(
        "Review methods, assumptions, and sources",
        on_click=_navigate,
        args=("Methods & QA",),
        key="overview_open_methods",
        width="stretch",
    )
    st.download_button(
        "Download exact overview comparison CSV",
        frame[[column for column in frame.columns if not column.startswith("package_")]].to_csv(index=False),
        file_name="host-city-mobility-overview.csv",
        mime="text/csv",
        width="stretch",
    )


def render_home(metrics: pd.DataFrame, artifacts: Mapping[str, Any], weights: Mapping[str, float]) -> None:
    """Render a direct, all-city comparison for every Track 1 objective."""

    page_header(
        "Transportation & access",
        "FIFA 2026 Host City Mobility Readiness",
        "Compare resilience, modeled visitor movement, first/last-mile gaps, concrete actions, and decision outcomes across every U.S. host.",
        ("11 cities at once", "5 Track 1 objectives", "No portfolio map or city filter"),
    )
    frame = _with_track1_metrics(
        build_portfolio_overview(
            metrics,
            artifacts.get("access_gaps", []),
            artifacts.get("investment_recommendations", []),
            artifacts.get("intervention_outcomes", []),
            weights=weights,
        ),
        artifacts,
    )
    ranked = frame.dropna(subset=["strict_rank", "strict_score"]).sort_values("strict_rank")
    highest = ranked.iloc[0] if not ranked.empty else None
    readiness_order = ranked["city"].tolist() + [
        city for city in frame["city"].tolist() if city not in set(ranked["city"])
    ]

    largest_gap = frame.dropna(subset=["capacity_qualified_gap_pph"]).sort_values(
        "capacity_qualified_gap_pph", ascending=False
    )
    largest_gap_row = largest_gap.iloc[0] if not largest_gap.empty else None
    stress_values = pd.to_numeric(frame["stress_coverage_pct"], errors="coerce").dropna()
    zero_capacity_matches = int(
        pd.to_numeric(frame["zero_capacity_matches"], errors="coerce").fillna(0).sum()
    )
    match_count = int(
        pd.to_numeric(frame["city_match_count"], errors="coerce").fillna(0).sum()
    )
    missing_walk_paths = int((frame["walking_status"] == "unavailable").sum())
    forecast_rows = frame.dropna(
        subset=["forecast_non_host_attendees_base"]
    ).sort_values(
        "forecast_non_host_attendees_base", ascending=False
    )
    highest_external = forecast_rows.iloc[0] if not forecast_rows.empty else None
    planning_scenarios = int((frame["forecast_status"] == "scenario").sum())
    actions = frame.dropna(subset=["top_gap_resolved"]).sort_values(
        "top_gap_resolved", ascending=False
    )
    highest_action = actions.iloc[0] if not actions.empty else None
    distinct_actions = int(frame["top_intervention"].dropna().nunique())
    qualified_action_cities = int(frame["top_option_qualified"].fillna(False).sum())

    section_header(
        "Compare every Track 1 objective",
        "Each tab answers one decision question with one all-city comparison. Definitions and limitations stay next to the number; exact values remain available on demand.",
        "Track 1 scorecard",
    )
    (
        resilience_tab,
        movement_tab,
        access_tab,
        actions_tab,
        outcomes_tab,
    ) = st.tabs(
        [
            ":material/health_and_safety: Resilience",
            ":material/route: Visitor movement",
            ":material/transfer_within_a_station: First/last mile",
            ":material/construction: Investments & strategies",
            ":material/monitoring: Outcomes",
        ],
        key="track1_objective",
        on_change="rerun",
    )

    if resilience_tab.open:
        with resilience_tab:
            st.markdown("#### How do hosts rank, and how much scheduled coverage survives a common stress?")
            _metric_grid(
                [
                    (
                        f"#{int(highest['strict_rank'])} - {highest['city']}" if highest is not None else "Not available",
                        "Overall readiness leader",
                        "derived",
                        f"{_number(highest['strict_score'], decimals=1)} / 100 under current weights" if highest is not None else "Eligible evidence required",
                        "teal",
                    ),
                    (
                        f"{stress_values.median():.1f}%" if not stress_values.empty else "Not available",
                        "Median stress-test coverage",
                        "scenario",
                        "After 10% more demand and 20% less scheduled capacity",
                        "coral",
                    ),
                ]
            )
            st.plotly_chart(
                readiness_ranking_chart(frame),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_readiness_rank",
            )
            st.caption(
                "Readiness combines transit proximity, heat safety, urban heat safety, and venue support under the visible sidebar weights. "
                "It is orientation, not a transport disruption model or an investment ranking."
            )
            st.markdown("##### Transportation stress test")
            st.plotly_chart(
                portfolio_resilience_chart(frame),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_resilience_stress",
            )
            st.caption(
                "The same sensitivity is applied to every representative match: peak movement rises 10% while scheduled passenger capacity falls 20%. "
                "This reports retained scheduled coverage in physical units; it is not the probability of a disruption."
            )
            with st.expander("What drives readiness?", icon=":material/grid_view:"):
                st.plotly_chart(
                    readiness_components_chart(metrics, readiness_order),
                    width="stretch",
                    config={"displayModeBar": False},
                    key="portfolio_readiness_components",
                )
                st.caption(
                    "Transit proximity counts relative nearby GTFS service; heat metrics invert exposure; venue support counts nearby destinations. "
                    "None of these substitutes for event-hour capacity, walking safety, or ADA evidence."
                )
            with st.expander("Exact resilience values", icon=":material/table_chart:"):
                st.dataframe(_resilience_table(frame), hide_index=True, width="stretch", height=455)

    if movement_tab.open:
        with movement_tab:
            st.markdown("#### Where are World Cup attendees forecast to come from, and how might they reach the venue?")
            _metric_grid(
                [
                    (
                        _number(highest_external["forecast_non_host_attendees_base"], " attendees") if highest_external is not None else "Not available",
                        f"Largest non-host-market forecast - {highest_external['city']}" if highest_external is not None else "Largest non-host-market forecast",
                        "scenario",
                        f"{_number(highest_external['forecast_non_host_share_pct'], '%', 1)} of base city-tournament attendance" if highest_external is not None else "Base city-tournament attendance",
                        "violet",
                    ),
                    (
                        f"{planning_scenarios} of {len(frame)}",
                        "Cities labeled scenario forecast",
                        "scenario",
                        "No city has observed FIFA fan origin and mode calibration",
                        "amber",
                    ),
                ]
            )
            forecast_view = st.segmented_control(
                "Forecast view",
                ["Origin mix", "Mode mix", "Peak timing"],
                default="Origin mix",
                required=True,
                key="portfolio_forecast_view",
                width="stretch",
                persist_state="session",
            )
            st.plotly_chart(
                portfolio_visitor_forecast_chart(frame, str(forecast_view)),
                width="stretch",
                config={"displayModeBar": False},
                key=f"portfolio_visitor_forecast_{str(forecast_view).lower().replace(' ', '_')}",
            )
            forecast_caption = {
                "Origin mix": (
                    "The forecast allocates every hosted match attendance case to host-market, nearby U.S., long-distance U.S., and international/unobserved origin types, then aggregates compatible attendee counts across the city tournament. "
                    "Supplied commercial customer origins shape only the U.S. prior; international share is an explicit tournament-stage scenario. Neither is observed FIFA fan behavior."
                ),
                "Mode mix": (
                    "Broad mode demand responds to transit readiness, exact-hour scheduled coverage, access-gap severity, and venue-side walking evidence. "
                    "It predicts planning demand for transit, shuttles/coaches, private vehicles/taxis, and walk/bike access—not delivered service, exact routes, travel time, or measured mode share."
                ),
                "Peak timing": (
                    "The city's highest non-host-demand match anchors this timing view. Official local kickoff anchors fixed low/base/high arrival and post-match departure profiles. "
                    "The timing curve reconciles to attendance but is not calibrated to ticket scans or observed FIFA crowd movement."
                ),
            }[str(forecast_view)]
            st.caption(forecast_caption)
            with st.expander("Exact movement values", icon=":material/table_chart:"):
                st.dataframe(_movement_table(frame), hide_index=True, width="stretch", height=455)

    if access_tab.open:
        with access_tab:
            st.markdown("#### Where does the venue-side journey fail in the modeled peak hour?")
            _metric_grid(
                [
                    (
                        _number(largest_gap_row["capacity_qualified_gap_pph"], " / hr") if largest_gap_row is not None else "Not available",
                        f"Largest scheduled-capacity gap - {largest_gap_row['city']}" if largest_gap_row is not None else "Largest scheduled-capacity gap",
                        "scenario",
                        f"{largest_gap_row['peak_direction']} peak for the representative match" if largest_gap_row is not None else "Peak direction unavailable",
                        "coral",
                    ),
                    (
                        f"{zero_capacity_matches} of {match_count}",
                        "Matches with zero scheduled half-mile capacity",
                        "derived",
                        f"{missing_walk_paths} cities also lack an event-stop walking path",
                        "amber",
                    ),
                ]
            )
            st.plotly_chart(
                portfolio_access_chart(frame),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_first_last_mile",
            )
            st.caption(
                "Scheduled coverage = event-valid scheduled passenger capacity in the exact peak hour and direction divided by modeled peak movement. "
                "Walking evidence covers one event-relevant stop-to-venue path; it is the venue-side last mile for arrivals and first mile for departures, not an origin-to-venue accessibility or safety audit."
            )
            with st.expander("Exact first/last-mile values", icon=":material/table_chart:"):
                st.dataframe(_access_table(frame), hide_index=True, width="stretch", height=455)

    if actions_tab.open:
        with actions_tab:
            st.markdown("#### What concrete measure should each host validate first?")
            _metric_grid(
                [
                    (
                        f"{distinct_actions} measure types",
                        "Bottleneck-matched priority screens",
                        "scenario",
                        "Zero service, long approaches, heat, and existing route capacity trigger different screens",
                        "teal",
                    ),
                    (
                        f"{qualified_action_cities} of {len(frame)}",
                        "Cities with a qualified priority screen",
                        "scenario",
                        _number(highest_action["top_gap_resolved"], " / hr") + " is the largest modeled single-measure benefit" if highest_action is not None else "No qualified benefit available",
                        "blue",
                    ),
                ]
            )
            st.plotly_chart(
                portfolio_actions_chart(frame),
                width="stretch",
                config={"displayModeBar": False},
                key="portfolio_priority_actions",
            )
            st.caption(
                "The priority is a transparent bottleneck-matched screening measure, not an automatic winner or agency commitment. "
                "Operational/capital is retained as delivery and cost metadata on each measure; composite packages remain only in the advanced scenario explorer."
            )
            with st.expander("Exact investment and strategy values", icon=":material/table_chart:"):
                st.dataframe(_actions_table(frame), hide_index=True, width="stretch", height=455)

    if outcomes_tab.open:
        with outcomes_tab:
            st.markdown("#### What does each city's priority single measure change?")
            outcome = st.segmented_control(
                "Outcome to compare",
                ["Access", "Traffic", "CO2e"],
                default="Access",
                required=True,
                key="portfolio_outcome_metric",
                width="stretch",
                persist_state="session",
            )
            outcome_column = {
                "Access": "top_gap_resolved",
                "Traffic": "top_vehicle_trips_avoided",
                "CO2e": "top_net_co2e_kg",
            }[str(outcome)]
            outcome_values = pd.to_numeric(frame[outcome_column], errors="coerce").dropna()
            outcome_rows = frame.dropna(subset=[outcome_column]).sort_values(
                outcome_column, ascending=False
            )
            best_outcome = outcome_rows.iloc[0] if not outcome_rows.empty else None
            unit = {"Access": " / hr", "Traffic": " trips", "CO2e": " kg"}[str(outcome)]
            outcome_label = {
                "Access": "access",
                "Traffic": "traffic",
                "CO2e": "CO2e",
            }[str(outcome)]
            _metric_grid(
                [
                    (
                        _number(best_outcome[outcome_column], unit) if best_outcome is not None else "Not available",
                        f"Largest modeled {outcome_label} outcome - {best_outcome['city']}" if best_outcome is not None else "Largest modeled outcome",
                        "scenario",
                        str(best_outcome["top_intervention"]) if best_outcome is not None else "No qualified measure",
                        "teal",
                    ),
                    (
                        _number(outcome_values.median(), unit) if not outcome_values.empty else "Not available",
                        "Median modeled outcome",
                        "scenario",
                        "Across representative matches; values are not summed across incompatible event peaks",
                        "blue",
                    ),
                ]
            )
            st.plotly_chart(
                portfolio_outcome_chart(frame, str(outcome)),
                width="stretch",
                config={"displayModeBar": False},
                key=f"portfolio_outcome_{str(outcome).lower()}",
            )
            st.caption(
                "Access is peak passengers addressed per hour; traffic is modeled venue-area vehicle trips avoided; CO2e is net avoided emissions after added service mileage. "
                "These are planning outcomes with shared factor ranges, not observed mode shift, roadway congestion relief, or a certified emissions inventory."
            )
            with st.expander("Exact outcome values", icon=":material/table_chart:"):
                st.dataframe(_outcomes_table(frame), hide_index=True, width="stretch", height=455)

    priority_city = str(largest_gap_row["city"]) if largest_gap_row is not None else None
    section_header(
        "Open the priority case",
        "Continue from the all-city comparison to the representative match, concrete scope, delivery owner, dependencies, and evidence limits.",
        "Drill down",
    )
    st.button(
        f"Open {priority_city} action plan" if priority_city else "Open priority city action plan",
        key="overview_open_city",
        on_click=_navigate,
        args=("City Brief", priority_city),
        disabled=priority_city is None,
        width="stretch",
    )
    st.button(
        "Review methods, assumptions, and sources",
        on_click=_navigate,
        args=("Methods & QA",),
        key="overview_open_methods",
        width="stretch",
    )
    st.download_button(
        "Download exact Track 1 comparison CSV",
        frame[[column for column in frame.columns if not column.startswith("package_")]].to_csv(index=False),
        file_name="track-1-host-city-comparison.csv",
        mime="text/csv",
        width="stretch",
    )
