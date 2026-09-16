from streamlit.testing.v1 import AppTest

from dashboard.mobility_platform.config import ProjectPaths
from dashboard.ui import session_data


def _paths(tmp_path):
    return ProjectPaths(tmp_path, None, tmp_path / "cache")


def test_navigation_reuses_decoded_data_without_polluting_source(tmp_path, monkeypatch):
    state = {}
    calls = []
    source = {"visits": [1, 2, 3]}
    monkeypatch.setattr(session_data.st, "session_state", state)
    monkeypatch.setattr(session_data, "_load_decoded_artifacts", lambda *args: calls.append(args) or source)

    first = session_data.session_artifacts(_paths(tmp_path))
    first["computed_bundle"] = True
    state["_metrics_bundle_cache"] = "keep"
    second = session_data.session_artifacts(_paths(tmp_path))

    assert len(calls) == 1
    assert first["visits"] is second["visits"]
    assert "computed_bundle" not in second
    assert state["_metrics_bundle_cache"] == "keep"


def test_changed_snapshot_invalidates_all_derived_results(tmp_path, monkeypatch):
    paths = _paths(tmp_path)
    paths.artifact_root.mkdir()
    snapshot = paths.artifact_root / "manifest.json"
    snapshot.write_text("{}", encoding="utf-8")
    state = {}
    calls = []
    monkeypatch.setattr(session_data.st, "session_state", state)
    monkeypatch.setattr(session_data, "_load_decoded_artifacts", lambda *args: calls.append(args) or {})
    session_data.session_artifacts(paths)
    for key in session_data._DERIVED_KEYS:
        state[key] = "stale"

    snapshot.write_text('{"updated": true}', encoding="utf-8")
    session_data.session_artifacts(paths)

    assert len(calls) == 2
    assert all(key not in state for key in session_data._DERIVED_KEYS)


def test_revision_detects_added_and_deleted_sources(tmp_path):
    paths = _paths(tmp_path)
    before = session_data.artifact_revision(paths)
    paths.artifact_root.mkdir()
    snapshot = paths.artifact_root / "map_layers.json"
    snapshot.write_text("{}", encoding="utf-8")
    assert session_data.artifact_revision(paths) != before
    snapshot.unlink()
    assert session_data.artifact_revision(paths) == before


def test_different_sessions_do_not_share_mutable_decoded_data(tmp_path, monkeypatch):
    monkeypatch.setattr(session_data, "_load_decoded_artifacts", lambda *args: {"values": []})
    monkeypatch.setattr(session_data.st, "session_state", {})
    first = session_data.session_artifacts(_paths(tmp_path))
    first["values"].append("first session")
    monkeypatch.setattr(session_data.st, "session_state", {})
    second = session_data.session_artifacts(_paths(tmp_path))
    assert second["values"] == []


def test_weight_changes_refresh_scores_but_reuse_source_data():
    app = AppTest.from_file("dashboard/app.py").run(timeout=60)
    assert not app.exception
    decoded = app.session_state["_decoded_artifacts"][1]
    original = app.session_state["_metrics_bundle_cache"][1]["score"].copy()

    next(slider for slider in app.slider if slider.label == "Traffic management").set_value(0.40)
    app.run(timeout=60)
    assert not app.exception
    assert app.session_state["_decoded_artifacts"][1] is decoded
    assert not app.session_state["_metrics_bundle_cache"][1]["score"].equals(original)

    next(slider for slider in app.slider if slider.label == "Traffic management").set_value(0.30)
    app.run(timeout=60)
    assert not app.exception
    assert app.session_state["_metrics_bundle_cache"][1]["score"].equals(original)
