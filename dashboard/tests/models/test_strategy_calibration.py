from __future__ import annotations

import pytest

from dashboard.models.strategy_calibration import (
    CAPACITY_MANAGED_RAIL,
    DIRECT_DISTRIBUTED_EGRESS,
    DIRECT_HIGH_CAPACITY,
    DISTRIBUTED_EXPRESS,
    DOWNTOWN_DISPERSAL,
    MULTI_HUB_SHUTTLE,
    MULTIMODAL_TRANSFER,
    PARK_RIDE_HYBRID,
    REGIONAL_RAIL_BRIDGE,
    StrategyFeatures,
    classify_strategy,
    compare_with_benchmark,
)


def _features(**changes) -> StrategyFeatures:
    values = {
        "scheduled_coverage": 0.0,
        "nearest_stop_mi": 0.5,
        "stops_half_mile": 2,
        "transit_score": 10,
        "route_count": 40,
        "regional_hub_count": 8,
        "nearest_regional_hub_mi": 6.0,
        "rail_hub_count": 4,
        "maximum_hub_routes": 4,
        "network_walk_distance_m": 900,
    }
    values.update(changes)
    return StrategyFeatures(**values)


@pytest.mark.parametrize(
    ("features", "family"),
    [
        (_features(nearest_stop_mi=5.3, nearest_regional_hub_mi=16.5), REGIONAL_RAIL_BRIDGE),
        (
            _features(
                route_count=405,
                nearest_regional_hub_mi=16.4,
                network_walk_distance_m=None,
            ),
            DISTRIBUTED_EXPRESS,
        ),
        (
            _features(
                route_count=123,
                nearest_regional_hub_mi=11.1,
                network_walk_distance_m=None,
            ),
            MULTI_HUB_SHUTTLE,
        ),
        (
            _features(
                scheduled_coverage=0.04,
                nearest_stop_mi=0.13,
                route_count=17,
                maximum_hub_routes=8,
            ),
            CAPACITY_MANAGED_RAIL,
        ),
        (
            _features(
                scheduled_coverage=0.61,
                nearest_stop_mi=0.10,
                stops_half_mile=25,
                network_walk_distance_m=364,
            ),
            DIRECT_HIGH_CAPACITY,
        ),
        (
            _features(
                scheduled_coverage=0.70,
                nearest_stop_mi=0.12,
                stops_half_mile=62,
                network_walk_distance_m=187,
            ),
            DOWNTOWN_DISPERSAL,
        ),
        (
            _features(
                scheduled_coverage=0.14,
                nearest_stop_mi=0.22,
                nearest_regional_hub_mi=0.54,
                rail_hub_count=8,
            ),
            MULTIMODAL_TRANSFER,
        ),
        (
            _features(
                scheduled_coverage=0.12,
                nearest_stop_mi=0.18,
                nearest_regional_hub_mi=5.8,
            ),
            DIRECT_DISTRIBUTED_EGRESS,
        ),
        (
            _features(
                scheduled_coverage=0.02,
                nearest_stop_mi=0.29,
                transit_score=40,
                route_count=120,
                nearest_regional_hub_mi=2.3,
            ),
            PARK_RIDE_HYBRID,
        ),
    ],
)
def test_strategy_rules_produce_distinct_network_families(
    features: StrategyFeatures,
    family: str,
) -> None:
    prediction = classify_strategy(features)
    assert prediction.family == family
    assert prediction.reasons


def test_benchmark_is_compared_after_prediction() -> None:
    prediction = classify_strategy(
        _features(
            scheduled_coverage=0.61,
            nearest_stop_mi=0.10,
            network_walk_distance_m=364,
        )
    )
    matching = compare_with_benchmark(
        prediction,
        {"strategy_family": DIRECT_HIGH_CAPACITY, "source_url": "https://example.test"},
    )
    conflicting = compare_with_benchmark(
        prediction,
        {"strategy_family": MULTI_HUB_SHUTTLE, "source_url": "https://example.test"},
    )

    assert prediction.family == DIRECT_HIGH_CAPACITY
    assert matching["benchmark_agreement"] == "matches"
    assert conflicting["benchmark_agreement"] == "differs"
