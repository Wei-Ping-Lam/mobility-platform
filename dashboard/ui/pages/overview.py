"""Judge- and decision-maker-facing proof sequence."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.action_plans import (
    CITY_ACTION_PLANS,
    CITY_TRAFFIC_MANAGEMENT_PLANS,
    RECOMMENDATION_FOCUS_POINTS,
    TRAFFIC_MANAGEMENT_SCORES,
)
from dashboard.domain.comparison import build_city_comparison
from dashboard.domain.solution_context import solution_context
from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.models.action_impact import ACTION_SCOPES, estimate_action_impact
from dashboard.models.capital_alternatives import (
    ALTERNATIVES,
    BRT_COST_SOURCE,
    BUS_COST_SOURCE,
    SPARE_FLEET_SOURCE,
    estimate_capital_alternative,
)
from dashboard.models.electric_bus import (
    CITY_GRID_REGION,
    EGRID_SOURCE,
    ENERGY_SOURCE,
    ENERGY_STRESS_SOURCE,
)
from dashboard.models.interventions import (
    CityInterventionInputs,
    InterventionFactorRegistry,
    factor_registry_from_snapshot,
    recommendation_candidates,
)
from dashboard.models.service_design import ELECTRIC_SERVICE_COST_MULTIPLIER
from dashboard.models.solution_comparison import compare_transit_solutions
from dashboard.ui.presentation import PlatformPresentation, build_presentation
from dashboard.ui.theme import callout, metric_card, page_header, section_header
from dashboard.viz.portfolio import READINESS_COMPONENTS, transit_solution_comparison_chart
from dashboard.viz.strategy_overlap import (
    access_overlap_map,
    add_road_controls,
    recommendation_focus_map,
    road_controls_map,
)
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


def _readiness_components(metric: Mapping[str, Any]) -> go.Figure:
    rows = pd.DataFrame([
        {
            "Component": label,
            "Score": metric.get(column),
            "Evidence": metric.get(column.replace("_score", "_status"), "unavailable"),
        }
        for label, column in READINESS_COMPONENTS.items()
    ])
    rows["Score"] = pd.to_numeric(rows["Score"], errors="coerce")
    figure = go.Figure(go.Bar(
        x=rows["Score"],
        y=rows["Component"],
        orientation="h",
        marker_color=[STATUS_COLORS.get(str(status), COLORS["slate"]) for status in rows["Evidence"]],
        text=rows["Score"],
        texttemplate="%{text:.1f}",
        textposition="outside",
        cliponaxis=False,
        customdata=rows[["Evidence"]],
        hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}/100<br>Evidence: %{customdata[0]}<extra></extra>",
    ))
    figure.update_xaxes(range=[0, 100], title="Component score (0-100)")
    figure.update_yaxes(autorange="reversed")
    return style_figure(figure, 300, legend=False, margin=dict(l=18, r=42, t=34, b=26))


def _current_strategies_summary(
    city: str, venue: Mapping[str, Any], artifacts: dict[str, Any],
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
                dedicated_basis = str(dedicated.get("basis")).replace("$", r"\$")
                st.markdown(f"**Dedicated service** — {dedicated_basis}")
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
        if city == "New York/NJ":
            shapes = layers.get("gtfs_routes", [])
            meadowlands = [row for row in shapes if row.get("route_name") == "MRL"]
            layers["highlight_routes"] = [
                {**row, "name": "Meadowlands Rail Line: Secaucus Junction - Meadowlands"}
                for row in meadowlands[:1]
            ]
            layers["gtfs_routes"] = [
                {**row, "name": "Main/Bergen County Line (MNBN)"}
                if row.get("route_name") == "MNBN" else row
                for row in shapes if row.get("route_name") != "MRL"
            ]
            city_gtfs = artifacts.get("gtfs", {}).get(city, {})
            secaucus = next(
                (row for row in city_gtfs.get("regional_hubs", []) if row.get("stop_id") == "38174"), None,
            )
            stadium_stop = next(
                (row for row in layers.get("gtfs", []) if row.get("stop_id") == "40570"), None,
            )
            layers["highlight_stops"] = [
                {**row, "name": name} for row, name in (
                    (secaucus, "Secaucus Junction"),
                    (stadium_stop, "Meadowlands (Sports Complex)"),
                ) if row
            ]
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
        _road_control_sources(artifacts.get("road_closures", {}).get(city, []))
        if city == "New York/NJ":
            st.caption(
                "[Meadowlands Rail Line: Secaucus Junction to Meadowlands (Sports Complex)]"
                "(https://www.njtransit.com/first-run/take-nj-transit-meadowlands). "
                "Route geometry is from the pinned GTFS feed; service depends on the event schedule."
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
    readiness_figure = _readiness_components(decision_metric)
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
    if scope_note := CITY_ACTION_PLANS.get(city, {}).get("impact_scope_note"):
        st.caption(scope_note)
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
    _metric_row([
        (_number(base["passengers"]), "Passengers addressed / match", "scenario",
         "Beneficiaries, not necessarily new riders", "teal"),
        (_number(base["net_co2e_kg"], " kg"), "Net CO2e avoided / match", "scenario",
         f"Factor sensitivity: {_number(base['net_co2e_kg_low'])} to {_number(base['net_co2e_kg_high'])} kg", "blue"),
        (_number(base["net_vehicle_miles"], " mi"), "Net vehicle-miles saved / match", "scenario",
         "Includes empty returns and depot allowance", "slate"),
        (_money(base["first_event_cost"]), "Estimated first-event cost", "scenario",
         f"{_money(base['capital_cost'])} upfront + {_money(base['operating_cost'])} per match", "amber"),
    ])
    if base["net_co2e_kg"] <= 0:
        st.warning("This base case does not reduce operating CO2e. Validate or redesign service before deployment.")
    with st.expander("Estimate assumptions and scenario range"):
        scope = ACTION_SCOPES[city]
        st.write(scope.description.replace("$", r"\$"))
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
        st.write((
            f"Base non-bus operating allowance: {_money(scope.operating_allowance)} per match; "
            f"upfront allowance: {_money(scope.capital_allowance)}. "
            "Scope scales to 60% / 100% / 140%; these allowances scale to 60% / 100% / 160%. "
            "Count deliveries reaching the destination within each window, per staged bus. "
            "The last empty return may finish later; its full mileage and time are still charged. "
            "Ridership uses an assumed load, capped by attendance; these are not verified bookings. "
            "Capacity, loading, cost, and conventional emissions factors use the corresponding registry case."
        ).replace("$", r"\$"))
        st.caption(
            f"Factor registry: {factors.registry_version}. Base bus capacity: "
            f"{factors.shuttle_passengers_per_bus.base:g} passengers at {factors.service_load_factor.base:.0%} load; "
            f"electric bus cost allowance: ${factors.shuttle_cost_per_bus_hour.base * ELECTRIC_SERVICE_COST_MULTIPLIER:g}/hour. "
            f"Car emissions: {factors.private_vehicle_co2e_kg_per_mile.base:g} kg CO2e/mi; "
            f"electric bus emissions: {base['electric_kg_per_mile']:.3f} kg CO2e/mi when bus service is modeled."
        )
        st.caption(
            "Bus costs include a 20% allowance for electric leasing and temporary charging. "
            "A 10% mileage allowance covers depot travel; paid time covers both full service windows and any later return "
            "plus one setup hour per active bus. Mid-match standby, if required by the operator, is extra. "
            "These remain planning allowances, not local quotes. Boston, Dallas, Kansas City, and Los Angeles replace "
            "equivalent conventional bus trips; other shuttle actions add service. Cost is the gross service budget."
        )
        if scope.buses:
            st.caption(
                f"Electricity: EPA eGRID2023 {CITY_GRID_REGION[city]} regional proxy, with 2.1 kWh/mi "
                "vehicle use, 90% charging efficiency and an assumed 5% grid delivery loss. "
                "This is annual-average operating accounting, not marginal dispatch or a verified depot tariff. "
                "Conventional service remains a generic vehicle proxy; verify the actual fuel and vehicle type."
            )
            st.markdown(
                f"[EPA regional electricity factors]({EGRID_SOURCE}) · "
                f"[CARB energy-use assumptions]({ENERGY_SOURCE}) · "
                f"[NREL higher energy-use case]({ENERGY_STRESS_SOURCE})"
            )
        st.caption(
            "The CO2e factor-sensitivity range holds base ridership and dispatch fixed, varies car and "
            "conventional-bus factors across the registry range, and uses 1.8-2.84 kWh/mi for electric buses. "
            "It is not a confidence interval and does not establish that the assumed mode shift will occur. "
            "Shifts onto existing rail assume spare capacity and no extra train service; marginal passenger energy is excluded."
        )
        st.caption(
            f"CO2e accounting per match: {_number(base['avoided_car_co2e_kg'], ' kg')} from car trips replaced "
            f"+ {_number(base['baseline_service_co2e_kg'], ' kg')} from replaced conventional service "
            f"- {_number(base['proposed_service_co2e_kg'], ' kg')} from proposed electric service."
        )
        if scope.incentive_per_shifted_rider:
            st.caption((
                f"Travel-credit assumption: {_money(scope.incentive_per_shifted_rider)} per additional rider "
                f"switching from a car; {_money(base['incentive_cost'])} included in base operating cost. "
                "Actual redemption by existing transit riders would add cost without the modeled emissions benefit."
            ).replace("$", r"\$"))
        if scope.incentive_per_service_rider:
            st.caption((
                f"Fare-credit assumption: {_money(scope.incentive_per_service_rider)} per round-trip bus rider; "
                f"{_money(base['incentive_cost'])} included in base operating cost. "
                "Credits apply to existing riders and do not imply car-trip or emissions savings. "
                "The credit per rider stays fixed across scope cases."
            ).replace("$", r"\$"))
        if scope.buses and scope.replaces_existing_service:
            st.write(
                "Fleet-replacement savings require equivalent conventional trips to be displaced, "
                "not extra electric service. Verify baseline vehicle emissions, booked demand, "
                "route distance, vehicle range and charging emissions."
            )
        elif scope.buses:
            st.write(
                f"Minimum car-trip replacement for operating CO2e break-even: {base['minimum_car_shift_share']:.1%} "
                f"of riders; design target: {scope.private_shift_share:.0%}. "
                "Verify actual bookings, route distance, load and charging emissions before dispatch."
            )
        st.markdown(
            "Passengers addressed = attendance x assumed beneficiary share, or bus seats x load x on-time deliveries, "
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
        st.caption("Vehicle manufacturing, construction emissions, fuel supply chains, idling savings, fare revenue, "
                   "and parking revenue are excluded. "
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
            "label": "Recommended: detour improvements" if city_plan.get("additional_recommended_action") else "Recommended first action",
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


def _render_capital_alternative(city: str, artifacts: Mapping[str, Any], match_id: str) -> None:
    if city not in ALTERNATIVES:
        return
    try:
        attendance, inputs, _ = _match_impact_context(city, artifacts, match_id)
        estimate = estimate_capital_alternative(city, attendance, inputs.arrival_window_hours)
    except (KeyError, TypeError, ValueError):
        st.caption("Capital alternative estimate unavailable: match attendance and travel inputs are required.")
        return
    if estimate is None:
        return
    concept = estimate["concept"]
    section_header("High-investment, High-impact alternative")
    st.markdown(f"### {concept.title}")
    st.write(concept.rationale)
    _metric_row([
        (f"{_money(estimate['capital_low'])} - {_money(estimate['capital_high'])}",
         "Estimated capital cost", "scenario", "Fleet, charging, contingency and corridor scope", "amber"),
        (f"{_number(estimate['passengers_low'])} - {_number(estimate['passengers_high'])}",
         "Potential passengers addressed / match", "scenario", "Reserve fleet and event delays included", "teal"),
    ])
    st.caption("Long-term concept for future events and everyday service; not a funded project or demand forecast.")
    with st.expander("Capital and passenger assumptions"):
        st.write(
            f"Purchase {concept.buses} electric buses: {estimate['active_buses']} in service and "
            f"{estimate['reserve_buses']} held in reserve. Use a 20% spare-to-active fleet planning ratio. "
            f"Assume {concept.cycle_hours:g}-hour round-trip cycles and {inputs.arrival_window_hours:g} hours "
            f"each for arrivals and departures. The low case adds 25% to cycle time "
            f"({estimate['slow_cycles_per_bus']} deliveries per bus); the high case uses "
            f"{estimate['cycles_per_bus']} deliveries. Start buses at boarding points; the first delivery takes "
            "half a cycle, with symmetric outbound/return time. The final empty return can finish after the window. "
            "Use 45 seats at 65%-85% loading, capped at attendance; do not double-count return passengers. "
            "Passenger figures describe potential service coverage, not incremental riders or avoided car trips."
        )
        st.write(
            "Bus purchase allowance: USD 1.3-1.7 million each, plus 20%-40% of fleet cost for charging "
            "and depot work. Add a separate 15%-30% fleet/infrastructure contingency. "
            "Only the vehicle-price range is source-backed; infrastructure, delay and contingency percentages "
            "are planning assumptions. Seated capacity and range require validation, especially for Boston express coaches. "
            "Counts assume sufficient drivers, loading bays and charging between service windows."
        )
        st.markdown(f"[Spare-fleet context: FTA]({SPARE_FLEET_SOURCE})")
        st.dataframe(pd.DataFrame([
            {"Cost component": label, "Low ($)": estimate[f"{key}_low"], "High ($)": estimate[f"{key}_high"]}
            for key, label in (
                ("fleet", "Purchased fleet"), ("infrastructure", "Charging and depot allowance"),
                ("contingency", "Fleet/infrastructure contingency"), ("corridor", "Corridor allowance"),
                ("capital", "Total"),
            )
        ]), hide_index=True, width="stretch", column_config={
            "Low ($)": st.column_config.NumberColumn(format="$%,.0f"),
            "High ($)": st.column_config.NumberColumn(format="$%,.0f"),
        })
        st.markdown(f"[Bus-cost reference: California State Auditor]({BUS_COST_SOURCE})")
        if concept.corridor_miles:
            st.write(
                f"Assume {concept.corridor_miles:g} corridor miles at USD 10-25 million per mile, "
                "plus the fleet and charging allowance above. Length is a scenario, not a surveyed alignment. "
                "The corridor allowance covers road conversion, stations and signal priority; it is an analyst "
                "assumption informed by conceptual BRT budgets, not a local quote or a direct cost transfer. "
                "Major land acquisition, tunneling and elevated structures are excluded."
            )
            st.markdown(f"[BRT cost context: Raleigh major investment study]({BRT_COST_SOURCE})")
        st.caption(
            "Reference-price USD (2025-26); no future escalation or financing model. Operating costs, maintenance, "
            "replacement batteries and lifecycle emissions are excluded. Validate year-round demand, "
            "agency plans, land availability and procurement costs before advancing."
        )


def _render_transit_solution_tab(
    city: str,
    artifacts: dict[str, Any],
    match: Any,
    recommendations: tuple[Any, ...],
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

    additional_action = city_plan.get("additional_recommended_action")
    section_header("Recommended actions" if additional_action else "Recommended first action")
    if city_plan.get("recommended_action"):
        with st.container(border=True):
            st.markdown(f"### {city_plan['recommended_action']}")
            why = city_plan.get("why_this_action") or city_plan.get("rationale") or city_plan.get("specific_problem")
            if why:
                st.markdown("**Why this action**")
                st.write(why.replace("$", r"\$"))
        if additional_action:
            with st.container(border=True):
                st.markdown(f"### {additional_action}")
                if additional_why := city_plan.get("additional_rationale"):
                    st.markdown("**Why this action**")
                    st.write(additional_why.replace("$", r"\$"))
                if source := city_plan.get("additional_source_url"):
                    st.caption(f"[Published transit operating plan]({source})")
    else:
        callout("warning", "No curated action plan yet", f"No hand-authored recommendation exists for {city}.")

    if city_plan.get("recommended_action"):
        _render_recommended_action_impact(city, artifacts, str(match.match_id))

    focus_points = RECOMMENDATION_FOCUS_POINTS.get(city, ())
    if city_plan.get("recommended_action") and focus_points:
        venue_context = HOST_CITIES.get(city, {})
        venue = {"name": match.venue, "lat": venue_context.get("lat"), "lon": venue_context.get("lon")}
        figure = recommendation_focus_map(venue, focus_points)
        add_road_controls(figure, artifacts.get("road_closures", {}).get(city, []))
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False},
            key="transit_solution_map",
        )
        named = ", ".join(str(point.get("name")) for point in focus_points)
        st.caption(
            f"The real place(s) this recommendation names: {named}. This is independently-verified geography, "
            "not an engineered route or an approved operating plan."
        )
        _road_control_sources(artifacts.get("road_closures", {}).get(city, []))

    _render_capital_alternative(city, artifacts, str(match.match_id))

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
            st.caption("Separate national screening models, not the recommended action or capital concept shown above.")
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


def _road_control_sources(records: list[dict[str, Any]]) -> None:
    if not records:
        return
    st.caption(
        "Red: documented vehicle closures. Amber: restricted vehicle access. "
        "Published 2026 event plans, not live status; only verified segments are mapped. "
        "Road alignment: OpenStreetMap contributors (ODbL)."
    )
    for url, publisher in sorted({(row["source_url"], row["publisher"]) for row in records}):
        st.caption(f"[Road-control source: {publisher}]({url})")


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
    roads = artifacts.get("road_closures", {}).get(city, [])
    if roads:
        venue = HOST_CITIES.get(city, {})
        st.plotly_chart(
            road_controls_map({**venue, "name": venue.get("venue")}, roads),
            width="stretch", config={"displayModeBar": False}, key=f"road_controls_{city}",
        )
        _road_control_sources(roads)
    elif hotspots:
        st.caption("Vehicle-closure boundaries are not mapped for this city; the documented controls below still apply.")
    if not hotspots:
        callout(
            "warning",
            "No documented congestion hotspots found yet",
            f"No real, cited reporting on match-day road closures or congestion control points was found for {city}.",
        )
        return

    rows = []
    for item in hotspots:
        url = str(item.get("source_url") or "")
        source = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">Open source</a>' if url.startswith("https://") else "Not available"
        rows.append(
            f"<tr><td>{escape(str(item.get('location') or ''))}</td>"
            f"<td>{escape(str(item.get('control') or ''))}</td><td>{source}</td></tr>"
        )
    st.markdown(
        "<table class='traffic-controls-table'><thead><tr><th scope='col'>Location</th>"
        "<th scope='col'>What happens here</th><th scope='col'>Source</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>", unsafe_allow_html=True,
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
    recommendations = decision.recommendation_set(match.match_id)
    city_plan = CITY_ACTION_PLANS.get(city, {})

    page_header(
        "City action plan",
        city,
        match.venue,
        meta=(
            f"Readiness rank #{int(row['strict_rank'])} of {int(comparison['strict_rank'].notna().sum())}"
            if pd.notna(row["strict_rank"]) else "Readiness rank unavailable",
        ),
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
        lambda: _render_transit_solution_tab(city, artifacts, match, recommendations, city_plan),
        lambda: _render_traffic_management_tab(city, artifacts),
    )
    for tab, renderer in zip(tabs, renderers):
        if tab.open:
            with tab:
                renderer()
