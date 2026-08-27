"""Concise, time-phased city traffic strategy presentation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.ui.portfolio.shared import metric_grid, number
from dashboard.ui.theme import callout
from dashboard.viz.strategy_overlap import operating_overlap_map


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


def _candidate_hubs(rows: object, selected_name: object) -> pd.DataFrame:
    records = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, Mapping) or "no service" in str(row.get("name") or "").casefold():
                continue
            records.append(
                {
                    "Rank": len(records) + 1,
                    "Candidate hub": row.get("name"),
                    "Selected": "Yes" if str(row.get("name")) == str(selected_name) else "",
                    "Distance": f"{number(row.get('distance_mi'), decimals=1)} mi",
                    "Routes": number(row.get("route_count")),
                    "Modes": ", ".join(str(value).replace("_", " ") for value in row.get("modes", [])),
                }
            )
    return pd.DataFrame(records)


def render(
    plan: Mapping[str, Any],
    venue: Mapping[str, Any],
    *,
    hub_candidates: list[Mapping[str, Any]] | None = None,
) -> None:
    """Render the decision summary first and keep audit detail collapsible."""

    with st.container(border=True):
        status = str(plan.get("status") or "scenario").upper()
        strength = str(plan.get("prediction_strength") or "limited").upper()
        st.caption(f"ENGINE STRATEGY · {status} · {strength} RULE")
        st.markdown(
            f"### {plan.get('predicted_pattern') or plan.get('primary_pattern', 'Strategy unavailable')}"
        )
        st.write(plan.get("summary") or "No strategy summary is available.")
        agreement = str(plan.get("benchmark_agreement") or "not benchmarked")
        benchmark_pattern = plan.get("benchmark_pattern")
        benchmark_url = plan.get("benchmark_source_url")
        source_note = f" [Source]({benchmark_url})." if benchmark_url else ""
        if agreement == "matches":
            callout(
                "success",
                "Matches the real, published strategy",
                "This engine-derived pattern agrees with the actual strategy already published for this host."
                + source_note,
            )
        elif agreement == "differs" and benchmark_pattern:
            callout(
                "warning",
                "Differs from the published strategy",
                f'This engine-derived pattern does not match the published strategy for this host, which is "{benchmark_pattern}." Prefer the published strategy where the two disagree.'
                + source_note,
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
                "Highest-ranked candidate from the bounded GTFS connectivity screen; not an approved hub",
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

    st.markdown("#### Planned operating footprint")
    st.plotly_chart(
        operating_overlap_map(plan, venue, hub_candidates or []),
        width="stretch",
        config={"displayModeBar": False},
    )
    st.caption(
        "Amber is the selected engine anchor; blue points are other retained candidates. The line is schematic, not a routed shuttle path or approved traffic control."
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
        st.caption("Rule strength describes evidence coverage; it is not a probability.")

    with st.expander("Hub candidates, screening method, and evidence gaps", icon=":material/checklist:"):
        candidates = _candidate_hubs(hub_candidates or [], plan.get("regional_hub_name"))
        if not candidates.empty:
            st.dataframe(candidates, hide_index=True, width="stretch", height=315)
        st.markdown("**How candidates are screened**")
        st.write(
            "The GTFS screen retains up to eight parent stations between 0.5 and 40 miles from the venue with scheduled service active on at least one host match date. Ranking favors rail or ferry connectivity, more routes, more event-valid trip patterns and match dates, then shorter distance."
        )
        st.caption(
            "This is a bounded network-connectivity shortlist, not an exhaustive list and not an operational feasibility ranking. It does not test parking, curb, platform, layover, staffing, ADA, emergency-access, or special-event capacity."
        )
        gaps = list(plan.get("evidence_gaps", []))
        if gaps:
            st.markdown("**Evidence still required**")
            st.markdown("\n".join(f"- {item}" for item in gaps))
