from __future__ import annotations

import copy
import json

import pytest

from dashboard.mobility_platform.mappings import HOST_CITIES
from dashboard.pipeline.public.strategy_benchmarks import DEFAULT_OUTPUT, validate_snapshot


def _snapshot():
    return json.loads(DEFAULT_OUTPUT.read_text(encoding="utf-8"))


def test_checked_strategy_benchmark_is_complete_and_valid() -> None:
    snapshot = _snapshot()
    validate_snapshot(snapshot)
    assert set(snapshot["benchmarks"]) == set(HOST_CITIES)
    assert all(row["source_url"].startswith("https://") for row in snapshot["benchmarks"].values())


def test_strategy_benchmark_rejects_label_or_hash_tampering() -> None:
    snapshot = _snapshot()
    changed = copy.deepcopy(snapshot)
    changed["benchmarks"]["Atlanta"]["strategy_family"] = "Invented family"
    with pytest.raises(ValueError):
        validate_snapshot(changed)
