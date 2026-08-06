"""Decision-oriented Executive, Explorer, and Methods/QA Streamlit views."""

from __future__ import annotations

import json
from typing import Any, Mapping

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.mobility_platform.sources import GTFS_SOURCE, RICE_COLLECTION, rice_source
from dashboard.models.demand import scenario_band, seasonal_baseline, validation_metrics
from dashboard.models.economics import economic_impact_range
from dashboard.ui.presentation import (
    AccessView,
    CityDecisionView,
    MovementView,
    PlatformPresentation,
    RecommendationView,
    ScenarioView,
    build_presentation,
    city_layer_records,
)
from dashboard.ui.theme import callout, evidence_row, metric_card, page_header, priority_card, section_header
from dashboard.viz.style import COLORS, SERIES_COLORS, STATUS_COLORS, discrete_status_scale, style_figure, style_map


def _safe(value: Any, suffix: str = "", decimals: int = 1) -> str:
    if value is None:
        return "Not available"
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not np.isfinite(parsed):
        return "Not available"
    if decimals == 0:
        return f"{parsed:,.0f}{suffix}"
    return f"{parsed:,.{decimals}f}{suffix}"


def _money(value: Any) -> str:
    if value is None:
        return "Not available"
    parsed = float(value)
    if abs(parsed) >= 1_000_000:
        return f"${parsed / 1_000_000:,.1f}M"
    if abs(parsed) >= 1_000:
        return f"${parsed / 1_000:,.0f}K"
    return f"${parsed:,.0f}"


def _money_range(low: Any, high: Any, base: Any = None) -> str:
    if low is not None and high is not None:
        return f"{_money(low)}–{_money(high)}"
    return _money(base)


def _number_range(low: Any, high: Any, base: Any = None, suffix: str = "") -> str:
    if low is not None and high is not None:
        return f"{_safe(low, suffix, 0)}–{_safe(high, suffix, 0)}"
    return _safe(base, suffix, 0)


def _metric_grid(items: list[tuple[str, str, str | None, str | None, str]]) -> None:
    for start in range(0, len(items), 4):
        group = items[start : start + 4]
        columns = st.columns(len(group))
        for column, (value, label, status, note, accent) in zip(columns, group):
            with column:
                st.markdown(metric_card(value, label, status, note=note, accent=accent), unsafe_allow_html=True)


def _fallback_recommendation(decision: CityDecisionView, access: AccessView) -> RecommendationView:
    missing: list[str] = []
    metric = decision.metric
    if access.peak_demand_per_hour is None:
        missing.append("match-hour demand")
    if not access.capacity_qualified:
        missing.append("event transit capacity")
    if access.network_walk_distance_m is None:
        missing.append("walking-network access")
    if missing:
        return RecommendationView(
            intervention="Complete the access evidence",
            rationale=f"Pin {', '.join(missing)} before selecting a transportation investment.",
            status="partial",
            responsible_actor="Transit and venue planning team",
            dependencies=tuple(missing),
        )
    if access.residual_passengers and access.residual_passengers > 0:
        return RecommendationView(
            intervention="Close the peak passenger gap",
            rationale="Compare added service, shuttle, active-travel, cooling, and arrival-management packages against the documented hourly shortfall.",
            status=access.status,
            gap_resolved_passengers=access.residual_passengers,
            responsible_actor="Host city mobility command",
            dependencies=("Package-level cost and operations evidence",),
        )
    weakest = min(
        ((label, metric.get(column)) for label, column in (("heat protection", "heat_score"), ("venue access", "access_score"), ("transit service", "transit_score")) if metric.get(column) is not None),
        key=lambda item: float(item[1]),
        default=("access operations", 0),
    )[0]
    return RecommendationView(
        intervention=f"Strengthen {weakest}",
        rationale="Use the scenario comparison to test measurable benefits before committing funds.",
        status=str(metric.get("score_status") or "partial"),
    )


def _comparison_option(
    recommendations: tuple[RecommendationView, ...],
) -> RecommendationView | None:
    """Choose a clearly labeled comparison example, never a universal optimum."""

    qualified = [item for item in recommendations if item.evidence_qualified]
    return min(
        qualified,
        key=lambda item: (
            item.cost_per_passenger
            if item.cost_per_passenger is not None
            else float("inf"),
            item.intervention,
        ),
        default=None,
    )


def _decision_rows(presentation: PlatformPresentation) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for city in sorted(presentation.cities):
        decision = presentation.cities[city]
        eligible_matches = [
            (match, decision.access(match.match_id))
            for match in decision.matches
            if decision.access(match.match_id).capacity_qualified
        ]
        if eligible_matches:
            match, access = max(
                eligible_matches,
                key=lambda item: float(item[1].residual_passengers or 0),
            )
        else:
            match = decision.match()
            access = decision.access(match.match_id)
        recommendations = decision.recommendation_set(match.match_id)
        recommendation = _comparison_option(recommendations)
        fallback = _fallback_recommendation(decision, access)
        capacity_qualified = access.capacity_qualified
        rows.append(
            {
                "city": city,
                "venue": decision.venue,
                "lat": decision.lat,
                "lon": decision.lon,
                "match_id": match.match_id,
                "peak_gap": access.residual_passengers if capacity_qualified else None,
                "peak_demand": access.peak_demand_per_hour,
                "investment": recommendation.intervention if recommendation else f"{len(recommendations)} exploratory options",
                "cost_range": _money_range(recommendation.cost_low, recommendation.cost_high, recommendation.cost_base) if recommendation else "Not qualified",
                "cost_base": recommendation.cost_base if recommendation else None,
                "net_co2e": recommendation.net_co2e_kg if recommendation else None,
                "lead_time": recommendation.lead_time_band if recommendation else "Requires evidence",
                "evidence": recommendation.status if recommendation else fallback.status,
                "rationale": recommendation.rationale if recommendation else fallback.rationale,
                "responsible_actor": recommendation.responsible_actor if recommendation else fallback.responsible_actor,
                "qualified_options": sum(item.evidence_qualified for item in recommendations),
                "exploratory_options": sum(not item.evidence_qualified for item in recommendations),
                "mrs": decision.metric.get("score"),
                "rankable": bool(decision.metric.get("rankable", False)),
            }
        )
    return pd.DataFrame(rows)


def _priority_map(rows: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    valid = rows.dropna(subset=["lat", "lon"])
    for status in ("observed", "derived", "scenario", "partial", "estimated", "unavailable"):
        subset = valid[valid["evidence"] == status]
        if subset.empty:
            continue
        sizes = pd.to_numeric(subset["peak_gap"], errors="coerce").fillna(
            pd.to_numeric(subset["peak_demand"], errors="coerce").fillna(0)
        )
        sizes = 13 + 18 * (sizes / max(float(sizes.max()), 1))
        figure.add_trace(
            go.Scattermap(
                lat=subset["lat"],
                lon=subset["lon"],
                mode="markers",
                marker=dict(size=sizes, color=STATUS_COLORS[status], opacity=.86),
                name=status.title(),
                customdata=subset[["city", "peak_demand", "peak_gap", "investment", "cost_range", "lead_time"]],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>Peak demand scenario: %{customdata[1]:,.0f} passengers/hour"
                    "<br>Capacity-qualified gap: %{customdata[2]:,.0f} passengers/hour"
                    "<br>Lowest comparison-cost qualified option: %{customdata[3]}<br>Total cost: %{customdata[4]}<br>Lead time: %{customdata[5]}<extra></extra>"
                ),
            )
        )
    return style_map(figure, 515, zoom=3.0, lat=38.5, lon=-96)


def render_executive(metrics: pd.DataFrame, artifacts: dict[str, Any], *, supplied_data_lens: bool = False) -> None:
    presentation = build_presentation(metrics, artifacts)
    rows = _decision_rows(presentation)
    known_gaps = rows["peak_gap"].notna().sum() if not rows.empty else 0
    known_demands = rows["peak_demand"].notna().sum() if not rows.empty else 0
    page_header(
        "Executive decision view",
        "Where mobility investment matters most",
        "Compare match-hour passenger gaps, investment choices, costs, climate outcomes, lead times, and evidence strength. Readiness scoring remains secondary.",
        (f"{len(rows)} host cities", "Match-specific planning", "Cache-only evidence"),
    )
    _metric_grid(
        [
            (str(len(rows)), "Cities in scope", None, "Current selection", "teal"),
            (str(int(known_demands)), "Cities with match demand scenarios", "scenario" if known_demands else "unavailable", "Passengers per hour", "blue"),
            (_safe(rows["peak_gap"].max() if known_gaps else None, " pph", 0), "Peak access gap — largest", "scenario" if known_gaps else "unavailable", "Not a roadway measure", "coral"),
            (str(int((rows["qualified_options"] > 0).sum())), "Cities with qualified screening options", "scenario", "No automatic winner", "amber"),
        ]
    )
    if supplied_data_lens:
        callout(
            "info",
            "Rice supplied-data lens remains context, not the transportation headline",
            "The supplied datasets inform heat, venue context, activity, origins, and economic sensitivity. Match-hour access claims require pinned public schedule, transit, and walking-network evidence.",
        )
    if known_gaps < len(rows):
        callout(
            "warning",
            f"{len(rows) - known_gaps} cities do not yet have a capacity-qualified passenger gap",
            "Match demand remains visible, but a missing transit feed is not treated as zero observed service. Missing transit or walking evidence is never replaced with an expert score.",
        )

    section_header(
        "Priority city map",
        "Marker size reflects the capacity-qualified gap where available, otherwise the match demand scenario. Written labels and the table provide alternatives to color.",
        "Where",
    )
    map_column, table_column = st.columns([1.35, 1], gap="large")
    with map_column:
        st.plotly_chart(_priority_map(rows), width="stretch", config={"displayModeBar": False})
        st.caption("Venue points are not corridor boundaries. Open Explorer for route-ready layers and missing-data warnings.")
    with table_column:
        display = rows[["city", "peak_demand", "peak_gap", "qualified_options", "exploratory_options", "investment", "cost_range", "lead_time", "evidence"]].copy()
        display["peak_demand"] = pd.to_numeric(display["peak_demand"], errors="coerce").round(0)
        display["peak_gap"] = pd.to_numeric(display["peak_gap"], errors="coerce").round(0)
        display.columns = ["City", "Peak demand scenario (passengers/hour)", "Capacity-qualified gap (passengers/hour)", "Qualified options", "Exploratory options", "Lowest comparison-cost qualified option", "Total cost range", "Lead time", "Evidence"]
        display = display.sort_values(
            ["Capacity-qualified gap (passengers/hour)", "Peak demand scenario (passengers/hour)"],
            ascending=False,
            na_position="last",
        )
        st.dataframe(display, hide_index=True, width="stretch", height=415)
        callout("info", "Decision reading order", "Start with the physical gap, then compare cost, climate outcome, delivery time, and evidence status. No single opaque optimization selects the answer.")

    section_header("Qualified comparison examples", "Cards use the lowest lifecycle-comparison cost only as a transparent display rule. Review the full nondominated set before selecting an action.", "What")
    top = rows.sort_values(["peak_gap", "cost_base"], ascending=[False, True], na_position="last").head(3)
    columns = st.columns(max(1, len(top)))
    for column, (_, row) in zip(columns, top.iterrows()):
        body = (
            f"{row['rationale']} Peak gap: {_safe(row['peak_gap'], ' passengers/hour', 0)}. "
            f"Cost: {row['cost_range']}. Lead: {row['lead_time']}. Owner: {row['responsible_actor']}."
        )
        with column:
            st.markdown(priority_card(str(row["city"]), str(row["investment"]), body, str(row["evidence"])), unsafe_allow_html=True)

    with st.expander("Secondary index: Mobility Readiness Score (MRS)"):
        callout("info", "Use MRS for sensitivity, not investment selection", "MRS summarizes weighted evidence. It does not replace match-hour capacity, cost-effectiveness, or implementation constraints.")
        secondary = rows[["city", "mrs", "rankable"]].copy()
        secondary.columns = ["City", "MRS", "Rankable under selected profile"]
        secondary["MRS"] = pd.to_numeric(secondary["MRS"], errors="coerce").round(1)
        st.dataframe(secondary.sort_values("MRS", ascending=False, na_position="last"), hide_index=True, width="stretch")


def _legacy_demand_chart(visits: pd.DataFrame, city: str, demand_status: str) -> tuple[go.Figure | None, pd.DataFrame]:
    series = seasonal_baseline(visits, city)
    if series.empty:
        return None, series
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=series["date"], y=series["actual"], name="Rice commercial-mobility context", line=dict(color=SERIES_COLORS["observed"], width=1.2), opacity=.58))
    figure.add_trace(go.Scatter(x=series["date"], y=series["baseline"], name="Seasonal baseline", line=dict(color=SERIES_COLORS["baseline"], width=2.4)))
    band = scenario_band(visits, city)
    if not band.empty and {"date", "low", "high"}.issubset(band.columns):
        figure.add_trace(go.Scatter(x=band["date"], y=band["low"], line=dict(width=0), showlegend=False, hoverinfo="skip"))
        figure.add_trace(go.Scatter(x=band["date"], y=band["high"], name="Planning range", fill="tonexty", fillcolor=SERIES_COLORS["scenario_fill"], line=dict(color=SERIES_COLORS["scenario"], dash="dash")))
    figure.update_yaxes(title="Daily commercial visits proxy")
    return style_figure(figure, 390), series


def _hour_column(frame: pd.DataFrame) -> str | None:
    return next((key for key in ("timestamp_local", "timestamp", "hour", "time", "window_start", "datetime") if key in frame.columns), None)


def _movement_chart(movement: MovementView) -> tuple[go.Figure | None, pd.DataFrame]:
    frame = pd.DataFrame(movement.hourly_rows)
    hour = _hour_column(frame)
    if frame.empty or hour is None:
        return None, frame
    figure = go.Figure()
    for direction, color in (("arrivals", COLORS["blue"]), ("departures", COLORS["teal"])):
        base = next((column for column in (f"{direction}_base", direction, f"base_{direction}") if column in frame), None)
        low = next((column for column in (f"{direction}_low", f"low_{direction}") if column in frame), None)
        high = next((column for column in (f"{direction}_high", f"high_{direction}") if column in frame), None)
        if low and high:
            figure.add_trace(go.Scatter(x=frame[hour], y=frame[low], line=dict(width=0), hoverinfo="skip", showlegend=False))
            figure.add_trace(go.Scatter(x=frame[hour], y=frame[high], fill="tonexty", fillcolor="rgba(53,107,154,.10)" if direction == "arrivals" else "rgba(11,113,105,.10)", line=dict(width=0), name=f"{direction.title()} range"))
        if base:
            figure.add_trace(go.Scatter(x=frame[hour], y=frame[base], line=dict(color=color, width=2.5), name=f"{direction.title()} base"))
    figure.update_yaxes(title="Passengers per hour")
    return style_figure(figure, 390), frame


def _city_rows(value: Any, city: str) -> pd.DataFrame:
    if not isinstance(value, pd.DataFrame) or value.empty or "city" not in value:
        return pd.DataFrame()
    return value[value["city"] == city].copy()


def _rice_dataset_ledger(artifacts: Mapping[str, Any], city: str) -> pd.DataFrame:
    specifications = (
        ("store-visits-rice", "Commercial activity baseline and category mix", "visits"),
        ("daily-weather-rice", "Heat-index context and route heat", "weather"),
        ("urban-heat-index-rice", "Venue and walking-route heat context", "uhi"),
        ("core-poi-geometry-rice", "Venue-support places and spatial bins", "poi"),
        ("spend-patterns-rice", "Customer-home-state context", "origins"),
        ("daily-spend-brand-and-state-rice", "Non-causal economic sensitivity baseline", "brand_spend"),
    )
    rows = []
    for dataset, role, key in specifications:
        city_frame = _city_rows(artifacts.get(key), city)
        statuses = (
            sorted(set(city_frame["evidence_status"].dropna().astype(str)))
            if not city_frame.empty and "evidence_status" in city_frame
            else []
        )
        rows.append(
            {
                "Supplied Rice dataset": dataset,
                "Role in this city view": role,
                "Rows available": len(city_frame),
                "Evidence": ", ".join(statuses) if statuses else ("derived" if len(city_frame) else "unavailable"),
            }
        )
    return pd.DataFrame(rows)


def _render_rice_context(decision: CityDecisionView, artifacts: Mapping[str, Any]) -> None:
    section_header(
        "Supplied Rice data context",
        "All six provided datasets are visible here. Commercial activity and spend support context and sensitivity analysis; neither is stadium attendance nor causal event impact.",
        "Canonical data",
    )
    category = _city_rows(artifacts.get("visits_category"), decision.city)
    spend = economic_impact_range(
        artifacts.get("brand_spend", pd.DataFrame()),
        decision.city,
        event_days=max(len(decision.matches), 1),
    )
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        if not category.empty and {"category", "daily_visits"}.issubset(category):
            category["daily_visits"] = pd.to_numeric(category["daily_visits"], errors="coerce")
            mix = (
                category.groupby("category", as_index=False)["daily_visits"]
                .mean()
                .nlargest(10, "daily_visits")
                .sort_values("daily_visits")
            )
            figure = px.bar(
                mix,
                x="daily_visits",
                y="category",
                orientation="h",
                color_discrete_sequence=[COLORS["blue"]],
            )
            figure.update_xaxes(title="Average daily visits")
            figure.update_yaxes(title=None)
            st.plotly_chart(style_figure(figure, 360, legend=False), width="stretch", config={"displayModeBar": False})
            with st.expander("Table alternative: commercial activity by category"):
                st.dataframe(mix, hide_index=True, width="stretch")
        else:
            callout("warning", "Category activity unavailable", "Rebuild the Rice ETL to restore category-level commercial context.")
    with right:
        _metric_grid(
            [
                (
                    _money(spend.get("baseline_daily_spend")),
                    "Observed median daily spend",
                    "derived" if spend.get("baseline_daily_spend") is not None else "unavailable",
                    f"{spend.get('sample_size', 0)} daily observations",
                    "teal",
                ),
                (
                    _money_range(spend.get("low"), spend.get("high"), spend.get("base")),
                    "Event-day spend sensitivity",
                    str(spend.get("status", "unavailable")),
                    f"{len(decision.matches)} match days; explicit uplift range",
                    "amber",
                ),
            ]
        )
        callout(
            "info",
            "Economic context is not attributed impact",
            "The range applies explicit 2%/5%/10% uplift assumptions to observed brand/state spend. It is not a causal estimate or ticket-holder spend.",
        )
    with st.expander("How all six supplied datasets are used", icon=":material/database:"):
        st.dataframe(_rice_dataset_ledger(artifacts, decision.city), hide_index=True, width="stretch")


def _render_origin_context(decision: CityDecisionView, artifacts: Mapping[str, Any]) -> None:
    origins = artifacts.get("origins", pd.DataFrame())
    if not isinstance(origins, pd.DataFrame) or origins.empty or "city" not in origins:
        return
    origin_table = origins[origins["city"] == decision.city].sort_values("count", ascending=False).head(10)
    if origin_table.empty:
        return
    section_header("Customer-home context", "Descriptive Rice spending origins; not ticket-holder origins.", "Origins")
    figure = px.bar(
        origin_table.sort_values("count"),
        x="count",
        y="home_state",
        orientation="h",
        color_discrete_sequence=[COLORS["violet"]],
    )
    figure.update_xaxes(title="Observed Rice records")
    figure.update_yaxes(title=None)
    st.plotly_chart(style_figure(figure, 330, legend=False), width="stretch", config={"displayModeBar": False})
    with st.expander("Table alternative: customer-home states"):
        st.dataframe(_present_table(origin_table), hide_index=True, width="stretch")


def _coordinates(row: Mapping[str, Any]) -> tuple[float, float] | None:
    lat = row.get("lat", row.get("latitude", row.get("stop_lat")))
    lon = row.get("lon", row.get("longitude", row.get("stop_lon")))
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def _traffic_pressure_table(
    baseline: ScenarioView,
    selected: ScenarioView,
) -> pd.DataFrame:
    """Return the exact modeled venue-area vehicle-trip comparison."""

    baseline_base = baseline.venue_vehicle_trips_base
    rows = []
    compared_scenarios = [baseline] if selected.name == baseline.name else [baseline, selected]
    for scenario in compared_scenarios:
        change = None
        if scenario.venue_vehicle_trips_base is not None and baseline_base is not None:
            change = scenario.venue_vehicle_trips_base - baseline_base
        rows.append(
            {
                "Scenario": scenario.name,
                "Low input case": scenario.venue_vehicle_trips_low,
                "Base input case": scenario.venue_vehicle_trips_base,
                "High input case": scenario.venue_vehicle_trips_high,
                "Change from baseline": change,
                "Evidence": scenario.status,
            }
        )
    return pd.DataFrame(rows)


def _traffic_pressure_envelope(scenario: ScenarioView) -> str:
    """Format the actual min/max output across low, base, and high input cases."""

    values = [
        float(value)
        for value in (
            scenario.venue_vehicle_trips_low,
            scenario.venue_vehicle_trips_base,
            scenario.venue_vehicle_trips_high,
        )
        if value is not None and np.isfinite(float(value))
    ]
    if not values:
        return "Not available"
    return f"{min(values):,.0f} to {max(values):,.0f} trips across input cases"


def _add_traffic_pressure_layer(
    figure: go.Figure,
    decision: CityDecisionView,
    baseline: ScenarioView,
    selected: ScenarioView,
) -> dict[str, str]:
    """Add a venue-area pressure marker without implying road-segment congestion."""

    baseline_value = baseline.venue_vehicle_trips_base
    selected_value = selected.venue_vehicle_trips_base
    if decision.lat is None or decision.lon is None or baseline_value is None or selected_value is None:
        return {
            "Layer": "Modeled traffic pressure",
            "Status": "Unavailable",
            "Mapped records": "0",
            "Source records": "0",
            "Meaning": "Scenario vehicle-trip values are unavailable",
        }

    baseline_range = _traffic_pressure_envelope(baseline)
    selected_range = _traffic_pressure_envelope(selected)
    change = float(selected_value) - float(baseline_value)
    change_pct = change / float(baseline_value) if float(baseline_value) else 0.0
    color = COLORS["amber"] if selected.name == baseline.name else COLORS["teal"] if change <= 0 else COLORS["coral"]
    change_label = "Baseline" if selected.name == baseline.name else f"{change_pct:+.0%} trips"
    figure.add_trace(
        go.Scattermap(
            lat=[decision.lat],
            lon=[decision.lon],
            mode="markers+text",
            marker=dict(size=52, color=color, opacity=.78),
            name=f"{selected.name} traffic pressure",
            text=[change_label],
            textposition="top center",
            textfont=dict(size=13, color=COLORS["ink"]),
            customdata=[[baseline_range, selected_range, change]],
            hovertemplate=(
                "<b>Modeled venue-area vehicle trips</b>"
                "<br>Baseline cases: %{customdata[0]}"
                f"<br>{selected.name} cases: %{{customdata[1]}}"
                "<br>Base-case change: %{customdata[2]:+,.0f} trips<extra></extra>"
            ),
        )
    )
    return {
        "Layer": "Modeled traffic pressure",
        "Status": str(selected.status).title(),
        "Mapped records": "1",
        "Source records": "2",
        "Meaning": (
            f"{float(baseline_value):,.0f} baseline to {float(selected_value):,.0f} trips "
            f"({change:+,.0f}) under {selected.name}"
        ),
    }


def _layer_map(
    decision: CityDecisionView,
    artifacts: Mapping[str, Any],
    selected_layers: tuple[str, ...] | list[str] | None = None,
    traffic_baseline: ScenarioView | None = None,
    traffic_scenario: ScenarioView | None = None,
) -> tuple[go.Figure, pd.DataFrame]:
    figure = go.Figure()
    readiness: list[dict[str, str]] = []
    legend_entries: set[str] = set()
    layers = (
        ("traffic_pressure", "Modeled traffic pressure", COLORS["coral"]),
        ("gtfs", "GTFS stops", COLORS["blue"]),
        ("gtfs_routes", "Event-valid GTFS routes", COLORS["violet"]),
        ("walk", "Walking network", COLORS["teal"]),
        ("uhi", "Heat observations", COLORS["coral"]),
        ("poi", "Venue-support places", COLORS["amber"]),
        ("origin", "Origin flows", COLORS["violet"]),
    )
    enabled = set(selected_layers) if selected_layers is not None else {key for key, _, _ in layers}
    for key, label, color in layers:
        if key == "traffic_pressure":
            if key not in enabled:
                readiness.append({"Layer": label, "Status": "Hidden", "Mapped records": "0", "Source records": "2", "Meaning": "Available to enable on the map"})
            elif traffic_baseline is not None and traffic_scenario is not None:
                readiness.append(_add_traffic_pressure_layer(figure, decision, traffic_baseline, traffic_scenario))
            else:
                readiness.append({"Layer": label, "Status": "Unavailable", "Mapped records": "0", "Source records": "0", "Meaning": "Scenario vehicle-trip values are unavailable"})
            continue
        raw_rows = city_layer_records(artifacts, decision.city, key)
        if key not in enabled:
            readiness.append({"Layer": label, "Status": "Hidden", "Mapped records": "0", "Source records": str(len(raw_rows)), "Meaning": "Available to enable on the map"})
            continue
        points = [(record, coordinate) for record in raw_rows if (coordinate := _coordinates(record))]
        if points:
            legend_entries.add(f"{key}:{label}")
            figure.add_trace(
                go.Scattermap(
                    lat=[coordinate[0] for _, coordinate in points],
                    lon=[coordinate[1] for _, coordinate in points],
                    mode="markers",
                    marker=dict(size=7 if key != "uhi" else 9, color=color, opacity=.66),
                    name=label,
                    legendgroup=key,
                    text=[str(record.get("name") or record.get("category") or label) for record, _ in points],
                    hovertemplate="%{text}<extra></extra>",
                )
            )
        line_count = 0
        gtfs_latitudes: list[float | None] = []
        gtfs_longitudes: list[float | None] = []
        gtfs_hover: list[str | None] = []
        for record in raw_rows:
            coordinates = record.get("coordinates") or record.get("geometry")
            if isinstance(coordinates, list) and coordinates and isinstance(coordinates[0], (list, tuple)):
                pairs = [(float(pair[1]), float(pair[0])) for pair in coordinates if len(pair) >= 2]
                if pairs:
                    record_label = str(
                        record.get("name")
                        or record.get("route_name")
                        or record.get("route_id")
                        or (f"{record.get('minutes')}-minute isochrone" if record.get("minutes") else label)
                    )
                    legend_label = label if key in {"gtfs_routes", "walk"} else record_label
                    legend_key = f"{key}:{legend_label}"
                    show_legend = legend_key not in legend_entries
                    legend_entries.add(legend_key)
                    agency = str(record.get("agency") or "")
                    hover_label = f"{record_label} | {agency}" if agency else record_label
                    if key == "gtfs_routes":
                        gtfs_latitudes.extend([pair[0] for pair in pairs] + [None])
                        gtfs_longitudes.extend([pair[1] for pair in pairs] + [None])
                        gtfs_hover.extend([hover_label] * len(pairs) + [None])
                        line_count += 1
                        continue
                    figure.add_trace(
                        go.Scattermap(
                            lat=[pair[0] for pair in pairs],
                            lon=[pair[1] for pair in pairs],
                            mode="lines",
                            line=dict(color=color, width=3 if record.get("name") else 1.5),
                            name=legend_label,
                            legendgroup=key,
                            showlegend=show_legend,
                            text=[hover_label] * len(pairs),
                            hovertemplate="%{text}<extra></extra>",
                        )
                    )
                    line_count += 1
        if gtfs_latitudes:
            figure.add_trace(
                go.Scattermap(
                    lat=gtfs_latitudes,
                    lon=gtfs_longitudes,
                    mode="lines",
                    line=dict(color=color, width=1.5),
                    name=label,
                    legendgroup=key,
                    showlegend=True,
                    connectgaps=False,
                    text=gtfs_hover,
                    hovertemplate="%{text}<extra></extra>",
                )
            )
        available = len(points) + line_count
        source_total = max((int(record.get("source_total_records", 0) or 0) for record in raw_rows), default=len(raw_rows))
        readiness.append({"Layer": label, "Status": "Available" if available else "Unavailable", "Mapped records": str(available), "Source records": str(max(source_total, len(raw_rows))), "Meaning": "Planning context; not an audited accessibility finding" if key == "walk" else "Evidence layer"})
    if decision.lat is not None and decision.lon is not None:
        figure.add_trace(go.Scattermap(lat=[decision.lat], lon=[decision.lon], mode="markers", marker=dict(size=20, color=COLORS["ink"]), name="Venue", text=[decision.venue], hovertemplate="%{text}<extra></extra>"))
    return style_map(figure, 465, zoom=11, lat=decision.lat or 38.5, lon=decision.lon or -96), pd.DataFrame(readiness)


def _composite_scope(package: Mapping[str, Any]) -> str:
    fields = (
        ("shuttle_buses_per_hour", "shuttle buses/hour"),
        ("added_transit_departures_per_hour", "added transit departures/hour"),
        ("park_ride_spaces", "park-and-ride spaces"),
        ("park_ride_feeder_departures_per_hour", "feeder departures/hour"),
        ("bike_hub_spaces", "bike and micromobility spaces"),
        ("cooled_walkway_km", "km cooled corridor"),
        ("arrival_spreading_pct", "peak arrivals shifted"),
    )
    parts = []
    for field, label in fields:
        value = package.get(field)
        if value is not None and float(value) > 0:
            prefix = f"{float(value):g}%" if field == "arrival_spreading_pct" else f"{float(value):g}"
            parts.append(f"{prefix} {label}")
    return "; ".join(parts) if parts else "No intervention (baseline)"


def _scenario_table(scenarios: tuple[ScenarioView, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Scenario": item.name,
                "What it combines": _composite_scope(item.package),
                "Evidence": item.status,
                "Gap resolved (passengers)": item.gap_resolved_passengers,
                "Vehicle trips (base)": item.venue_vehicle_trips_base,
                "Net VMT (base)": item.net_vmt_base,
                "Net CO2e avoided (kg, base)": item.net_co2e_kg_base,
                "Heat person-hours avoided": item.heat_exposure_person_hours_avoided,
                "Cost low": item.cost_low,
                "Cost base": item.cost_base,
                "Cost high": item.cost_high,
                "Capital cost base": item.capital_cost_base,
                "Operating cost base": item.operating_cost_base,
                "Effective arrival shift (pph)": item.arrival_shifted_pph_base,
                "Cost per passenger": item.cost_per_passenger,
                "Lead time": item.lead_time_band,
                "Basis": item.basis,
            }
            for item in scenarios
        ]
    )


def _implementation_readiness(
    recommendations: tuple[RecommendationView, ...],
    access: AccessView,
) -> pd.DataFrame:
    rows = []
    for item in recommendations:
        dependencies = list(item.dependencies)
        local_gate = []
        if not access.capacity_qualified:
            local_gate.append("event-window capacity evidence")
        if item.intervention in {"Bike and micromobility hubs", "Cooled walking corridors"} and access.walking_status != "derived":
            local_gate.append("field-verified walking connection")
        if "service" in item.intervention.lower() or "transit" in item.intervention.lower():
            local_gate.append("fleet, operator, and timetable confirmation")
        rows.append(
            {
                "Intervention": item.intervention,
                "Candidate owner": item.responsible_actor,
                "Lead-time band": item.lead_time_band,
                "Planning cost": _money_range(item.cost_low, item.cost_high, item.cost_base),
                "Comparison cost basis": item.cost_basis,
                "Dependencies": "; ".join(dependencies) or "Implementation plan",
                "Local confirmation before commitment": "; ".join(dict.fromkeys(local_gate)) or "Agency budget and operating approval",
                "Screening status": item.status,
                "Evidence-qualified": item.evidence_qualified,
                "Evidence quality": item.evidence_quality,
                "Evidence reason": item.evidence_reason,
            }
        )
    return pd.DataFrame(rows)


def _before_after(movement: MovementView, scenario: ScenarioView) -> pd.DataFrame:
    frame = pd.DataFrame(movement.hourly_rows)
    hour = _hour_column(frame)
    arrivals = next((column for column in ("arrivals_base", "arrivals", "base_arrivals") if column in frame), None)
    if frame.empty or hour is None or arrivals is None:
        return pd.DataFrame()
    values = pd.to_numeric(frame[arrivals], errors="coerce").fillna(0).to_numpy(dtype=float)
    after = values.copy()
    shifted_pph = float(scenario.arrival_shifted_pph_base or 0)
    if len(after) >= 3 and shifted_pph > 0 and after.sum() > 0:
        peak = int(np.argmax(after))
        movable = min(after[peak], shifted_pph)
        neighbors = [index for index in (peak - 1, peak + 1) if 0 <= index < len(after)]
        after[peak] -= movable
        for index in neighbors:
            after[index] += movable / len(neighbors)
    return pd.DataFrame({"Time": frame[hour], "Before": values, "After": after})


def render_explorer(metrics: pd.DataFrame, artifacts: dict[str, Any], selected_city: str, weights: dict[str, float], include_estimates: bool) -> None:
    presentation = build_presentation(metrics, artifacts)
    decision = presentation.city(selected_city)
    match_options = {item.match_id: item.label for item in decision.matches}
    selected_match_id = st.selectbox("Match", list(match_options), format_func=match_options.get, key=f"match_selector_{decision.city}")
    match = decision.match(selected_match_id)
    movement = decision.movement(match.match_id)
    access = decision.access(match.match_id)
    scenarios = decision.scenario_set(match.match_id)
    baseline_scenario = next((item for item in scenarios if item.name == "Baseline"), ScenarioView(name="Baseline"))
    recommendations = decision.recommendation_set(match.match_id)
    qualified_count = sum(item.evidence_qualified for item in recommendations)
    exploratory_count = len(recommendations) - qualified_count

    page_header(
        "Scenario explorer",
        f"{decision.city} / {match.venue}",
        "Explore one match at a time: hourly movement, route-ready evidence layers, intervention tradeoffs, and the assumptions behind each value.",
        (match.stage, match.kickoff_local or "Schedule evidence unavailable", f"Capacity {_safe(match.capacity, '', 0)}"),
    )
    if include_estimates:
        callout("warning", "Estimated evidence is enabled", "Estimated values remain labeled and appear only because the sidebar sensitivity option is active.")
    if match.status == "unavailable":
        callout("warning", "Official match record unavailable", "The compatibility portfolio view remains usable, but match-hour conclusions are withheld until a pinned schedule record is supplied.")

    _metric_grid(
        [
            (_safe(access.residual_passengers if access.capacity_qualified else None, " pph", 0), "Peak access gap", access.transit_status, "Passengers per hour", "coral"),
            (_safe(access.peak_demand_per_hour, " pph", 0), "Peak movement demand", movement.status, movement.uncertainty_type, "blue"),
            (_number_range(access.transit_capacity_low, access.transit_capacity_high, access.transit_capacity_base, " pph") if access.capacity_qualified else "Not qualified", "Scheduled transit capacity", access.transit_status, "Planning capacity range", "teal"),
            (f"{qualified_count} + {exploratory_count}", "Qualified + exploratory options", "scenario" if qualified_count else "partial", "No automatic winner", "amber"),
        ]
    )
    if access.capacity_qualified and float(access.transit_capacity_high or 0) == 0:
        callout(
            "warning",
            "Observed scheduled-service zero near the venue",
            "The pinned event-date GTFS feed contains no scheduled departures within the half-mile capacity catchment. This is treated as a severe first/last-mile gap, not missing data; special-event service not published in GTFS remains unmeasured.",
        )

    scenario_names = [item.name for item in scenarios]
    scenario_focus_key = f"scenario_focus_{decision.city}_{match.match_id}"

    def _focused_scenario() -> ScenarioView:
        selected_name = st.session_state.get(scenario_focus_key, "Operational Package")
        return next((item for item in scenarios if item.name == selected_name), scenarios[0])

    def _render_movement() -> None:
        section_header("Match-hour demand timeline", "Hourly low, base, and high arrivals and departures.", "Movement")
        figure, movement_table = _movement_chart(movement)
        if figure is not None:
            st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
            with st.expander("Table alternative: match-hour movement"):
                st.dataframe(movement_table, hide_index=True, width="stretch")
        else:
            callout("warning", "Match-hour movement unavailable", "No contract 0.3 hourly rows are available for this match. The chart below is commercial-mobility context, not fan movement.")
            legacy_figure, legacy_table = _legacy_demand_chart(artifacts.get("visits", pd.DataFrame()), decision.city, str(decision.metric.get("demand_status", "unavailable")))
            if legacy_figure is not None:
                st.plotly_chart(legacy_figure, width="stretch", config={"displayModeBar": False})
                with st.expander("Table alternative: commercial-mobility baseline"):
                    st.dataframe(legacy_table, hide_index=True, width="stretch")
            else:
                callout("info", "Commercial activity artifact unavailable", "Run the offline Rice ETL to restore historical city context.")
        st.caption("Rice store visits describe commercial activity. They are not stadium attendance or ticket-holder behavior.")

    def _render_map() -> None:
        section_header("Venue access evidence", "Compare traffic pressure, service, walking, heat, venue-support, and origin layers.", "Place")
        default_traffic_scenario = "Operational Package" if "Operational Package" in scenario_names else scenario_names[0]
        traffic_scenario_name = st.segmented_control(
            "Traffic scenario",
            scenario_names,
            default=default_traffic_scenario,
            key=f"traffic_scenario_{decision.city}_{match.match_id}",
        ) or default_traffic_scenario
        traffic_scenario = next(item for item in scenarios if item.name == traffic_scenario_name)
        if baseline_scenario.venue_vehicle_trips_base is not None and traffic_scenario.venue_vehicle_trips_base is not None:
            traffic_change = traffic_scenario.venue_vehicle_trips_base - baseline_scenario.venue_vehicle_trips_base
            traffic_change_pct = (
                traffic_change / baseline_scenario.venue_vehicle_trips_base
                if baseline_scenario.venue_vehicle_trips_base
                else 0.0
            )
            _metric_grid(
                [
                    (
                        _safe(baseline_scenario.venue_vehicle_trips_base, " trips", 0),
                        "Baseline vehicle pressure",
                        baseline_scenario.status,
                        _traffic_pressure_envelope(baseline_scenario),
                        "amber",
                    ),
                    (
                        _safe(traffic_scenario.venue_vehicle_trips_base, " trips", 0),
                        f"{traffic_scenario.name} pressure",
                        traffic_scenario.status,
                        _traffic_pressure_envelope(traffic_scenario),
                        "teal" if traffic_change <= 0 else "coral",
                    ),
                    (
                        f"{traffic_change:+,.0f} trips ({traffic_change_pct:+.1%})",
                        "Change from baseline",
                        traffic_scenario.status,
                        "Base input case",
                        "teal" if traffic_change <= 0 else "coral",
                    ),
                ]
            )
        layer_options = {
            "traffic_pressure": "Traffic pressure",
            "gtfs": "GTFS stops",
            "gtfs_routes": "GTFS routes",
            "walk": "Walking access",
            "uhi": "Heat context",
            "poi": "Venue support",
            "origin": "Customer origins",
        }
        selected_layers = st.multiselect(
            "Map layers",
            list(layer_options),
            default=["traffic_pressure", "gtfs", "gtfs_routes", "walk", "uhi"],
            format_func=layer_options.get,
            key=f"map_layers_{decision.city}_{match.match_id}",
        )
        layer_figure, layer_table = _layer_map(
            decision,
            artifacts,
            selected_layers,
            traffic_baseline=baseline_scenario,
            traffic_scenario=traffic_scenario,
        )
        layer_scope = "none" if not selected_layers else "__".join(sorted(selected_layers))
        st.plotly_chart(
            layer_figure,
            width="stretch",
            config={"displayModeBar": False},
            key=f"venue_map_{decision.city}_{match.match_id}_{traffic_scenario.name}_{layer_scope}",
        )
        traffic_table = _traffic_pressure_table(baseline_scenario, traffic_scenario)
        with st.expander("Table alternative: modeled traffic pressure"):
            st.dataframe(traffic_table, hide_index=True, width="stretch")
        unavailable = layer_table[layer_table["Status"] == "Unavailable"]["Layer"].tolist()
        if unavailable:
            callout("warning", "Some map layers are unavailable", f"No displayable records for: {', '.join(unavailable)}. Aggregate evidence may still appear below, but no geometry is inferred.")
        with st.expander("Map-layer readiness", icon=":material/layers:"):
            st.dataframe(_present_table(layer_table), hide_index=True, width="stretch")

    def _render_scenarios() -> None:
        section_header(
            "Composite scenario sensitivity",
            "These multi-measure bundles stress-test the model; they are not investment recommendations.",
            "Advanced",
        )
        selected_name = st.segmented_control(
            "Focus composite scenario",
            scenario_names,
            default="Operational Package",
            key=scenario_focus_key,
        ) or "Operational Package"
        selected = next((item for item in scenarios if item.name == selected_name), scenarios[0])
        st.caption(f"Selected composite: {_composite_scope(selected.package)}")
        _metric_grid(
            [
                (_safe(selected.gap_resolved_passengers, " passengers", 0), "Gap resolved", selected.status, selected.basis, "teal"),
                (_money_range(selected.cost_low, selected.cost_high, selected.cost_base), "Planning cost", selected.status, selected.lead_time_band, "amber"),
                (_number_range(selected.net_co2e_kg_low, selected.net_co2e_kg_high, selected.net_co2e_kg_base, " kg"), "Net CO2e avoided", selected.status, "Negative values indicate an increase", "blue"),
                (_safe(selected.cost_per_passenger, " / passenger", 0), "Total cost / gap passenger", selected.status, "Named-package ratio; recommendation comparison uses reusable-event costs", "violet"),
            ]
        )
        comparison = _scenario_table(scenarios)
        chart = comparison.dropna(subset=["Cost base", "Gap resolved (passengers)"])
        if not chart.empty:
            chart = chart.copy()
            chart["Climate magnitude"] = pd.to_numeric(chart["Net CO2e avoided (kg, base)"], errors="coerce").abs().fillna(0) + 1
            tradeoff = px.scatter(chart, x="Cost base", y="Gap resolved (passengers)", color="Scenario", text="Scenario", size="Climate magnitude", size_max=28, hover_data={"Net CO2e avoided (kg, base)": True, "Climate magnitude": False}, color_discrete_map={"Baseline": COLORS["slate"], "Operational Package": COLORS["teal"], "Capital Package": COLORS["blue"]})
            tradeoff.update_traces(textposition="top center")
            tradeoff.update_xaxes(tickprefix="$", title="Planning cost")
            st.plotly_chart(style_figure(tradeoff, 390), width="stretch", config={"displayModeBar": False})
        else:
            callout("info", "Cost-effectiveness chart unavailable", "Package cost and passenger-benefit evidence have not both been supplied.")
        with st.expander("Exact scenario comparison", icon=":material/table_chart:"):
            st.dataframe(_present_table(comparison), hide_index=True, width="stretch")

        section_header("Concrete investment options", "Compare defined single measures, their scale, cost basis, and evidence gate.", "Investments")
        pareto_table = pd.DataFrame(
            [
                {
                    "Intervention": item.intervention,
                    "Proposed scale": item.scope,
                    "Decision class": "Evidence-qualified screening" if item.evidence_qualified else "Exploratory sensitivity",
                    "Gap resolved": item.gap_resolved_passengers,
                    "Comparison cost": item.comparison_cost_base,
                    "Comparison cost per passenger": item.cost_per_passenger,
                    "Total project/event cost": item.cost_base,
                    "Cost basis": item.cost_basis,
                    "Net CO2e avoided (kg)": item.net_co2e_kg,
                    "Heat person-hours avoided": item.heat_person_hours_avoided,
                    "Lead time": item.lead_time_band,
                    "Evidence quality": item.evidence_quality,
                    "Evidence-qualified": item.evidence_qualified,
                    "Responsible actor": item.responsible_actor,
                    "Why retained / limitation": item.rationale,
                }
                for item in recommendations
            ]
        )
        if pareto_table.empty:
            callout("warning", "Pareto set unavailable", "Validated factors and intervention outputs are required before prioritization.")
        else:
            summary_columns = [
                "Intervention",
                "Proposed scale",
                "Decision class",
                "Gap resolved",
                "Comparison cost per passenger",
                "Net CO2e avoided (kg)",
                "Lead time",
                "Evidence quality",
            ]
            st.dataframe(
                _present_table(pareto_table[summary_columns]),
                hide_index=True,
                width="stretch",
                column_config={
                    "Gap resolved": st.column_config.NumberColumn(format="%,.0f"),
                    "Comparison cost per passenger": st.column_config.NumberColumn(format="$%,.0f"),
                    "Net CO2e avoided (kg)": st.column_config.NumberColumn(format="%,.0f"),
                },
            )
            with st.expander("Cost basis and evidence details", icon=":material/fact_check:"):
                st.dataframe(_present_table(pareto_table), hide_index=True, width="stretch")

        section_header(
            "Implementation readiness",
            "Review owner, lead time, dependencies, and required local confirmation.",
            "Delivery",
        )
        readiness = _implementation_readiness(recommendations, access)
        if readiness.empty:
            callout("warning", "Implementation record unavailable", "A match-scoped Pareto option is required before delivery planning can begin.")
        else:
            with st.expander("Delivery owners, dependencies, and confirmation needs", icon=":material/assignment:"):
                st.dataframe(_present_table(readiness), hide_index=True, width="stretch")
            callout(
                "warning",
                "Planning readiness is not agency approval",
                "Fleet, labor, right-of-way, procurement, operating plans, and local budgets must be confirmed by the named actors.",
            )

        section_header("Before and after by hour", "Arrival spreading moves demand from the peak to adjacent hours.", "Time")
        timeline = _before_after(movement, selected)
        if timeline.empty:
            callout("info", "Hourly before/after unavailable", "Provide contract 0.3 movement rows to compare the package timing assumption by hour.")
        else:
            long = timeline.melt("Time", var_name="State", value_name="Passengers per hour")
            timeline_figure = px.line(long, x="Time", y="Passengers per hour", color="State", markers=True, color_discrete_map={"Before": COLORS["coral"], "After": COLORS["teal"]})
            st.plotly_chart(style_figure(timeline_figure, 355), width="stretch", config={"displayModeBar": False})
            with st.expander("Table alternative: before and after"):
                st.dataframe(timeline, hide_index=True, width="stretch")

        exact_json = presentation.scenario_json(decision.city, match.match_id)
        st.download_button("Download exact scenario JSON", exact_json, file_name=f"{decision.city.lower().replace(' ', '-')}-{match.match_id.lower()}-scenarios.json", mime="application/json", key=f"scenario_download_{decision.city}_{match.match_id}", width="stretch")

    def _render_evidence() -> None:
        section_header("Decision evidence ledger", "Every headline value retains a written status, source, and limitation.", "Audit")
        evidence = [
            ("Official match", match.status, "Pinned FIFA schedule supplement"),
            ("Movement scenario", movement.status, movement.uncertainty_type),
            ("Transit capacity gap", access.transit_status, "Event-window scheduled service + planning vehicle capacity"),
            ("Walking route", access.walking_status, "OSM network path to an event-relevant stop"),
            ("Route heat", access.heat_status, "Rice weather/UHI along an eligible path"),
            ("Transit", str(decision.metric.get("transit_status", "unavailable")), GTFS_SOURCE),
            ("Heat", str(decision.metric.get("heat_status", "unavailable")), rice_source("daily-weather-rice", "event-window heat")),
            ("Urban heat", str(decision.metric.get("uhi_status", "unavailable")), rice_source("urban-heat-index-rice", "venue context")),
            ("Venue support", str(decision.metric.get("access_status", "unavailable")), rice_source("core-poi-geometry-rice", "venue buffer")),
        ]
        st.markdown(f"<div class='evidence-list'>{''.join(evidence_row(*item) for item in evidence)}</div>", unsafe_allow_html=True)
        selected = _focused_scenario()
        assumptions = [*movement.assumptions, *access.assumptions, *selected.assumptions]
        with st.expander("Assumptions used for this selection", icon=":material/variables:"):
            if assumptions:
                st.dataframe(pd.DataFrame({"Assumption": list(dict.fromkeys(assumptions))}), hide_index=True, width="stretch")
            else:
                callout("info", "No assumptions supplied", "Upstream contract results should include an explicit assumption register before release.")
        _render_rice_context(decision, artifacts)
        _render_origin_context(decision, artifacts)

    movement_tab, map_tab, scenario_tab, evidence_tab = st.tabs(
        ["Movement", "Map & layers", "Scenarios", "Evidence"],
        key="explorer_section",
        on_change="rerun",
    )
    if movement_tab.open:
        with movement_tab:
            _render_movement()
    if map_tab.open:
        with map_tab:
            _render_map()
    if scenario_tab.open:
        with scenario_tab:
            _render_scenarios()
    if evidence_tab.open:
        with evidence_tab:
            _render_evidence()


def _coverage_heatmap(metrics: pd.DataFrame) -> go.Figure:
    dimensions = {"Transit": "transit_status", "Heat": "heat_status", "Urban heat": "uhi_status", "Venue support": "access_status"}
    status_order = ["unavailable", "partial", "estimated", "scenario", "derived", "observed"]
    colorscale, mapping = discrete_status_scale(status_order)
    available_columns = [column for column in dimensions.values() if column in metrics]
    status_matrix = metrics[available_columns].map(lambda value: value if value in mapping else "unavailable")
    labels = [label for label, column in dimensions.items() if column in available_columns]
    figure = go.Figure(go.Heatmap(z=status_matrix.map(mapping.get).to_numpy(), x=labels, y=metrics["city"], text=status_matrix.map(lambda value: str(value).upper()).to_numpy(), customdata=status_matrix.to_numpy(), texttemplate="%{text}", textfont=dict(color="#ffffff", size=10), colorscale=colorscale, zmin=0, zmax=len(status_order) - 1, showscale=False, xgap=4, ygap=4, hovertemplate="%{y}<br>%{x}: %{customdata}<extra></extra>"))
    figure.update_xaxes(side="top")
    figure.update_yaxes(autorange="reversed")
    return style_figure(figure, max(390, 35 * len(metrics)), legend=False, margin=dict(l=105, r=20, t=55, b=20))


def _legacy_source_rows(manifest: Mapping[str, Any]) -> pd.DataFrame:
    datasets = manifest.get("datasets", []) if isinstance(manifest, Mapping) else []
    return pd.DataFrame(datasets)


def _compact_columns(frame: pd.DataFrame, preferred: tuple[str, ...], limit: int = 8) -> list[str]:
    selected = [column for column in preferred if column in frame]
    return selected or list(frame.columns[:limit])


def _present_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Round numeric detail and humanize technical headers for on-screen tables."""

    display = frame.copy()
    numeric_columns = display.select_dtypes(include=[np.number]).columns
    if len(numeric_columns):
        display[numeric_columns] = display[numeric_columns].round(2)
    rename = {}
    for column in display.columns:
        label = str(column)
        if "_" in label or "." in label:
            humanized = label.replace("_", " ").replace(".", " · ")
            rename[column] = humanized[:1].upper() + humanized[1:]
    return display.rename(columns=rename)


def render_methods(metrics: pd.DataFrame, artifacts: dict[str, Any]) -> None:
    presentation = build_presentation(metrics, artifacts)
    manifest = artifacts.get("manifest", {})
    page_header(
        "Methods and quality assurance",
        "Audit every transportation claim",
        "Inspect source hashes, factor ranges, network coverage, validation, and index sensitivity before using a scenario in a public decision.",
        (f"{RICE_COLLECTION} canonical", "Public supplements pinned", "Exact exports"),
    )
    if not isinstance(manifest, Mapping) or manifest.get("status") == "unavailable":
        callout("error", "Versioned manifest unavailable", "Compatibility data can render, but release claims require pipeline-generated source hashes and coverage.")
    elif artifacts.get("legacy_mode"):
        callout("warning", "Compatibility mode", "Run the offline pipelines to restore versioned public supplements and complete quality evidence.")
    else:
        callout("success", "Versioned Rice artifacts loaded", f"Manifest generated {manifest.get('generated_at_utc', 'at an unknown time')}.")

    def _render_sources() -> None:
        section_header("Evidence eligibility by city", "Text appears inside every status cell; the table is the accessible equivalent.", "Coverage")
        st.plotly_chart(_coverage_heatmap(metrics), width="stretch", config={"displayModeBar": False})
        coverage_columns = [column for column in ("city", "transit_status", "heat_status", "uhi_status", "access_status", "data_coverage") if column in metrics]
        with st.expander("Accessible coverage table", icon=":material/table_chart:"):
            st.dataframe(_present_table(metrics[coverage_columns]), hide_index=True, width="stretch")
        section_header("Source registry", "URLs, publishers, versions, retrieval times, licenses, coverage, and SHA-256 values must come from deterministic pipelines.", "Provenance")
        source_table = pd.DataFrame(presentation.source_rows)
        if source_table.empty:
            source_table = _legacy_source_rows(manifest)
        if source_table.empty:
            callout("warning", "Source registry unavailable", "No contract source references or manifest datasets were provided.")
        else:
            source_columns = _compact_columns(
                source_table,
                ("source_id", "source", "publisher", "status", "coverage_start", "coverage_end", "retrieved_at", "license", "sha256"),
            )
            with st.expander("Source records and hashes", icon=":material/fingerprint:"):
                st.dataframe(_present_table(source_table[source_columns]), hide_index=True, width="stretch")
            st.caption("Complete source records and hashes are available in the manifest download.")
            hash_columns = [column for column in source_table if "sha" in column.lower() or "hash" in column.lower()]
            if not hash_columns:
                callout("warning", "Public source hashes missing", "Release evidence must include a content hash for each pinned supplement.")
        section_header(
            "Observed operational benchmarks",
            "Official post-event aggregates are displayed separately from match-hour scenarios. Every row states what it can and cannot calibrate.",
            "Post-event evidence",
        )
        operational = pd.DataFrame(presentation.operational_rows)
        coverage = pd.DataFrame(presentation.operational_coverage_rows)
        if operational.empty:
            callout(
                "warning",
                "Operational benchmarks unavailable",
                "Published agency outcomes have not been loaded; scenario assumptions remain unvalidated by post-event operations.",
            )
        else:
            source_lookup = {
                str(row.get("source_id")): row
                for row in presentation.source_rows
                if row.get("source_id")
            }
            operational["source"] = operational["source_id"].map(
                lambda source_id: source_lookup.get(str(source_id), {}).get("source", source_id)
            )
            operational["source_url"] = operational["source_id"].map(
                lambda source_id: source_lookup.get(str(source_id), {}).get("url")
            )
            operational["not_suitable_for"] = operational["not_suitable_for"].map(
                lambda values: "; ".join(str(value) for value in values) if isinstance(values, list) else values
            )
            compact_operational_columns = [column for column in ("city", "metric", "value", "unit", "status", "granularity", "source") if column in operational]
            city_count = int(operational["city"].nunique()) if "city" in operational else 0
            source_count = int(operational["source_id"].nunique()) if "source_id" in operational else 0
            _metric_grid(
                [
                    (f"{len(operational):,}", "Published benchmark rows", "observed", "Post-event aggregate records", "teal"),
                    (f"{city_count:,}", "Cities represented", "observed", "Coverage varies by metric", "blue"),
                    (f"{source_count:,}", "Pinned benchmark sources", "observed", "See source registry", "amber"),
                ]
            )
            with st.expander("Operational benchmark records", icon=":material/table_chart:"):
                st.dataframe(_present_table(operational[compact_operational_columns]), hide_index=True, width="stretch")
            event_records = pd.json_normalize(list(presentation.operational_event_rows), sep=".")
            if not event_records.empty:
                event_columns = _compact_columns(
                    event_records,
                    ("city", "event_id", "event_date", "venue", "attendance", "transit_ridership", "mode_share", "source_id"),
                )
                with st.expander("Match-level operating records", icon=":material/event:"):
                    st.dataframe(_present_table(event_records[event_columns]), hide_index=True, width="stretch")
                st.caption("The methods download retains every reported event field.")
            callout(
                "info",
                "Aggregate evidence does not qualify match-hour calibration",
                "No published row supplies complete 15-minute arrivals, mode share, transit loads, curb throughput, parking, and roadway observations for a match.",
            )
        if not coverage.empty:
            coverage["open_request_fields"] = coverage["open_request_fields"].map(
                lambda values: "; ".join(str(value) for value in values) if isinstance(values, list) else values
            )
            coverage["source_ids"] = coverage["source_ids"].map(
                lambda values: "; ".join(str(value) for value in values) if isinstance(values, list) else values
            )
            with st.expander("Operational evidence gaps and open requests", icon=":material/checklist:"):
                st.dataframe(_present_table(coverage), hide_index=True, width="stretch")

    def _render_factors() -> None:
        section_header("Planning factor registry", "Low, base, and high cost, vehicle-capacity, VMT, and emissions factors retain their publisher and version.", "Factors")
        factor_table = pd.DataFrame(presentation.factor_rows)
        if factor_table.empty:
            callout("warning", "Factor registry unavailable", "Do not interpret cost or climate outputs as implementation estimates until cited factor ranges are supplied.")
        else:
            with st.expander("Planning factor ranges", icon=":material/tune:"):
                st.dataframe(_present_table(factor_table), hide_index=True, width="stretch")
        section_header(
            "Equation registry",
            "Stable equation IDs connect model code, reviewer documentation, and exported scenario records.",
            "Equations",
        )
        equation_table = pd.DataFrame(presentation.equation_rows)
        if equation_table.empty:
            callout("error", "Equation registry unavailable", "Do not present modeled outcomes until their equations and evidence limits are registered.")
        else:
            with st.expander("Equation definitions", icon=":material/function:"):
                st.dataframe(_present_table(equation_table), hide_index=True, width="stretch")
        section_header(
            "Recommendation policy registry",
            "Evidence gates, cost treatment, owners, dependencies, and lead times are configuration—not hidden UI behavior.",
            "Policy",
        )
        policy_table = pd.DataFrame(presentation.policy_rows)
        if policy_table.empty:
            callout("error", "Recommendation policy unavailable", "Options cannot be described as decision-ready without an explicit evidence and cost policy.")
        else:
            with st.expander("Recommendation policies", icon=":material/policy:"):
                st.dataframe(_present_table(policy_table), hide_index=True, width="stretch")
        heuristic_table = pd.DataFrame(artifacts.get("city_intervention_inputs", []))
        if not heuristic_table.empty:
            section_header("City and match scenario heuristics", "Private-mode share, occupancy, trip distance, and active-mode distance inputs remain editable planning assumptions—not observed fan behavior.", "Assumptions")
            heuristic_columns = _compact_columns(
                heuristic_table,
                ("city", "match_id", "private_vehicle_share", "average_vehicle_occupancy", "average_trip_km_round_trip", "active_mode_max_distance_km", "status"),
            )
            with st.expander("Scenario assumptions by city and match", icon=":material/variables:"):
                st.dataframe(_present_table(heuristic_table[heuristic_columns]), hide_index=True, width="stretch")
        section_header("Walking-network coverage", "Coverage reports geometry, detour, crossings, sidewalks, and tag completeness without implying audited accessibility.", "Network")
        network_table = pd.DataFrame(presentation.network_rows)
        if network_table.empty:
            callout("warning", "Network coverage unavailable", "The venue map will show route-ready geometry only after pinned walking extracts are supplied.")
        else:
            network_columns = _compact_columns(
                network_table,
                ("city", "status", "network_distance_m", "straight_line_distance_m", "detour_ratio", "sidewalk_tag_coverage_pct", "crossing_tag_coverage_pct", "accessibility_status"),
            )
            with st.expander("Walking-network coverage details", icon=":material/directions_walk:"):
                st.dataframe(_present_table(network_table[network_columns]), hide_index=True, width="stretch")
        gtfs_rows = []
        for city, value in sorted(artifacts.get("gtfs", {}).items() if isinstance(artifacts.get("gtfs", {}), Mapping) else []):
            feeds = value.get("feeds", []) if isinstance(value, Mapping) else []
            if not feeds:
                feeds = [{}]
            for feed in feeds:
                gtfs_rows.append(
                    {
                        "City": city,
                        "Agency": feed.get("agency", "Agency unavailable"),
                        "Feed status": feed.get("status", value.get("feed_status", "unavailable")),
                        "Archive provider": feed.get("archive_provider") or "Publisher URL with enforced hash",
                        "Valid from": feed.get("valid_from"),
                        "Valid to": feed.get("valid_to"),
                        "Assigned matches": len(feed.get("assigned_match_ids", [])),
                        "Event-valid matches": len(feed.get("event_valid_match_ids", [])),
                        "SHA-256": feed.get("sha256"),
                        "Publisher URL": feed.get("publisher_url") or feed.get("url"),
                    }
                )
        if gtfs_rows:
            with st.expander("Pinned transit feeds", icon=":material/train:"):
                st.dataframe(_present_table(pd.DataFrame(gtfs_rows)), hide_index=True, width="stretch")

    def _render_validation() -> None:
        section_header("Movement validation", "Rolling holdouts are compared with a seasonal-naive baseline. Failure keeps the user-facing label at planning scenario.", "Backtest")
        validation = pd.DataFrame(presentation.validation_rows)
        if validation.empty:
            validation = validation_metrics(artifacts.get("visits", pd.DataFrame()))
        if validation.empty:
            callout("warning", "Validation unavailable", "Movement outputs remain planning scenarios.")
        else:
            comparator_column = next((column for column in ("outperforms_seasonal_naive", "beats_seasonal_naive") if column in validation), None)
            wins = int(validation[comparator_column].fillna(False).sum()) if comparator_column else 0
            _metric_grid(
                [
                    (f"{len(validation):,}", "Holdout rows", "derived", "Rolling comparisons", "blue"),
                    (f"{wins:,} / {len(validation):,}", "Rows beating seasonal naive", "derived", "Does not validate match behavior", "teal" if wins == len(validation) else "amber"),
                ]
            )
            with st.expander("Validation rows", icon=":material/table_chart:"):
                st.dataframe(_present_table(validation), hide_index=True, width="stretch")
            if comparator_column and bool(validation[comparator_column].all()):
                callout("success", "Reported holdouts clear the comparator", "The displayed validation rows all outperform their seasonal-naive comparator.")
            else:
                callout("warning", "Use planning-scenario language", "The supplied validation does not consistently clear the comparator.")
        callout("info", "Not measured", "The platform does not report stadium attendance, observed mode shift, causal economic impact, audited pedestrian access, or roadway performance.")

    def _render_sensitivity() -> None:
        section_header("Readiness rank sensitivity", "Compare how policy weights change scores and ranks before citing the index.", "Index")
        sensitivity = pd.DataFrame(presentation.sensitivity_rows)
        if sensitivity.empty:
            callout("warning", "Sensitivity unavailable", "No named-profile sensitivity rows were provided or derivable.")
        else:
            rankable = sensitivity.dropna(subset=["Rank"]) if "Rank" in sensitivity else pd.DataFrame()
            if not rankable.empty:
                rank_figure = px.line(rankable, x="Profile", y="Rank", color="City", markers=True)
                rank_figure.update_yaxes(autorange="reversed", dtick=1)
                st.plotly_chart(style_figure(rank_figure, 410), width="stretch", config={"displayModeBar": False})
            with st.expander("Exact sensitivity results", icon=":material/table_chart:"):
                st.dataframe(_present_table(sensitivity), hide_index=True, width="stretch")
        city_download, manifest_download, methods_download = st.columns(3)
        with city_download:
            st.download_button("Download displayed city metrics", metrics.to_csv(index=False), file_name="city_metrics.csv", mime="text/csv", key="metrics_download", width="stretch")
        with manifest_download:
            st.download_button("Download source manifest", json.dumps(manifest, indent=2, default=str), file_name="manifest.json", mime="application/json", key="manifest_download", width="stretch")
        with methods_download:
            methods_payload = {
                "equations": list(presentation.equation_rows),
                "assumptions": list(presentation.assumption_rows),
                "recommendation_policy": list(presentation.policy_rows),
                "operational_benchmarks": list(presentation.operational_rows),
                "operational_event_records": list(presentation.operational_event_rows),
                "operational_coverage": list(presentation.operational_coverage_rows),
            }
            st.download_button("Download equations & assumptions", json.dumps(methods_payload, indent=2, default=str), file_name="model-methods.json", mime="application/json", key="methods_download", width="stretch")

    sources_tab, factors_tab, validation_tab, sensitivity_tab = st.tabs(
        ["Sources & hashes", "Factors & network", "Validation", "Readiness sensitivity & downloads"],
        key="methods_section",
        on_change="rerun",
    )
    if sources_tab.open:
        with sources_tab:
            _render_sources()
    if factors_tab.open:
        with factors_tab:
            _render_factors()
    if validation_tab.open:
        with validation_tab:
            _render_validation()
    if sensitivity_tab.open:
        with sensitivity_tab:
            _render_sensitivity()
