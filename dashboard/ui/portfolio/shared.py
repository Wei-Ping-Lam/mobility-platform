"""Small presentation utilities shared by Portfolio objective modules."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.domain.decision_support import build_custom_intervention_outcome
from dashboard.domain.scoring import DEFAULT_WEIGHTS, normalize_weights
from dashboard.mobility_platform.contracts import InterventionPackage
from dashboard.mobility_platform.sources import RICE_COLLECTION
from dashboard.models.demand import validation_metrics
from dashboard.ui.theme import metric_card


@st.cache_data(show_spinner=False)
def _cached_validation_metrics(visits: pd.DataFrame) -> pd.DataFrame:
    """Cache the 2-year rolling holdout so every slider drag doesn't recompute it."""

    return validation_metrics(visits)

MetricItem = tuple[str, str, str, str, str]

# Session-state keys shared between app.py (resolves weights before metrics are
# built) and render_weight_settings (renders the interactive widgets inside the
# Overview tab). Keeping the settings widgets inside a tab means app.py must
# read last-run values from session_state before this run's tab renders.
WEIGHT_PROFILE_KEY = "weight_profile"
WEIGHT_FIELD_KEYS = {
    "transit": "weight_transit",
    "heat": "weight_heat",
    "uhi": "weight_uhi",
    "access": "weight_access",
}
INCLUDE_ESTIMATES_KEY = "include_estimates"


def resolve_weight_settings() -> tuple[dict[str, float], bool]:
    """Read the current weight profile/sliders from session_state.

    Called from app.py before metrics are built, so it must work even before
    render_weight_settings has ever executed (fresh session): falls back to
    the "balanced" profile's defaults, exactly what the widgets below
    initialize to on their first render.
    """

    profile = st.session_state.get(WEIGHT_PROFILE_KEY, "balanced")
    if profile not in DEFAULT_WEIGHTS:
        profile = "balanced"
    defaults = dict(DEFAULT_WEIGHTS[profile])
    weights = {
        field: float(st.session_state.get(key, defaults[field]))
        for field, key in WEIGHT_FIELD_KEYS.items()
    }
    include_estimates = bool(st.session_state.get(INCLUDE_ESTIMATES_KEY, False))
    return normalize_weights(weights), include_estimates


def render_weight_settings() -> None:
    """Render the interactive weight-profile controls (moved here from the sidebar)."""

    profile_labels = {
        "balanced": "Balanced mobility",
        "transit_access": "Transit and access",
        "heat_resilience": "Heat resilience",
        "sustainability": "Sustainability",
        "rice_supplied_data": "Rice supplied-data lens",
    }
    profile_options = list(DEFAULT_WEIGHTS)

    def _reset_to_profile() -> None:
        profile = st.session_state.get(WEIGHT_PROFILE_KEY, "balanced")
        defaults = dict(DEFAULT_WEIGHTS.get(profile, DEFAULT_WEIGHTS["balanced"]))
        for field, key in WEIGHT_FIELD_KEYS.items():
            st.session_state[key] = float(defaults[field])

    st.session_state.setdefault(WEIGHT_PROFILE_KEY, "balanced")
    for field, key in WEIGHT_FIELD_KEYS.items():
        st.session_state.setdefault(key, float(DEFAULT_WEIGHTS["balanced"][field]))

    with st.expander("Advanced comparison settings", expanded=False):
        profile = st.selectbox(
            "Weight profile",
            profile_options,
            format_func=profile_labels.get,
            key=WEIGHT_PROFILE_KEY,
            on_change=_reset_to_profile,
        )
        st.caption("Readiness gives the high-level orientation; task-specific evidence below should drive decisions.")
        st.markdown("##### Tune score weights")
        st.slider("Transit", 0.0, 1.0, step=0.05, key=WEIGHT_FIELD_KEYS["transit"])
        st.slider("Heat safety", 0.0, 1.0, step=0.05, key=WEIGHT_FIELD_KEYS["heat"])
        st.slider("UHI safety", 0.0, 1.0, step=0.05, key=WEIGHT_FIELD_KEYS["uhi"])
        st.slider("Venue support", 0.0, 1.0, step=0.05, key=WEIGHT_FIELD_KEYS["access"])
        if profile == "rice_supplied_data":
            st.caption(
                f"This lens uses only {RICE_COLLECTION} weather, UHI, and venue-support evidence; "
                "it does not score transit service."
            )
        st.checkbox(
            "Include estimated values",
            key=INCLUDE_ESTIMATES_KEY,
            help="Strict mode excludes estimated components from rankings. Enable this only for sensitivity exploration.",
        )


def number(value: Any, suffix: str = "", decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "Not available"
    return f"{float(value):,.{decimals}f}{suffix}"


def metric_grid(items: list[MetricItem]) -> None:
    for start in range(0, len(items), 2):
        for column, item in zip(st.columns(2), items[start : start + 2]):
            value, label, status, note, accent = item
            with column:
                st.markdown(
                    metric_card(
                        value,
                        label,
                        status,
                        note=note,
                        accent=accent,
                    ),
                    unsafe_allow_html=True,
                )


def navigate(workspace: str, city: str | None = None) -> None:
    st.session_state["workspace"] = workspace
    if city:
        st.session_state["city_focus"] = city
        st.session_state["selected_city_context"] = city


def evaluate_custom_package(
    city: str,
    match_id: str,
    metrics: pd.DataFrame,
    artifacts: Mapping[str, Any],
    *,
    shuttle_buses_per_hour: float = 0.0,
    bike_hub_spaces: float = 0.0,
    park_ride_spaces: float = 0.0,
    park_ride_feeder_departures_per_hour: float = 0.0,
    cooled_walkway_km: float = 0.0,
) -> dict[str, Any] | None:
    """Live-evaluate a slider-driven InterventionPackage against the real model.

    Unlike the two named packages (Operational/Capital), this scenario is built
    fresh from whatever lever values the UI passes in, then run through the
    same evaluate_intervention() equation used everywhere else in this app -
    it is not a fabricated formula, just a different (custom) input package.
    """

    package = InterventionPackage(
        name="Custom Scenario",
        shuttle_buses_per_hour=int(round(shuttle_buses_per_hour)),
        bike_hub_spaces=int(round(bike_hub_spaces)),
        park_ride_spaces=int(round(park_ride_spaces)),
        park_ride_feeder_departures_per_hour=int(round(park_ride_feeder_departures_per_hour)),
        cooled_walkway_km=round(float(cooled_walkway_km), 2),
    )
    validation = _cached_validation_metrics(artifacts.get("visits", pd.DataFrame()))
    return build_custom_intervention_outcome(
        city, match_id, package, metrics, artifacts, validation=validation
    )
