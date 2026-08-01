"""Shared visual language for the dashboard."""

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root { color-scheme: dark; }
        [data-testid="stAppViewContainer"] { background: #08111f; }
        [data-testid="stSidebar"] { background: #0d1c2d; border-right: 1px solid #203b59; }
        h1, h2, h3, h4 { letter-spacing: -0.02em; }
        .eyebrow { color: #70c8f7; font-size: .75rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
        .muted { color: #9bb2c8; }
        .metric-card { background: linear-gradient(145deg,#11263b,#0d1b2d); border: 1px solid #254b70; border-radius: 14px; padding: 16px; min-height: 92px; }
        .metric-value { color: #75d4ff; font-size: 1.8rem; font-weight: 800; }
        .metric-label { color: #a8bfd4; font-size: .76rem; text-transform: uppercase; letter-spacing: .08em; }
        .status-observed { color: #63e6a2; font-weight: 700; }
        .status-derived { color: #70c8f7; font-weight: 700; }
        .status-partial { color: #ffd166; font-weight: 700; }
        .status-estimated, .status-scenario { color: #ffb86b; font-weight: 700; }
        .status-unavailable { color: #ff8b8b; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(value: str, label: str, status: str | None = None) -> str:
    badge = f"<div class='status-{status}'>{status}</div>" if status else ""
    return f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div>{badge}</div>"


def status_label(status: str) -> str:
    return f"<span class='status-{status}'>{status}</span>"
