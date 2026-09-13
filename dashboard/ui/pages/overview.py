"""Judge- and decision-maker-facing proof sequence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.action_plans import (
    CITY_ACTION_PLANS,
    CITY_TRAFFIC_MANAGEMENT_PLANS,
    RECOMMENDATION_FOCUS_POINTS,
    TRAFFIC_MANAGEMENT_SCORES,
)
from dashboard.domain.comparison import build_city_comparison
from dashboard.domain.portfolio import build_portfolio_timeline, portfolio_summary
from dashboard.domain.solution_context import solution_context
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.models.action_impact import ACTION_SCOPES, estimate_action_impact
from dashboard.models.interventions import (
    CityInterventionInputs,
    InterventionFactorRegistry,
    factor_registry_from_snapshot,
    recommendation_candidates,
)
from dashboard.models.service_design import ELECTRIC_SERVICE_COST_MULTIPLIER, ELECTRIC_SERVICE_EMISSIONS_RATIO
from dashboard.models.solution_comparison import compare_transit_solutions
from dashboard.ui.presentation import PlatformPresentation, build_presentation
from dashboard.ui.theme import callout, metric_card, page_header, section_header
from dashboard.viz.portfolio import transit_solution_comparison_chart
from dashboard.viz.strategy_overlap import access_overlap_map, recommendation_focus_map
from dashboard.viz.style import COLORS, STATUS_COLORS, style_figure


def _number(value: Any, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.{decimals}f}{suffix}"


def _money(value: Any) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.0f}K"
    return f"${value:,.0f}"


def _added_frequency_candidate(artifacts: Mapping[str, Any], city: str) -> str:
    walking = artifacts.get("walking_networks", {})
    city_walk = walking.get(city, {}) if isinstance(walking, Mapping) else {}
    target = city_walk.get("target_stop") if isinstance(city_walk, Mapping) else None
    if not isinstance(target, Mapping):
        return "no route-specific candidate established"
    agency = str(target.get("agency") or "Transit agency")
    route = str(target.get("route") or "route not identified")
    stop = str(target.get("name") or "stop not identified")
    return f"{agency} Route {route} at {stop}"


def _render_added_frequency_cost_basis(
    priority: Any,
    artifacts: Mapping[str, Any],
    *,
    city: str,
    match_id: str,
) -> None:
    if priority.intervention != "Added transit frequency":
        return
    snapshot = artifacts.get("factor_snapshot", {})
    factor_rows = snapshot.get("factors", {}) if isinstance(snapshot, Mapping) else {}
    cost_factor = factor_rows.get("transit_cost_per_departure", {})
    capacity_factor = factor_rows.get("transit_passengers_per_departure", {})
    load_factor = factor_rows.get("service_load_factor", {})
    if not all(isinstance(item, Mapping) for item in (cost_factor, capacity_factor, load_factor)):
        return
    city_input = next(
        (
            row
            for row in artifacts.get("city_intervention_inputs", [])
            if str(row.get("city")) == city and str(row.get("match_id")) == match_id
        ),
        {},
    )
    arrival_hours = float(city_input.get("arrival_window_hours") or 3.0)
    package = next(
        item for item in recommendation_candidates() if item.name == "Added transit frequency"
    )
    departures_per_hour = float(package.added_transit_departures_per_hour)
    event_departures = departures_per_hour * arrival_hours
    base_cost_per_departure = float(cost_factor.get("base") or 0)
    base_capacity = float(capacity_factor.get("base") or 0)
    usable_load = float(load_factor.get("base") or 0)
    peak_capacity = departures_per_hour * base_capacity * usable_load
    source_ids = list(cost_factor.get("source_ids", []))
    source_rows = snapshot.get("sources", {}) if isinstance(snapshot, Mapping) else {}
    source = source_rows.get(source_ids[0], {}) if source_ids else {}
    source_name = source.get("source") or "national transit operating-cost reference"
    source_url = source.get("url")
    candidate = _added_frequency_candidate(artifacts, city)

    with st.expander(
        "Why the unallocated added-service estimate is low",
        expanded=False,
        icon=":material/calculate:",
    ):
        st.markdown(
            f"**Route allocation:** unresolved. The nearest event-relevant GTFS candidate is "
            f"**{candidate}**, but it is not an assigned route, direction, terminal, or operating plan."
        )
        st.markdown(
            f"**Base cost:** {event_departures:,.0f} added departures "
            f"({departures_per_hour:,.0f}/hour × {arrival_hours:g} hours) × "
            f"{base_cost_per_departure:,.0f} USD/departure = "
            f"**{float(priority.comparison_cost_base):,.0f} USD per match**."
        )
        st.markdown(
            f"**Capacity screen:** {departures_per_hour:,.0f} departures/hour × "
            f"{base_capacity:,.0f} passengers/departure × {usable_load:.0%} usable load = "
            f"**{peak_capacity:,.0f} passengers/hour**. The displayed "
            f"{float(priority.cost_per_passenger):,.2f} USD ratio divides the per-match operating screen by that peak-hour capacity; it is not an observed cost per rider."
        )
        st.caption(
            "The 140-passenger factor is a cross-mode planning assumption, not the capacity of the candidate route. Do not interpret the 630-passenger result as a route-specific claim."
        )
        source_label = f"[{source_name}]({source_url})" if source_url else str(source_name)
        st.caption(
            f"Source basis: {source_label}. {cost_factor.get('basis') or ''} "
            "This national order-of-magnitude screen excludes agency-specific overtime, deadhead, dispatch, security, station and curb operations, and fleet acquisition. Replace it with a local operating plan and quote before funding."
        )


def _scenario_scope(package: Mapping[str, Any]) -> str:
    """Translate a model composite into plain-language quantities."""

    fields = (
        ("shuttle_buses_per_hour", "shuttle buses/hour"),
        ("added_transit_departures_per_hour", "added transit departures/hour"),
        ("park_ride_spaces", "park-and-ride spaces"),
        ("park_ride_feeder_departures_per_hour", "feeder departures/hour"),
        ("bike_hub_spaces", "bike and micromobility spaces"),
        ("cooled_walkway_km", "km cooled walking corridor"),
        ("arrival_spreading_pct", "peak arrivals shifted"),
    )
    parts = []
    for field, label in fields:
        value = package.get(field)
        if value is not None and float(value) > 0:
            prefix = f"{float(value):g}%" if field == "arrival_spreading_pct" else f"{float(value):g}"
            parts.append(f"{prefix} {label}")
    return "; ".join(parts) if parts else "No intervention (baseline)"


def _metric_row(items: list[tuple[str, str, str, str, str]]) -> None:
    for start in range(0, len(items), 4):
        group = items[start : start + 4]
        for column, item in zip(st.columns(len(group)), group):
            value, label, status, note, accent = item
            with column:
                st.markdown(metric_card(value, label, status, note=note, accent=accent), unsafe_allow_html=True)


def _priority_city(comparison: pd.DataFrame, selected_city: str | None) -> str:
    if selected_city and selected_city in set(comparison["city"]):
        return selected_city
    qualified = comparison.dropna(subset=["capacity_qualified_gap_pph"])
    if not qualified.empty:
        return str(qualified.sort_values("capacity_qualified_gap_pph", ascending=False).iloc[0]["city"])
    return str(comparison.sort_values("peak_demand_pph", ascending=False, na_position="last").iloc[0]["city"])


def _portfolio_chart(timeline: pd.DataFrame) -> go.Figure:
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=timeline["event_date"],
            y=timeline["gap_resolved_passengers"],
            mode="lines+markers",
            name="Cumulative peak passengers addressed",
            line=dict(color=COLORS["teal"], width=3),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=timeline["event_date"],
            y=timeline["net_co2e_kg"],
            mode="lines+markers",
            name="Cumulative net CO2e avoided (kg)",
            line=dict(color=COLORS["blue"], width=2.5),
            yaxis="y2",
        )
    )
    figure.update_layout(
        yaxis=dict(title="Passengers addressed"),
        yaxis2=dict(title="Net CO2e avoided (kg)", overlaying="y", side="right", showgrid=False),
    )
    return style_figure(figure, 390)


def _readiness_components(metric: Mapping[str, Any]) -> tuple[go.Figure, pd.DataFrame]:
    rows = pd.DataFrame(
        [
            {
                "Component": label,
                "Score": metric.get(f"{key}_score"),
                "Evidence": metric.get(f"{key}_status", "unavailable"),
            }
            for key, label in (
                ("transit", "Transit service"),
                ("access", "Venue support"),
                ("heat", "Heat safety"),
                ("traffic", "Traffic management"),
            )
        ]
    )
    rows["Score"] = pd.to_numeric(rows["Score"], errors="coerce")
    chart = rows.dropna(subset=["Score"]).sort_values("Score")
    figure = go.Figure(
        go.Bar(
            x=chart["Score"],
            y=chart["Component"],
            orientation="h",
            marker_color=[STATUS_COLORS.get(str(status), COLORS["slate"]) for status in chart["Evidence"]],
            text=chart["Score"],
            texttemplate="%{text:.1f}",
            textposition="outside",
            customdata=chart[["Evidence"]],
            hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}<br>Evidence: %{customdata[0]}<extra></extra>",
        )
    )
    figure.update_xaxes(range=[0, 100], title="Component score (0–100)")
    return style_figure(figure, 300, legend=False), rows


def _current_strategies_summary(
    city: str, venue: Mapping[str, Any], artifacts: dict[str, Any],
    *, no_nearby_departures: bool = False,
) -> None:
    """Show what real transit service already exists for a host, sourced to the transit agency.

    Independent of anything this app recommends further down the page. The map
    reuses the same real GTFS stop/route evidence layers as the venue-access
    map further down the page - it illustrates where that service actually
    runs, not the strategy_benchmarks text itself, which has no coordinates.
    """

    section_header("Mobility summary")
    col_text, col_map = st.columns([1.3, 1])

    with col_text:
        benchmark = artifacts.get("strategy_benchmarks", {}).get(city, {})
        if benchmark:
            congestion = benchmark.get("congestion_management_evidence")
            congestion = congestion if isinstance(congestion, Mapping) else {}
            traffic_statement = congestion.get("command_note") or None
            traffic_publisher = congestion.get("command_publisher")
            traffic_source_title = congestion.get("command_source_title")
            traffic_source_url = congestion.get("command_source_url")
            if not traffic_statement:
                hotspots = [item for item in congestion.get("hotspots") or [] if isinstance(item, Mapping)]
                if hotspots:
                    first = hotspots[0]
                    traffic_statement = f"{first.get('location')} — {first.get('control')}"
                    traffic_publisher = first.get("publisher")
                    traffic_source_title = first.get("source_title")
                    traffic_source_url = first.get("source_url")
            if traffic_statement:
                traffic_source = (
                    f"[{traffic_source_title}]({traffic_source_url})"
                    if traffic_source_title and traffic_source_url
                    else "Source not available"
                )
                st.markdown(f"**Traffic** — {traffic_statement}")
                st.caption(f"{traffic_publisher or 'Publisher not available'} · {traffic_source}")

            dedicated = benchmark.get("dedicated_service_evidence")
            if isinstance(dedicated, Mapping) and dedicated.get("basis"):
                dedicated_source = (
                    f"[{dedicated.get('source_title')}]({dedicated.get('source_url')})"
                    if dedicated.get("source_title") and dedicated.get("source_url")
                    else "Source not available"
                )
                st.markdown(f"**Dedicated service** — {dedicated.get('basis')}")
                st.caption(f"{dedicated.get('publisher', 'Publisher not available')} · {dedicated_source}")

            sustainability = benchmark.get("sustainability_evidence")
            sustainability = sustainability if isinstance(sustainability, Mapping) else {}
            if sustainability.get("fleet_electrification_basis"):
                sustainability_source = (
                    f"[{sustainability.get('source_title')}]({sustainability.get('source_url')})"
                    if sustainability.get("source_title") and sustainability.get("source_url")
                    else "Source not available"
                )
                st.markdown(f"**Sustainability** — {sustainability.get('fleet_electrification_basis')}")
                st.caption(f"{sustainability.get('publisher', 'Publisher not available')} · {sustainability_source}")

            if sustainability.get("pedestrian_infrastructure_basis"):
                pedestrian_source = (
                    f"[{sustainability.get('pedestrian_infrastructure_source_title')}]"
                    f"({sustainability.get('pedestrian_infrastructure_source_url')})"
                    if sustainability.get("pedestrian_infrastructure_source_title")
                    and sustainability.get("pedestrian_infrastructure_source_url")
                    else "Source not available"
                )
                st.markdown(
                    f"**Pedestrian infrastructure** — {sustainability.get('pedestrian_infrastructure_basis')}"
                )
                st.caption(
                    f"{sustainability.get('pedestrian_infrastructure_publisher', 'Publisher not available')} · "
                    f"{pedestrian_source}"
                )
            else:
                st.markdown("**Pedestrian infrastructure** — No real, sourced evidence found for this venue yet.")
        else:
            st.caption(f"No published transit-service benchmark found for {city}.")

    with col_map:
        layers = dict(artifacts.get("map_layers", {}).get(city, {}))
        # Keep the 15/30-minute walking isochrones (real evidence of walkable
        # range) but drop the "Network path to event-relevant stop" line -
        # that's about one specific walking route, not this map's subject.
        layers["walk"] = [
            row for row in layers.get("walk", []) if isinstance(row, Mapping) and "minutes" in row
        ]
        agencies = artifacts.get("gtfs", {}).get(city, {}).get("agencies", [])
        agency_label = " & ".join(agencies) if agencies else "Transit"
        st.plotly_chart(
            access_overlap_map(
                venue,
                layers,
                route_label=f"{agency_label} routes",
                stop_label=f"{agency_label} stops",
            ),
            width="stretch",
            config={"displayModeBar": False},
            key=f"current_strategies_map_{city}",
        )
        st.caption(f"Real {agency_label} routes and stops, and modeled 15/30-minute walking isochrones.")
        if no_nearby_departures:
            callout(
                "warning",
                "No nearby event-window departures",
                "The pinned schedule contains no departures within the half-mile venue catchment.",
            )


_PRESENTATION_CACHE_KEY = "_presentation_cache"


def _cached_presentation(metrics: pd.DataFrame, artifacts: dict[str, Any]) -> PlatformPresentation:
    """Cache build_presentation's all-city/all-match view across reruns.

    Streamlit reruns this whole script on every widget interaction (a city
    switch, an expander, an unrelated toggle), and build_presentation iterates
    every match for every host regardless of which single city is shown - only
    metrics (itself already cached in app.py on weights/include_estimates)
    changes what it returns, so cache on that object's identity instead of
    rebuilding it on every unrelated rerun.
    """

    cache_key = id(metrics)
    cached = st.session_state.get(_PRESENTATION_CACHE_KEY)
    if cached is not None and cached[0] == cache_key:
        return cached[1]
    presentation = build_presentation(metrics, artifacts)
    st.session_state[_PRESENTATION_CACHE_KEY] = (cache_key, presentation)
    return presentation


def _render_city_overview_tab(
    city: str,
    artifacts: dict[str, Any],
    match: Any,
    access: Any,
    decision_metric: Mapping[str, Any],
    city_plan: Mapping[str, str],
) -> None:
    no_nearby_departures = access.capacity_qualified and float(access.transit_capacity_high or 0) == 0
    _current_strategies_summary(
        city,
        {"name": match.venue, "lat": HOST_CITIES.get(city, {}).get("lat"), "lon": HOST_CITIES.get(city, {}).get("lon")},
        artifacts,
        no_nearby_departures=no_nearby_departures,
    )
    if city_plan.get("specific_problem"):
        callout("warning", f"{city}'s specific problem", city_plan["specific_problem"], prominent=True)
    else:
        callout(
            "info",
            "No curated problem statement yet",
            f"No hand-authored specific-problem note exists for {city}.",
        )
    if not access.capacity_qualified:
        callout(
            "warning",
            "This case is not capacity-qualified",
            "Demand remains visible, but missing or partial event transit evidence prevents a strict residual-gap claim.",
        )
    elif not no_nearby_departures and access.walking_status == "unavailable":
        callout(
            "warning",
            "Transit gap qualified; walking route unavailable",
            "Scheduled capacity can support a residual passenger gap, but the pedestrian connection remains a separate missing evidence component.",
        )

    section_header("Readiness Scores")
    readiness_figure, _ = _readiness_components(decision_metric)
    st.plotly_chart(readiness_figure, width="stretch", config={"displayModeBar": False})


def _match_impact_context(
    city: str, artifacts: Mapping[str, Any], match_id: str,
) -> tuple[float, CityInterventionInputs, InterventionFactorRegistry]:
    city_input = next(
        (row for row in artifacts.get("city_intervention_inputs", [])
         if row.get("city") == city and str(row.get("match_id")) == match_id),
        {},
    )
    movement = next(
        (row for row in artifacts.get("movement_scenarios", [])
         if row.get("city") == city and str(row.get("match_id")) == match_id),
        {},
    )
    return (
        float(movement["attendance_base"]),
        CityInterventionInputs(**city_input),
        factor_registry_from_snapshot(artifacts.get("factor_snapshot", {})),
    )


def _render_recommended_action_impact(city: str, artifacts: Mapping[str, Any], match_id: str) -> None:
    st.markdown("##### Projected impact")
    try:
        attendance, city_input, factors = _match_impact_context(city, artifacts, match_id)
        inputs = {
            "attendance": attendance,
            "private_vehicle_share": city_input.private_vehicle_share,
            "vehicle_occupancy": city_input.average_vehicle_occupancy,
            "private_trip_miles": city_input.average_private_trip_miles,
            "local_leg_miles": city_input.venue_area_leg_miles,
            "arrival_hours": city_input.arrival_window_hours,
        }
        cases = estimate_action_impact(city, factors=factors, **inputs)
    except (KeyError, TypeError, ValueError):
        st.caption("Estimate unavailable: this match needs attendance, travel inputs, and a valid factor registry.")
        return
    base = cases[1]
    st.caption("Illustrative planning estimate for this action, per match; not a validated forecast or local quote.")
    _metric_row([
        (_number(base["passengers"]), "Passengers addressed / match", "scenario",
         "Beneficiaries, not necessarily new riders", "teal"),
        (_number(base["net_co2e_kg"], " kg"), "Net CO2e avoided / match", "scenario",
         "Compared with the stated service baseline", "blue"),
        (_number(base["net_vehicle_miles"], " mi"), "Net vehicle-miles saved / match", "scenario",
         "Includes empty return trips", "slate"),
        (_money(base["first_event_cost"]), "Estimated first-event cost", "scenario",
         f"{_money(base['capital_cost'])} upfront + {_money(base['operating_cost'])} per match", "amber"),
    ])
    st.caption(
        f"Operational CO2e screen: {base['co2e_screen']}. "
        "Recommended actions require positive savings under the stated operating conditions. Zero does not meet that target."
    )
    with st.expander("Estimate assumptions and scenario range"):
        scope = ACTION_SCOPES[city]
        st.write(scope.description)
        st.caption(
            "Action scope, uptake, route cycles, staffing allowances, and construction budgets are explicit analyst "
            "assumptions. Low/base/high are alternative scope cases, not statistical confidence bounds. "
            "Capital costs are charged once; later matches incur operating costs only."
        )
        st.write(
            f"Base match attendance: {inputs['attendance']:,.0f}. Private-mode share: "
            f"{inputs['private_vehicle_share']:.0%}; vehicle occupancy: {inputs['vehicle_occupancy']:.1f}. "
            f"Avoided round-trip distance: {base['car_round_trip_miles']:.1f} mi. "
            f"Bus service: {inputs['arrival_hours']:g} hours each for arrivals and departures."
        )
        st.write(
            f"Base non-bus operating allowance: {_money(scope.operating_allowance)} per match; "
            f"upfront allowance: {_money(scope.capital_allowance)}. "
            "Scope scales to 60% / 100% / 140%; these allowances scale to 60% / 100% / 160%. "
            "Bus counts and dispatched trips are whole numbers, limited by reserved demand. "
            "Capacity, loading, cost, and conventional emissions factors use the corresponding registry case."
        )
        st.caption(
            f"Factor registry: {factors.registry_version}. Base bus capacity: "
            f"{factors.shuttle_passengers_per_bus.base:g} passengers at {factors.service_load_factor.base:.0%} load; "
            f"electric bus cost allowance: ${factors.shuttle_cost_per_bus_hour.base * ELECTRIC_SERVICE_COST_MULTIPLIER:g}/hour. "
            f"Car emissions: {factors.private_vehicle_co2e_kg_per_mile.base:g} kg CO2e/mi; "
            f"electric bus emissions: {factors.service_vehicle_co2e_kg_per_mile.base * ELECTRIC_SERVICE_EMISSIONS_RATIO:g} kg CO2e/mi."
        )
        st.caption(
            "Electric operation assumes 40% of conventional operating CO2e and a 20% bus-hour premium "
            "for electric leasing and temporary charging. These are procurement conditions to validate, "
            "not verified local electricity or lease rates. Dallas, Kansas City, and Los Angeles replace "
            "equivalent conventional bus trips; other shuttle actions add service. Cost is the gross service budget."
        )
        st.caption(
            f"CO2e accounting per match: {_number(base['avoided_car_co2e_kg'], ' kg')} from car trips replaced "
            f"+ {_number(base['baseline_service_co2e_kg'], ' kg')} from replaced conventional service "
            f"- {_number(base['proposed_service_co2e_kg'], ' kg')} from proposed electric service."
        )
        if scope.incentive_per_shifted_rider:
            st.caption(
                f"Travel-credit assumption: {_money(scope.incentive_per_shifted_rider)} per additional rider "
                f"switching from a car; {_money(base['incentive_cost'])} included in base operating cost. "
                "Actual redemption by existing transit riders would add cost without the modeled emissions benefit."
            )
        if scope.buses:
            st.write(
                f"Minimum car-trip replacement for operating CO2e break-even: {base['minimum_car_shift_share']:.1%} "
                f"of riders; design target: {scope.private_shift_share:.0%}. "
                "Verify actual bookings, route distance, load and charging emissions before dispatch."
            )
        st.markdown(
            "Passengers addressed = attendance x assumed beneficiary share, or bus seats x load x arrival cycles, "
            "capped at attendance. Where operating improvements and bus service overlap, use the larger "
            "beneficiary group rather than adding them. Avoided car-miles = passengers switching from cars / vehicle occupancy x "
            "round-trip distance. Net miles and CO2e compare the proposed service with its stated baseline, including empty return legs. "
            "Passenger counts are not doubled for return travel. Gate, signage, and enforcement improvements "
            "do not automatically create new capacity or mode shift."
        )
        columns = {
            "case": "Scenario", "passengers": "Passengers addressed", "shifted_passengers": "Passengers shifted from cars",
            "net_co2e_kg": "Net CO2e avoided (kg)", "net_vehicle_miles": "Net vehicle-miles saved",
            "operating_cost": "Operating cost / match ($)", "capital_cost": "Upfront cost ($)",
            "first_event_cost": "First-event cost ($)",
            "co2e_screen": "Operational CO2e screen",
        }
        st.dataframe(pd.DataFrame(cases)[list(columns)].rename(columns=columns).round(0),
                     hide_index=True, width="stretch")
        st.caption("Construction emissions, idling savings, fare revenue, and parking revenue are excluded. "
                   "Local ridership, operating plans, and bids are needed before funding.")


def _render_transit_solution_comparison(
    city: str, artifacts: Mapping[str, Any], match_id: str, city_plan: Mapping[str, str],
) -> None:
    st.markdown("##### Compare transit solutions")
    try:
        attendance, inputs, factors = _match_impact_context(city, artifacts, match_id)
        solutions = pd.DataFrame(compare_transit_solutions(attendance, inputs, factors))
    except (KeyError, TypeError, ValueError):
        st.caption("Comparison unavailable: match attendance, travel inputs, and a valid factor registry are required.")
        return
    contexts = solution_context(city, artifacts.get("strategy_benchmarks", {}).get(city, {}))
    for column in ("city_context", "context_note", "context_source"):
        solutions[column] = solutions["solution"].map(lambda name: contexts[name][column])
    recommended = None
    if city in ACTION_SCOPES and city_plan.get("recommended_action"):
        base = estimate_action_impact(
            city, attendance, inputs.private_vehicle_share, inputs.average_vehicle_occupancy,
            inputs.average_private_trip_miles, inputs.venue_area_leg_miles,
            inputs.arrival_window_hours, factors,
        )[1]
        recommended = {
            **base,
            "solution": f"Recommended: {city_plan.get('expected_impact', 'First action')}",
            "label": "Recommended first action",
        }
    st.plotly_chart(
        transit_solution_comparison_chart(solutions, recommended), width="stretch",
        config={"displayModeBar": False}, key="city_transit_solution_comparison",
    )
    if (solutions["co2e_screen"] != "Pass").any() or (recommended and recommended["co2e_screen"] != "Pass"):
        st.warning("A design fails the operating CO2e screen. Revise routing, vehicle emissions, or confirmed ridership before deployment.")
    st.caption(
        "Per-match planning scenarios. Passengers addressed includes existing riders who benefit; "
        "it does not mean new capacity. Designs target lower operating CO2e using electric service and demand-based dispatch."
    )
    st.caption(
        "The recommended-action star uses the Projected impact estimate above. Existing, related, and "
        "published-plan labels describe strategy overlap in the app's evidence snapshot, not measured "
        "outcomes or adoption of the modeled scenario."
    )
    with st.expander("Solution assumptions and exact values"):
        st.caption(
            "Independent examples, not equal-budget alternatives or additive benefits. "
            "Lane and electric-fleet cases modify an assumed existing service; park-and-ride and "
            "frequency cases add service. None is a validated local operating plan. "
            "Manufacturing and construction emissions are excluded."
        )
        for index, row in enumerate(solutions.to_dict("records"), start=1):
            st.markdown(f"**{index}. {row['solution']}**")
            st.markdown(f"**{row['city_context']}**: {row['context_note']}")
            if row["context_source"] and row["city_context"] != "Not documented":
                st.markdown(f"[City strategy evidence]({row['context_source']})")
            st.write(row["basis"])
            st.caption(
                f"Operational CO2e screen: {row['co2e_screen']}. Minimum share of addressed passengers "
                f"replacing car trips for break-even: {row['minimum_car_shift_share']:.1%}."
            )
        st.caption(
            f"Selected match: {attendance:,.0f} attendees; {inputs.arrival_window_hours:g}-hour "
            "arrival and departure windows. Bus cycles assume 20 mph plus 15 minutes layover. "
            f"Round trips: shuttle {inputs.shuttle_round_trip_miles:.1f} mi; matched feeder/car corridor "
            f"{inputs.venue_area_leg_miles:.1f} mi; transit "
            f"{inputs.transit_round_trip_miles:.1f} mi. Private travel: "
            f"{inputs.average_private_trip_miles:.1f} mi round trip, including a "
            f"{inputs.venue_area_leg_miles:.1f}-mi venue leg; {inputs.average_vehicle_occupancy:g} "
            f"people per car and {inputs.private_vehicle_share:.0%} private-mode share. "
            f"Factors: {factors.registry_version}. Passenger counts are not doubled for return travel."
        )
        st.caption(
            "Added bus and transit service uses an assumed electric emissions factor of 40% of the conventional "
            "vehicle proxy. This is a design condition, not a verified local grid estimate. Validate charging, "
            "ridership, matched hub routes and spare capacity before deployment. Failed screens require redesign; "
            "negative estimates are retained. Construction, manufacturing and broader environmental impacts are not scored."
        )
        display = solutions[["solution", "city_context", "passengers", "shifted_passengers", "net_co2e_kg", "net_vehicle_miles", "co2e_screen"]]
        st.dataframe(display.rename(columns={
            "solution": "Solution", "city_context": "City approach", "passengers": "Passengers addressed / match",
            "shifted_passengers": "Passengers shifted from cars",
            "net_co2e_kg": "Net CO2e avoided (kg / match)",
            "net_vehicle_miles": "Net vehicle-miles saved / match",
            "co2e_screen": "Operational CO2e screen",
        }).round(0), hide_index=True, width="stretch")


def _render_transit_solution_tab(
    city: str,
    artifacts: dict[str, Any],
    match: Any,
    recommendations: tuple[Any, ...],
    scenarios: tuple[Any, ...],
    city_plan: Mapping[str, str],
) -> None:
    qualified_options = [item for item in recommendations if item.evidence_qualified]
    exploratory_options = [item for item in recommendations if not item.evidence_qualified]
    screening_options = qualified_options or exploratory_options
    priority = min(
        qualified_options,
        key=lambda item: (
            item.cost_per_passenger if item.cost_per_passenger is not None else float("inf"),
            item.intervention,
        ),
        default=None,
    )

    section_header("Recommended first action")
    if city_plan.get("recommended_action"):
        with st.container(border=True):
            st.markdown(f"### {city_plan['recommended_action']}")
            why = city_plan.get("why_this_action") or city_plan.get("rationale") or city_plan.get("specific_problem")
            if why:
                st.markdown("**Why this action**")
                st.write(why)
    else:
        callout("warning", "No curated action plan yet", f"No hand-authored recommendation exists for {city}.")

    if city_plan.get("recommended_action"):
        _render_recommended_action_impact(city, artifacts, str(match.match_id))

    focus_points = RECOMMENDATION_FOCUS_POINTS.get(city, ())
    if city_plan.get("recommended_action") and focus_points:
        venue_context = HOST_CITIES.get(city, {})
        venue = {"name": match.venue, "lat": venue_context.get("lat"), "lon": venue_context.get("lon")}
        st.plotly_chart(
            recommendation_focus_map(venue, focus_points),
            width="stretch",
            config={"displayModeBar": False},
            key="transit_solution_map",
        )
        named = ", ".join(str(point.get("name")) for point in focus_points)
        st.caption(
            f"The real place(s) this recommendation names: {named}. This is independently-verified geography, "
            "not the separately-modeled engine hub pick shown in Traffic management solution, which answers a "
            "different (bounded GTFS connectivity) question."
        )

    _render_transit_solution_comparison(city, artifacts, str(match.match_id), city_plan)

    if screening_options:
        frequency_option = next(
            (option for option in recommendations if option.intervention == "Added transit frequency"),
            None,
        )
        # Every host currently lacks a transit-agency route assignment for this
        # measure (it's a structural evidence gap, not city-specific insight),
        # so it's surfaced once in the table's "Scope and location" column
        # below rather than as a repeated per-city warning callout.

        lens_table = pd.DataFrame(
            [
                {
                    "Decision": (
                        "Model's pick"
                        if priority is option
                        else "Compare"
                        if option.evidence_qualified
                        else "Hold - evidence gap"
                    ),
                    "Investment": option.intervention,
                    "Scope and location": (
                        f"{option.scope}. Nearest GTFS candidate: "
                        f"{_added_frequency_candidate(artifacts, city)}; not assigned."
                        if option.intervention == "Added transit frequency"
                        else option.scope
                    ),
                    "Peak passengers (access)": option.gap_resolved_passengers,
                    "Net CO2e avoided (emissions)": option.net_co2e_kg,
                    "Net VMT avoided (traffic)": option.net_vmt_base,
                    "Per-match screening cost": option.comparison_cost_base,
                    "Screening cost ratio": option.cost_per_passenger,
                    "Lead time": option.lead_time_band,
                    "Evidence": option.evidence_quality,
                }
                for option in recommendations
            ]
        )
        with st.expander("Exact quantified screen", icon=":material/table_chart:"):
            st.caption("Separate national screening models; these are not the four solution scenarios plotted above.")
            st.dataframe(
                lens_table,
                hide_index=True,
                width="stretch",
                column_config={
                    "Peak passengers (access)": st.column_config.NumberColumn(format="%.0f"),
                    "Net CO2e avoided (emissions)": st.column_config.NumberColumn(format="%.0f kg"),
                    "Net VMT avoided (traffic)": st.column_config.NumberColumn(format="%.0f mi"),
                    "Per-match screening cost": st.column_config.NumberColumn(format="$%,.0f"),
                    "Screening cost ratio": st.column_config.NumberColumn(format="$%.2f"),
                },
            )
            st.caption(
                f"{len(qualified_options)} qualified and {len(exploratory_options)} exploratory options. "
                "Local bids, fleet constraints, rights-of-way, and observed uptake should replace the shared "
                "national screening assumptions before funding. Net CO2e and net VMT can be negative for a poor "
                "option (more driving induced than avoided)."
            )
            if frequency_option is not None:
                _render_added_frequency_cost_basis(
                    frequency_option,
                    artifacts,
                    city=city,
                    match_id=match.match_id,
                )
    else:
        callout(
            "warning",
            "No match-specific action",
            "Movement, transit, factors, and intervention evidence must be complete before screening an option.",
        )

    show_composites = st.toggle(
        "Show advanced composite model tests",
        value=False,
        help="Operational and capital composites combine multiple measures for sensitivity testing; they are not funding recommendations.",
        key="brief_show_composites",
    )
    if not show_composites:
        return

    section_header(
        "Composite scenario sensitivity",
        "These fixed multi-measure bundles stress-test the model. They are not locally engineered plans or investment recommendations.",
        "Advanced",
    )
    st.markdown("#### Exact composite definitions")
    scenario_rows = pd.DataFrame(
        [
            {
                "Composite": item.name,
                "What it combines": _scenario_scope(item.package),
                "Gap resolved": item.gap_resolved_passengers,
                "Cost": item.cost_base,
                "Net CO2e avoided": item.net_co2e_kg_base,
                "Lead time": item.lead_time_band,
                "Evidence": item.status,
            }
            for item in scenarios
        ]
    )
    chart = scenario_rows.dropna(subset=["Gap resolved", "Cost"]).copy()
    if not chart.empty:
        chart["Climate magnitude"] = chart["Net CO2e avoided"].abs().fillna(0) + 1
        figure = px.scatter(
            chart,
            x="Cost",
            y="Gap resolved",
            color="Composite",
            size="Climate magnitude",
            text="Composite",
            color_discrete_map={
                "Baseline": COLORS["slate"],
                "Operational Package": COLORS["teal"],
                "Capital Package": COLORS["blue"],
            },
        )
        figure.update_traces(textposition="top center")
        figure.update_xaxes(tickprefix="$", title="Planning cost")
        st.plotly_chart(style_figure(figure, 390), width="stretch", config={"displayModeBar": False})
    with st.expander("Exact composite outcome table"):
        st.dataframe(scenario_rows, hide_index=True, width="stretch")

    st.markdown("#### Tournament sensitivity")
    scope_labels = {
        "match": "Selected match",
        "city_tournament": f"{city} tournament",
        "us_tournament": "All U.S. matches",
    }
    scope_label = (
        st.segmented_control(
            "Time horizon",
            list(scope_labels.values()),
            default="Selected match",
            key="brief_scope",
        )
        or "Selected match"
    )
    scope = next(key for key, label in scope_labels.items() if label == scope_label)
    package_name = st.selectbox("Composite scenario", [item.name for item in scenarios], index=1, key="brief_package")
    include_partial_portfolio = st.checkbox(
        "Include partial or unavailable access evidence in screening totals",
        value=False,
        help="Default totals include only capacity-qualified access results. Opt-in totals remain scenario screens and retain the access status for every match.",
        key="brief_include_partial",
    )
    factors = factor_registry_from_snapshot(artifacts["factor_snapshot"])
    timeline = build_portfolio_timeline(
        artifacts.get("match_events", []),
        artifacts.get("intervention_outcomes", []),
        artifacts.get("city_intervention_inputs", []),
        factors,
        package_name=package_name,
        scope=scope,
        city=city,
        match_id=match.match_id,
        access_rows=artifacts.get("access_gaps", []),
        include_partial=include_partial_portfolio,
    )
    summary = portfolio_summary(timeline)
    _metric_row(
        [
            (
                str(summary.get("match_count", 0)),
                "Matches included",
                "scenario" if not timeline.empty else "unavailable",
                f"{summary.get('omitted_matches', 0)} omitted for evidence",
                "slate",
            ),
            (
                _number(summary.get("gap_resolved_passengers"), " passengers"),
                "Cumulative peak gaps addressed",
                "scenario",
                "Sum of match-level peak benefits",
                "teal",
            ),
            (
                _number(summary.get("net_co2e_kg"), " kg"),
                "Cumulative net CO2e avoided",
                "scenario",
                "May be negative for poor service",
                "blue",
            ),
            (
                _money(summary.get("total_cost_base")),
                "Cumulative planning cost",
                "scenario",
                "Capital + recurring operations",
                "amber",
            ),
        ]
    )
    if not timeline.empty:
        st.plotly_chart(_portfolio_chart(timeline), width="stretch", config={"displayModeBar": False})
        with st.expander("Accessible table: cumulative outcome ledger"):
            st.dataframe(timeline, hide_index=True, width="stretch")


def _render_congestion_hotspots(city: str, artifacts: dict[str, Any]) -> None:
    """Show real, cited match-day road closures/enforcement zones - where officials

    have actually documented congestion and stationed control points, sourced to
    local news and official agency reporting (see dashboard/pipeline/public/
    strategy_benchmarks.py's congestion_management_evidence field).
    """

    benchmark = artifacts.get("strategy_benchmarks", {}).get(city, {})
    evidence = benchmark.get("congestion_management_evidence")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    hotspots = [item for item in evidence.get("hotspots") or [] if isinstance(item, Mapping)]

    st.markdown("##### Documented traffic controls")
    if not hotspots:
        callout(
            "warning",
            "No documented congestion hotspots found yet",
            f"No real, cited reporting on match-day road closures or congestion control points was found for {city}.",
        )
        return

    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Location": item.get("location"),
                    "What happens here": item.get("control"),
                    "Source": item.get("source_url"),
                }
                for item in hotspots
            ]
        ),
        hide_index=True,
        width="stretch",
        column_config={
            "Location": st.column_config.TextColumn(width="medium"),
            "What happens here": st.column_config.TextColumn(width="large"),
            "Source": st.column_config.LinkColumn(display_text="Open source"),
        },
    )
    if evidence.get("command_note"):
        command_source = (
            f"[{evidence.get('command_source_title')}]({evidence.get('command_source_url')})"
            if evidence.get("command_source_title") and evidence.get("command_source_url")
            else None
        )
        st.markdown(f"**Command and enforcement** — {evidence['command_note']}")
        if command_source:
            st.caption(f"{evidence.get('command_publisher', 'Publisher not available')} · {command_source}")
    st.caption(
        "Real, cited road closures, restrictions, and enforcement zones reported around this venue - not a "
        "locally engineered patrol deployment plan. These are the documented control points officials and "
        "traffic patrols would need to staff on match days, not exact patrol coordinates."
    )


def _render_traffic_management_tab(
    city: str,
    artifacts: dict[str, Any],
) -> None:
    _render_congestion_hotspots(city, artifacts)

    st.markdown("##### Recommended traffic management solution")
    plan = CITY_TRAFFIC_MANAGEMENT_PLANS.get(city, {})
    score_entry = TRAFFIC_MANAGEMENT_SCORES.get(city, {})
    if plan.get("recommended_action"):
        with st.container(border=True):
            if score_entry.get("score") is not None:
                st.caption(f"Traffic management score: {score_entry['score']:.0f}/100")
            st.markdown(f"### {plan['recommended_action']}")
            st.write(plan.get("rationale", ""))
            if score_entry.get("rationale"):
                st.caption(score_entry["rationale"])
    else:
        callout(
            "warning",
            "No curated traffic management plan yet",
            f"No hand-authored traffic-management recommendation exists for {city}.",
        )


def render_decision_brief(
    metrics: pd.DataFrame,
    artifacts: dict[str, Any],
    *,
    selected_city: str | None,
    weights: Mapping[str, float],
) -> None:
    presentation = _cached_presentation(metrics, artifacts)
    comparison = build_city_comparison(
        metrics,
        artifacts.get("access_gaps", []),
        artifacts.get("investment_recommendations", []),
        weights=weights,
    )
    city = _priority_city(comparison, selected_city)
    row = comparison[comparison["city"] == city].iloc[0]
    decision = presentation.city(city)
    match_id = row.get("representative_match_id")
    match = decision.match(str(match_id)) if match_id else decision.match()
    access = decision.access(match.match_id)
    scenarios = decision.scenario_set(match.match_id)
    recommendations = decision.recommendation_set(match.match_id)
    city_plan = CITY_ACTION_PLANS.get(city, {})

    page_header(
        "City action plan",
        city,
        match.venue,
        metric=(
            "Estimated peak movement demand",
            _number(access.peak_demand_per_hour),
            "passengers / hour",
            "Base attendance scenario; peak may be a post-match departure",
        ),
    )

    tabs = st.tabs(
        [
            ":material/location_city: City overview",
            ":material/directions_bus: Transit solution",
            ":material/traffic: Traffic management solution",
        ],
        key="city_brief_objective",
        on_change="rerun",
    )
    renderers = (
        lambda: _render_city_overview_tab(city, artifacts, match, access, decision.metric, city_plan),
        lambda: _render_transit_solution_tab(city, artifacts, match, recommendations, scenarios, city_plan),
        lambda: _render_traffic_management_tab(city, artifacts),
    )
    for tab, renderer in zip(tabs, renderers):
        if tab.open:
            with tab:
                renderer()
