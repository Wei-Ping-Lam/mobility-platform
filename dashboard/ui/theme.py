"""Cohesive visual language and reusable HTML primitives for the dashboard."""

from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st

_VALID_STATUSES = {"observed", "derived", "partial", "estimated", "unavailable", "scenario"}
_VALID_ACCENTS = {"teal", "blue", "amber", "coral", "violet", "slate"}


def _status_class(status: str | None) -> str:
    normalized = str(status or "unavailable").strip().lower()
    return normalized if normalized in _VALID_STATUSES else "unavailable"


def apply_theme() -> None:
    """Apply the platform's civic-analytics design system."""

    st.markdown(
        """
        <style>
        :root {
            color-scheme: light;
            --canvas: #f3f6f4;
            --surface: #ffffff;
            --surface-soft: #edf4f1;
            --ink: #16302f;
            --ink-soft: #536a67;
            --line: #d9e4df;
            --teal: #0b7169;
            --teal-deep: #0a3436;
            --blue: #356b9a;
            --amber: #a96512;
            --coral: #b9533a;
            --violet: #71569a;
            --slate: #6c7b78;
            --shadow: 0 12px 34px rgba(28, 60, 55, .07);
        }

        html, body, [class*="css"] {
            font-family: Inter, Aptos, "Segoe UI", system-ui, -apple-system, sans-serif;
        }
        body { color: var(--ink); }
        [data-testid="stAppViewContainer"], .stApp {
            background:
                radial-gradient(circle at 82% -12%, rgba(102, 180, 164, .12), transparent 28rem),
                var(--canvas);
            color: var(--ink);
        }
        [data-testid="stHeader"] {
            background: rgba(243, 246, 244, .88);
            border-bottom: 1px solid rgba(217, 228, 223, .78);
            backdrop-filter: blur(12px);
        }
        [data-testid="stDecoration"] { display: none; }
        [data-testid="stToolbar"] { right: 1rem; }
        .block-container {
            max-width: 1480px;
            padding: 2.35rem 3rem 5rem;
        }
        h1, h2, h3, h4, h5, h6 {
            color: var(--ink);
            font-weight: 720;
            letter-spacing: -.035em;
        }
        h1 { font-size: clamp(2rem, 3vw, 3.35rem); line-height: 1.05; }
        h2 { font-size: 1.5rem; }
        h3, h4 { letter-spacing: -.02em; }
        p, li { color: var(--ink-soft); line-height: 1.62; }
        hr { border-color: var(--line) !important; }
        a { color: var(--teal); }

        /* Navigation rail */
        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 8% 8%, rgba(76, 164, 148, .2), transparent 15rem),
                var(--teal-deep);
            border-right: 0;
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.35rem; }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span { color: #eef8f5; }
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #a9c4bf; }
        [data-testid="stSidebar"] hr { border-color: rgba(222, 241, 236, .15) !important; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] .stNumberInput input {
            background: rgba(255, 255, 255, .08);
            border-color: rgba(219, 238, 233, .2);
            color: #f5fbf9;
            border-radius: 10px;
        }
        [data-testid="stSidebar"] [role="radiogroup"] { gap: .35rem; }
        [data-testid="stSidebar"] [role="radiogroup"] label {
            border: 1px solid transparent;
            border-radius: 10px;
            padding: .42rem .55rem;
            transition: background .15s ease, border-color .15s ease;
        }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: rgba(255, 255, 255, .08);
            border-color: rgba(255, 255, 255, .1);
        }
        [data-testid="stSidebar"] [data-testid="stExpander"] {
            background: rgba(255, 255, 255, .055);
            border: 1px solid rgba(219, 238, 233, .14);
            border-radius: 12px;
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: .8rem;
            margin: .1rem 0 .4rem;
        }
        .brand-mark {
            display: grid;
            place-items: center;
            width: 2.65rem;
            height: 2.65rem;
            border-radius: 12px;
            background: #d7f06a;
            color: #123532;
            font-size: .78rem;
            font-weight: 850;
            letter-spacing: -.03em;
            box-shadow: 0 8px 20px rgba(0, 0, 0, .15);
        }
        .brand-name { color: #f5fbf9; font-size: 1rem; font-weight: 750; line-height: 1.15; }
        .brand-sub { color: #9fbbb6; font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; margin-top: .18rem; }
        .sidebar-kicker {
            color: #86aaa4;
            font-size: .66rem;
            font-weight: 750;
            letter-spacing: .12em;
            margin: 1.4rem 0 .2rem;
            text-transform: uppercase;
        }
        .sidebar-health {
            border: 1px solid rgba(219, 238, 233, .14);
            border-radius: 12px;
            background: rgba(255, 255, 255, .055);
            padding: .8rem .85rem;
            margin-top: .7rem;
        }
        .sidebar-health strong { display: block; color: #eff8f5; font-size: .79rem; }
        .sidebar-health span { display: block; color: #9fbbb6 !important; font-size: .7rem; line-height: 1.45; margin-top: .22rem; }

        /* Page hierarchy */
        .hero-shell {
            position: relative;
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 22px;
            background: linear-gradient(132deg, #ffffff 0%, #f4faf7 62%, #edf6f2 100%);
            box-shadow: var(--shadow);
            padding: clamp(1.4rem, 2.8vw, 2.45rem);
            margin: .15rem 0 1.35rem;
        }
        .hero-shell::after {
            content: "";
            position: absolute;
            width: 18rem;
            height: 18rem;
            right: -7rem;
            top: -9rem;
            border: 1px solid rgba(11, 113, 105, .13);
            border-radius: 50%;
            box-shadow: 0 0 0 2.8rem rgba(11, 113, 105, .025), 0 0 0 5.6rem rgba(11, 113, 105, .018);
        }
        .hero-kicker, .section-kicker {
            color: var(--teal);
            font-size: .68rem;
            font-weight: 800;
            letter-spacing: .14em;
            text-transform: uppercase;
        }
        .hero-title {
            position: relative;
            z-index: 1;
            color: var(--ink);
            font-size: clamp(2rem, 3.2vw, 3.25rem);
            font-weight: 760;
            letter-spacing: -.052em;
            line-height: 1.04;
            max-width: 56rem;
            margin: .5rem 0 .65rem;
        }
        .hero-copy {
            position: relative;
            z-index: 1;
            color: var(--ink-soft);
            font-size: .98rem;
            line-height: 1.6;
            max-width: 54rem;
            margin: 0;
        }
        .hero-meta { display: flex; flex-wrap: wrap; gap: .45rem; margin-top: 1.15rem; position: relative; z-index: 1; }
        .meta-chip {
            border: 1px solid #cfe0d9;
            border-radius: 999px;
            background: rgba(255, 255, 255, .76);
            color: #45615d;
            font-size: .69rem;
            font-weight: 700;
            padding: .35rem .62rem;
        }
        .section-head { margin: 2.2rem 0 .82rem; }
        .section-title { color: var(--ink); font-size: 1.16rem; font-weight: 760; letter-spacing: -.025em; margin-top: .23rem; }
        .section-copy { color: var(--ink-soft); font-size: .8rem; line-height: 1.5; max-width: 52rem; margin-top: .2rem; }

        /* Cards and evidence semantics */
        .metric-card {
            position: relative;
            height: 100%;
            min-height: 8.2rem;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 16px;
            box-shadow: 0 7px 22px rgba(24, 56, 51, .045);
            padding: 1.05rem 1.1rem .95rem;
        }
        .metric-card::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            border-radius: 16px 0 0 16px;
            background: var(--teal);
        }
        .metric-card.accent-blue::before { background: var(--blue); }
        .metric-card.accent-amber::before { background: var(--amber); }
        .metric-card.accent-coral::before { background: var(--coral); }
        .metric-card.accent-violet::before { background: var(--violet); }
        .metric-card.accent-slate::before { background: var(--slate); }
        .metric-value { color: var(--ink); font-size: clamp(1.55rem, 2vw, 2.05rem); font-weight: 770; letter-spacing: -.045em; line-height: 1.05; }
        .metric-label { color: var(--ink-soft); font-size: .72rem; font-weight: 700; letter-spacing: .025em; margin-top: .48rem; }
        .metric-note { color: #738682; font-size: .65rem; line-height: 1.35; margin-top: .38rem; }
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: .34rem;
            border-radius: 999px;
            font-size: .62rem;
            font-weight: 800;
            letter-spacing: .055em;
            line-height: 1;
            padding: .32rem .5rem;
            text-transform: uppercase;
            white-space: nowrap;
        }
        .status-dot { width: .38rem; height: .38rem; border-radius: 50%; background: currentColor; }
        .status-observed { color: #086e5b; background: #e1f3ed; }
        .status-derived { color: #2f6497; background: #e6eff8; }
        .status-partial { color: #91580c; background: #fff0d8; }
        .status-estimated { color: #a14831; background: #fbe8e2; }
        .status-scenario { color: #684c91; background: #eee9f7; }
        .status-unavailable { color: #637370; background: #e9eeec; }
        .metric-card .status-badge { margin-top: .62rem; }

        .callout {
            display: grid;
            grid-template-columns: .35rem 1fr;
            gap: .8rem;
            border: 1px solid var(--line);
            border-radius: 13px;
            background: #fff;
            padding: .85rem 1rem;
            margin: .65rem 0 1rem;
        }
        .callout-bar { border-radius: 999px; background: var(--blue); }
        .callout.warning .callout-bar { background: var(--amber); }
        .callout.success .callout-bar { background: var(--teal); }
        .callout.error .callout-bar { background: var(--coral); }
        .callout-title { color: var(--ink); font-size: .78rem; font-weight: 760; }
        .callout-body { color: var(--ink-soft); font-size: .74rem; line-height: 1.5; margin-top: .16rem; }

        .priority-card {
            min-height: 9.4rem;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: #fff;
            padding: 1rem 1.05rem;
            box-shadow: 0 7px 22px rgba(24, 56, 51, .04);
        }
        .priority-city { color: var(--teal); font-size: .68rem; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
        .priority-title { color: var(--ink); font-size: .96rem; font-weight: 760; margin-top: .35rem; }
        .priority-copy { color: var(--ink-soft); font-size: .72rem; line-height: 1.48; margin-top: .35rem; }

        .evidence-list { display: grid; gap: .48rem; }
        .evidence-row {
            display: grid;
            grid-template-columns: minmax(7rem, .7fr) auto minmax(10rem, 1.45fr);
            align-items: center;
            gap: .75rem;
            border-bottom: 1px solid #e5ece9;
            padding: .72rem .1rem;
        }
        .evidence-row:last-child { border-bottom: 0; }
        .evidence-name { color: var(--ink); font-size: .76rem; font-weight: 740; }
        .evidence-source { color: var(--ink-soft); font-size: .69rem; line-height: 1.35; text-align: right; }

        /* Streamlit components */
        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"] {
            overflow: hidden;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--surface);
            box-shadow: 0 7px 22px rgba(24, 56, 51, .04);
            padding: .28rem;
        }
        [data-testid="stAlert"] {
            border-radius: 13px;
            border-width: 1px;
            box-shadow: none;
        }
        [data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 13px;
            background: rgba(255, 255, 255, .64);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: .25rem;
            border-bottom: 1px solid var(--line);
        }
        .stTabs button[data-baseweb="tab"] {
            color: #617470;
            font-size: .78rem;
            font-weight: 720;
            padding: .75rem .95rem;
        }
        .stTabs button[data-baseweb="tab"][aria-selected="true"] { color: var(--teal); }
        .stTabs [data-baseweb="tab-highlight"] { background-color: var(--teal); }
        .stButton > button,
        .stDownloadButton > button {
            min-height: 2.65rem;
            border: 1px solid #a9c4bd;
            border-radius: 11px;
            background: #fff;
            color: var(--teal-deep);
            font-weight: 730;
            transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
        }
        .stButton > button:hover,
        .stDownloadButton > button:hover {
            border-color: var(--teal);
            color: var(--teal);
            box-shadow: 0 6px 16px rgba(11, 113, 105, .09);
            transform: translateY(-1px);
        }
        [data-baseweb="slider"] [role="slider"] { background-color: var(--teal); }
        [data-testid="stCheckbox"] svg { color: var(--teal); }
        code { border-radius: 8px; }

        @media (max-width: 1000px) {
            .block-container { padding: 1.7rem 1.35rem 4rem; }
            .evidence-row { grid-template-columns: 1fr auto; }
            .evidence-source { grid-column: 1 / -1; text-align: left; }
        }
        @media (max-width: 640px) {
            .block-container { padding: 1.2rem .85rem 3rem; }
            .hero-shell { border-radius: 17px; padding: 1.25rem 1.05rem; }
            .hero-title { font-size: 2rem; }
            .hero-copy { font-size: .86rem; }
            .metric-card { min-height: 7.3rem; }
            .section-head { margin-top: 1.65rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def status_badge(status: str, label: str | None = None) -> str:
    """Return an accessible status badge that uses text as well as color."""

    status_class = _status_class(status)
    display = escape(label or status_class.replace("_", " ").title())
    return (
        f"<span class='status-badge status-{status_class}'>"
        f"<span class='status-dot' aria-hidden='true'></span>{display}</span>"
    )


def metric_card(
    value: str,
    label: str,
    status: str | None = None,
    *,
    note: str | None = None,
    accent: str = "teal",
) -> str:
    accent_class = accent if accent in _VALID_ACCENTS else "teal"
    badge = status_badge(status) if status else ""
    note_html = f"<div class='metric-note'>{escape(note)}</div>" if note else ""
    return (
        f"<div class='metric-card accent-{accent_class}'>"
        f"<div class='metric-value'>{escape(str(value))}</div>"
        f"<div class='metric-label'>{escape(label)}</div>{note_html}{badge}</div>"
    )


def page_header(kicker: str, title: str, description: str, meta: Iterable[str] = ()) -> None:
    chips = "".join(f"<span class='meta-chip'>{escape(str(item))}</span>" for item in meta)
    meta_html = f"<div class='hero-meta'>{chips}</div>" if chips else ""
    st.markdown(
        f"<section class='hero-shell'>"
        f"<div class='hero-kicker'>{escape(kicker)}</div>"
        f"<div class='hero-title'>{escape(title)}</div>"
        f"<p class='hero-copy'>{escape(description)}</p>{meta_html}</section>",
        unsafe_allow_html=True,
    )


def section_header(title: str, description: str | None = None, kicker: str | None = None) -> None:
    kicker_html = f"<div class='section-kicker'>{escape(kicker)}</div>" if kicker else ""
    copy_html = f"<div class='section-copy'>{escape(description)}</div>" if description else ""
    st.markdown(
        f"<div class='section-head'>{kicker_html}<div class='section-title'>{escape(title)}</div>{copy_html}</div>",
        unsafe_allow_html=True,
    )


def callout(kind: str, title: str, body: str) -> None:
    callout_kind = kind if kind in {"info", "warning", "success", "error"} else "info"
    st.markdown(
        f"<div class='callout {callout_kind}'><div class='callout-bar'></div><div>"
        f"<div class='callout-title'>{escape(title)}</div>"
        f"<div class='callout-body'>{escape(body)}</div></div></div>",
        unsafe_allow_html=True,
    )


def priority_card(city: str, title: str, body: str, status: str) -> str:
    return (
        "<div class='priority-card'>"
        f"<div class='priority-city'>{escape(city)}</div>"
        f"<div class='priority-title'>{escape(title)}</div>"
        f"<div class='priority-copy'>{escape(body)}</div>"
        f"<div style='margin-top:.65rem'>{status_badge(status)}</div></div>"
    )


def evidence_row(name: str, status: str, source: str) -> str:
    return (
        "<div class='evidence-row'>"
        f"<div class='evidence-name'>{escape(name)}</div>{status_badge(status)}"
        f"<div class='evidence-source'>{escape(source)}</div></div>"
    )


def brand_block() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-mark">M26</div>
            <div>
                <div class="brand-name">Mobility Readiness</div>
                <div class="brand-sub">Host city decision studio</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_status(title: str, detail: str) -> None:
    st.markdown(
        f"<div class='sidebar-health'><strong>{escape(title)}</strong><span>{escape(detail)}</span></div>",
        unsafe_allow_html=True,
    )


def status_label(status: str) -> str:
    """Backward-compatible alias for status badges."""

    return status_badge(status)
