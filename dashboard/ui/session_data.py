"""Keep decoded artifacts session-local; refresh when offline inputs change."""

from pathlib import Path
from typing import Any

import streamlit as st

from dashboard.mobility_platform.config import ProjectPaths
from dashboard.ui.data import load_artifacts

_SESSION_KEY = "_decoded_artifacts"
_DERIVED_KEYS = ("_metrics_bundle_cache", "_presentation_cache", "_portfolio_frame_cache")


def artifact_revision(paths: ProjectPaths) -> tuple[tuple[str, int, int], ...]:
    """Stat compact input files, not their contents or the raw source tree."""
    files = {paths.repo_root / "data" / "gtfs_transit_scores.json", Path(__file__), Path(__file__).with_name("data.py")}
    for root in (paths.artifact_root, paths.repo_root / "data" / "snapshots"):
        if root.exists():
            files.update(path for path in root.rglob("*") if path.suffix in {".json", ".parquet"})
    stamps = []
    for path in sorted(files):
        try:
            stat = path.stat()
            stamps.append((str(path), stat.st_mtime_ns, stat.st_size))
        except FileNotFoundError:
            stamps.append((str(path), -1, -1))
    return tuple(stamps)


@st.cache_data(show_spinner="Loading verified mobility artifacts...", max_entries=2)
def _load_decoded_artifacts(paths: ProjectPaths, revision: tuple) -> dict[str, Any]:
    return load_artifacts(paths)


def session_artifacts(paths: ProjectPaths) -> dict[str, Any]:
    revision = (paths, artifact_revision(paths))
    cached = st.session_state.get(_SESSION_KEY)
    if cached is None or cached[0] != revision:
        decoded = _load_decoded_artifacts(paths, revision[1])
        for key in _DERIVED_KEYS:
            st.session_state.pop(key, None)
        cached = (revision, decoded)
        st.session_state[_SESSION_KEY] = cached
    # Renderers treat nested source data as read-only. The run-local top-level
    # dictionary lets app.py attach computed outputs without polluting the source.
    return dict(cached[1])
