"""Compatibility entry point for the modular Portfolio page."""

from dashboard.ui.portfolio.page import render_portfolio

render_home = render_portfolio

__all__ = ["render_home"]
