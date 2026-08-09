"""Small presentation utilities shared by Portfolio objective modules."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.ui.theme import metric_card

MetricItem = tuple[str, str, str, str, str]


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
