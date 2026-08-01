"""Plotly styling and semantic palettes shared by every dashboard view."""

from __future__ import annotations

import plotly.graph_objects as go

COLORS = {
    "ink": "#16302f",
    "muted": "#637873",
    "line": "#dce6e2",
    "grid": "#e8efec",
    "teal": "#0b7169",
    "teal_light": "#7bb9af",
    "blue": "#356b9a",
    "amber": "#a96512",
    "coral": "#b9533a",
    "violet": "#71569a",
    "slate": "#6c7b78",
    "surface": "#ffffff",
}

STATUS_COLORS = {
    "observed": "#0b7169",
    "derived": "#356b9a",
    "partial": "#b47418",
    "estimated": "#b9533a",
    "scenario": "#71569a",
    "unavailable": "#87938f",
}

READINESS_SCALE = [
    [0.0, "#e4eeeb"],
    [0.45, "#90c2b9"],
    [0.72, "#3f9389"],
    [1.0, "#075f59"],
]

SERIES_COLORS = {
    "observed": "#447f7a",
    "baseline": "#356b9a",
    "scenario": "#bd7022",
    "scenario_fill": "rgba(189, 112, 34, .14)",
}


def style_figure(
    fig: go.Figure,
    height: int = 360,
    *,
    legend: bool = True,
    margin: dict[str, int] | None = None,
) -> go.Figure:
    """Apply consistent typography, spacing, grids, and hover treatments."""

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter, Aptos, "Segoe UI", sans-serif', color=COLORS["ink"], size=12),
        colorway=[COLORS["teal"], COLORS["blue"], COLORS["amber"], COLORS["violet"], COLORS["coral"]],
        height=height,
        margin=margin or dict(l=18, r=18, t=34, b=26),
        hoverlabel=dict(bgcolor=COLORS["ink"], bordercolor=COLORS["ink"], font_color="#ffffff"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color=COLORS["muted"]),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=legend,
    )
    fig.update_xaxes(
        gridcolor=COLORS["grid"],
        linecolor=COLORS["line"],
        tickfont=dict(color=COLORS["muted"]),
        title_font=dict(color=COLORS["muted"], size=12),
        zeroline=False,
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor=COLORS["grid"],
        linecolor=COLORS["line"],
        tickfont=dict(color=COLORS["muted"]),
        title_font=dict(color=COLORS["muted"], size=12),
        zeroline=False,
        automargin=True,
    )
    return fig


def style_map(fig: go.Figure, height: int = 500, *, zoom: float, lat: float, lon: float) -> go.Figure:
    """Use one light basemap and layout treatment for every venue map."""

    fig.update_layout(
        template="plotly_white",
        mapbox=dict(style="carto-positron", zoom=zoom, center={"lat": lat, "lon": lon}),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family='Inter, Aptos, "Segoe UI", sans-serif', color=COLORS["ink"], size=12),
        hoverlabel=dict(bgcolor=COLORS["ink"], bordercolor=COLORS["ink"], font_color="#ffffff"),
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=.01,
            xanchor="left",
            x=.01,
            bgcolor="rgba(255,255,255,.88)",
            bordercolor=COLORS["line"],
            borderwidth=1,
            font=dict(size=10, color=COLORS["ink"]),
        ),
    )
    return fig


def discrete_status_scale(statuses: list[str]) -> tuple[list[list[object]], dict[str, int]]:
    """Build a Plotly colorscale with one stable band per evidence status."""

    normalized = [status if status in STATUS_COLORS else "unavailable" for status in statuses]
    mapping = {status: index for index, status in enumerate(normalized)}
    if len(normalized) == 1:
        color = STATUS_COLORS[normalized[0]]
        return [[0.0, color], [1.0, color]], mapping
    scale: list[list[object]] = []
    maximum = len(normalized) - 1
    for index, status in enumerate(normalized):
        start = max(0.0, (index - .49) / maximum)
        end = min(1.0, (index + .49) / maximum)
        scale.extend([[start, STATUS_COLORS[status]], [end, STATUS_COLORS[status]]])
    return scale, mapping
