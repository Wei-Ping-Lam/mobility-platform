"""All-city comparison with strict rankings separated from screening evidence."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.domain.comparison import build_city_comparison
from dashboard.ui.theme import callout, page_header, section_header
from dashboard.viz.style import COLORS, style_figure


def _screening_interval_chart(frame: pd.DataFrame) -> go.Figure:
    chart = frame.sort_values("screening_score")
    figure = go.Figure()
    for _, row in chart.iterrows():
        figure.add_trace(
            go.Scatter(
                x=[row["screening_low"], row["screening_high"]],
                y=[row["city"], row["city"]],
                mode="lines",
                line=dict(color=COLORS["line"], width=8),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    colors = {"high": COLORS["teal"], "medium": COLORS["blue"], "low": COLORS["amber"], "insufficient": COLORS["slate"]}
    for confidence, subset in chart.groupby("screening_confidence"):
        figure.add_trace(
            go.Scatter(
                x=subset["screening_score"],
                y=subset["city"],
                mode="markers",
                marker=dict(size=12, color=colors.get(confidence, COLORS["slate"]), line=dict(color="white", width=1)),
                name=f"{confidence.title()} confidence",
                customdata=subset[["screening_low", "screening_high", "screening_limitations"]],
                hovertemplate="Screening score: %{x:.1f}<br>Evidence range: %{customdata[0]:.1f}–%{customdata[1]:.1f}<br>%{customdata[2]}<extra></extra>",
            )
        )
    figure.update_xaxes(range=[0, 100], title="Screening score and evidence-eligibility range (0–100)")
    return style_figure(figure, 470)


def render_compare_cities(metrics: pd.DataFrame, artifacts: dict, weights: dict[str, float]) -> None:
    comparison = build_city_comparison(
        metrics,
        artifacts.get("access_gaps", []),
        artifacts.get("investment_recommendations", []),
        weights=weights,
    )
    strict_count = int(comparison["strict_rankable"].sum())
    page_header(
        "Compare cities",
        "One honest portfolio view for all 11 hosts",
        "Strict transportation ranks use only eligible evidence. The screening view keeps every city visible and bounds partial or missing components instead of silently converting them to zero.",
        (f"{len(comparison)} cities screened", f"{strict_count} strictly rankable", "Partial is not zero"),
    )
    strict_tab, screening_tab, access_tab = st.tabs(["Strict comparison", "All-city screening", "Match access portfolio"])
    with strict_tab:
        section_header("Capacity- and evidence-qualified ranking", "Only cities whose selected score components are observed or derived receive an ordinal rank.", "Strict")
        strict = comparison[comparison["strict_rankable"]].copy()
        if strict.empty:
            callout("warning", "No cities are strictly rankable", "Use the screening table to understand which evidence blocks qualification.")
        else:
            display = strict[["strict_rank", "city", "strict_score", "qualified_matches", "capacity_qualified_gap_pph", "top_intervention", "top_evidence"]].copy()
            display.columns = ["Rank", "City", "MRS", "Qualified matches", "Representative access gap (pph)", "Match-specific Pareto option", "Evidence"]
            st.dataframe(display, hide_index=True, width="stretch")
        with st.expander("Why other cities are not strictly rankable", expanded=True):
            excluded = comparison[~comparison["strict_rankable"]][["city", "strict_exclusion_reason", "qualified_matches", "partial_matches", "unavailable_matches"]].copy()
            excluded.columns = ["City", "Exact exclusion reason", "Qualified matches", "Partial matches", "Unavailable matches"]
            st.dataframe(excluded, hide_index=True, width="stretch")

    with screening_tab:
        section_header("All-city evidence screening", "The dot is the available numeric evidence. The line is the conservative 0–100 range for components that are not strictly eligible; it is not a statistical confidence interval.", "All cities")
        st.plotly_chart(_screening_interval_chart(comparison), width="stretch", config={"displayModeBar": False})
        display = comparison[["screening_order", "city", "screening_score", "screening_low", "screening_high", "screening_confidence", "screening_numeric_coverage", "screening_limitations"]].copy()
        display.columns = ["Screening order", "City", "Available-evidence score", "Evidence low", "Evidence high", "Confidence", "Numeric coverage", "Limitations"]
        st.dataframe(display, hide_index=True, width="stretch")
        callout("info", "Screening order is not a strict rank", "It supports prioritization and data collection across all cities while preserving uncertainty. Cite the strict rank only where the Rank column exists.")

    with access_tab:
        section_header("Match access portfolio", "Compare the physical demand and capacity-qualified gap before interpreting any normalized index.", "Transportation")
        chart = comparison.sort_values("peak_demand_pph", ascending=True)
        figure = go.Figure()
        figure.add_trace(go.Bar(y=chart["city"], x=chart["peak_demand_pph"], orientation="h", name="Peak demand scenario", marker_color=COLORS["blue"]))
        figure.add_trace(go.Bar(y=chart["city"], x=chart["capacity_qualified_gap_pph"], orientation="h", name="Capacity-qualified gap", marker_color=COLORS["coral"]))
        figure.update_layout(barmode="group")
        figure.update_xaxes(title="Passengers per hour")
        st.plotly_chart(style_figure(figure, 470), width="stretch", config={"displayModeBar": False})
        display = comparison[["city", "representative_match_id", "peak_demand_pph", "capacity_qualified_gap_pph", "qualified_matches", "partial_matches", "unavailable_matches", "top_intervention", "top_cost_per_passenger", "top_net_co2e_kg", "top_lead_time"]].copy()
        display.columns = ["City", "Representative match", "Peak demand (pph)", "Qualified gap (pph)", "Qualified matches", "Partial matches", "Unavailable matches", "Pareto option", "Cost/passenger", "Net CO2e (kg)", "Lead time"]
        st.dataframe(display, hide_index=True, width="stretch")

    st.download_button("Download exact all-city comparison CSV", comparison.to_csv(index=False), file_name="all-city-mobility-comparison.csv", mime="text/csv", width="stretch")
