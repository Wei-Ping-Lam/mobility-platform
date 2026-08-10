"""Concise, time-phased city traffic strategy presentation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.viz.strategy_overlap import access_overlap_map, operating_overlap_map


def _actions(plan: Mapping[str, Any]) -> pd.DataFrame:
    rows = []
    for action in plan.get("actions", []):
        rows.append(
            {
                "Phase": action.get("phase"),
                "Action": action.get("title"),
                "When": action.get("time_window"),
                "Where": action.get("location") or "Not location-specific",
                "Instruction": action.get("instruction"),
                "Evidence": action.get("evidence_status"),
            }
        )
    return pd.DataFrame(rows)


def render(
    plan: Mapping[str, Any],
    venue: Mapping[str, Any],
    *,
    map_layers: Mapping[str, Any] | None = None,
    published_plan: Mapping[str, Any] | None = None,
) -> None:
    """Render the decision summary first and keep audit detail collapsible."""

    with st.container(border=True):
        status = str(plan.get("status") or "scenario").upper()
        strength = str(plan.get("prediction_strength") or "limited").upper()
        agreement = str(plan.get("benchmark_agreement") or "not benchmarked").upper()
        st.caption(f"ENGINE STRATEGY · {status} · {strength} RULE · {agreement}")
        st.markdown(
            f"### {plan.get('predicted_pattern') or plan.get('primary_pattern', 'Strategy unavailable')}"
        )
        st.write(plan.get("summary") or "No strategy summary is available.")
        benchmark = plan.get("benchmark_pattern")
        source_url = plan.get("benchmark_source_url")
        if benchmark and source_url:
            st.markdown(
                f"Official benchmark: [{benchmark}]({source_url}) · "
                f"{plan.get('benchmark_evidence_level') or 'evidence level unavailable'}"
            )

    bus_range = (
        f"{number(plan.get('required_buses_per_hour_low'))} · "
        f"{number(plan.get('required_buses_per_hour_base'))} · "
        f"{number(plan.get('required_buses_per_hour_high'))}"
    )
    hub_status = str(plan.get("regional_hub_status") or "unavailable")
    hub_evidence = {
        "published": "observed",
        "candidate": "partial",
    }.get(hub_status, "unavailable")
    metric_grid(
        [
            (
                str(plan.get("regional_hub_name") or "Site not established"),
                "Transfer hub",
                hub_evidence,
                "Published means official; candidate means event-valid GTFS evidence only",
                "blue",
            ),
            (
                bus_range,
                "Bus equivalents / hr — low · base · high",
                "scenario",
                str(plan.get("single_hub_feasibility") or "Feasibility unavailable"),
                "amber",
            ),
        ]
    )

    st.markdown("#### Five actions, in operating order")
    st.dataframe(
        _actions(plan),
        hide_index=True,
        width="stretch",
        height=252,
        column_config={
            "Instruction": st.column_config.TextColumn(width="large"),
            "Action": st.column_config.TextColumn(width="medium"),
        },
    )
    st.caption(
        "This is decision support, not an approved traffic-engineering plan. The full residual-gap scale screen is distinct from the bounded first investment shown below. Validate fleet, curb and layover throughput, staffing, ADA paths, emergency access, and enforcement before activation."
    )

    with st.expander("Why the engine selected this strategy", icon=":material/rule:"):
        reasons = list(plan.get("prediction_reasons", []))
        if reasons:
            st.markdown("\n".join(f"- {reason}" for reason in reasons))
        st.caption(
            "The official benchmark is withheld from the classifier and compared afterward. Rule strength is not a probability."
        )

    with st.expander("Overlap maps, controls, and evidence gaps", icon=":material/map:"):
        access_tab, operating_tab = st.tabs(["Venue access overlap", "Operating overlap"])
        with access_tab:
            st.plotly_chart(
                access_overlap_map(venue, map_layers or {}),
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption(
                "Overlap of the half-mile scheduled-service screen, event-valid GTFS routes and stops, and available walking geometry. Presence on the map does not prove capacity, accessibility, or match-day operation."
            )
        with operating_tab:
            st.plotly_chart(
                operating_overlap_map(plan, venue, published_plan),
                width="stretch",
                config={"displayModeBar": False},
            )
            st.caption(
                "Published hubs are blue; engine candidate hubs are amber. Connector lines show the strategy structure only; they are not routed shuttle paths or approved traffic controls."
            )
        controls = list(plan.get("published_controls", []))
        if controls:
            st.markdown("**Published controls retained from the official plan**")
            st.markdown("\n".join(f"- {item}" for item in controls))
        else:
            st.info("No published road closure or traffic-control overlay is integrated for this city.")
        gaps = list(plan.get("evidence_gaps", []))
        if gaps:
            st.markdown("**Evidence still required**")
            st.markdown("\n".join(f"- {item}" for item in gaps))
