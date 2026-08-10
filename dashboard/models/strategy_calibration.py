"""Transparent host-city strategy-family calibration.

The classifier intentionally uses only evidence available to the generated
model: scheduled-service coverage, stop proximity, network walking evidence,
regional-hub structure, and transit-network scale.  Official World Cup plans
are held outside this module and used only as post-prediction benchmarks.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import inf
from typing import Any, Mapping, Sequence

from dashboard.mobility_platform.contracts import AccessGapResult

DIRECT_HIGH_CAPACITY = "Direct high-capacity transit reinforcement"
DOWNTOWN_DISPERSAL = "Downtown multimodal dispersal"
DIRECT_DISTRIBUTED_EGRESS = "Direct transit plus distributed egress"
MULTIMODAL_TRANSFER = "Multimodal rail-transfer network"
DISTRIBUTED_EXPRESS = "Distributed express bus and rail"
MULTI_HUB_SHUTTLE = "Multi-hub stadium shuttle"
REGIONAL_RAIL_BRIDGE = "Regional rail to charter-bus bridge"
CAPACITY_MANAGED_RAIL = "Capacity-managed rail plus shuttle"
PARK_RIDE_HYBRID = "Park-and-ride and shuttle hybrid"
DEDICATED_SHUTTLE = "Dedicated event shuttle staging"

STRATEGY_FAMILIES = (
    DIRECT_HIGH_CAPACITY,
    DOWNTOWN_DISPERSAL,
    DIRECT_DISTRIBUTED_EGRESS,
    MULTIMODAL_TRANSFER,
    DISTRIBUTED_EXPRESS,
    MULTI_HUB_SHUTTLE,
    REGIONAL_RAIL_BRIDGE,
    CAPACITY_MANAGED_RAIL,
    PARK_RIDE_HYBRID,
    DEDICATED_SHUTTLE,
)


@dataclass(frozen=True)
class StrategyFeatures:
    """Auditable features used by the strategy-family classifier."""

    scheduled_coverage: float
    nearest_stop_mi: float | None
    stops_half_mile: int
    transit_score: float | None
    route_count: int
    regional_hub_count: int
    nearest_regional_hub_mi: float | None
    rail_hub_count: int
    maximum_hub_routes: int
    network_walk_distance_m: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyPrediction:
    """One independently generated strategy family with an explanation."""

    family: str
    strength: str
    reasons: tuple[str, ...]
    features: StrategyFeatures

    def __post_init__(self) -> None:
        if self.family not in STRATEGY_FAMILIES:
            raise ValueError(f"Unsupported strategy family: {self.family}")
        if self.strength not in {"strong", "moderate", "limited"}:
            raise ValueError(f"Unsupported prediction strength: {self.strength}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "strength": self.strength,
            "reasons": list(self.reasons),
            "features": self.features.to_dict(),
        }


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed == parsed else None


def _hubs(city_gtfs: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = city_gtfs.get("regional_hubs")
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


def build_strategy_features(
    access: AccessGapResult,
    city_gtfs: Mapping[str, Any],
    walking: Mapping[str, Any],
) -> StrategyFeatures:
    """Build classifier inputs without consulting a published plan or city name."""

    demand = max(float(access.peak_demand_per_hour), 0.0)
    coverage = min(max(float(access.transit_capacity_base) / demand, 0.0), 1.0) if demand else 0.0
    hubs = _hubs(city_gtfs)
    distances = [_number(row.get("distance_mi")) for row in hubs]
    distances = [value for value in distances if value is not None]
    rail_hubs = [
        row
        for row in hubs
        if any(
            mode in {"rail", "subway_metro", "tram_light_rail"}
            for mode in row.get("modes", [])
        )
    ]
    route_counts = [int(_number(row.get("route_count")) or 0) for row in hubs]
    walk_distance = _number(access.network_walk_distance_m)
    if walk_distance is None:
        walk_distance = _number(walking.get("network_distance_m"))
    return StrategyFeatures(
        scheduled_coverage=round(coverage, 6),
        nearest_stop_mi=_number(city_gtfs.get("nearest_stop_mi")),
        stops_half_mile=int(_number(city_gtfs.get("stops_0_5mi")) or 0),
        transit_score=_number(city_gtfs.get("gtfs_transit_score")),
        route_count=int(_number(city_gtfs.get("route_count")) or 0),
        regional_hub_count=len(hubs),
        nearest_regional_hub_mi=min(distances) if distances else None,
        rail_hub_count=len(rail_hubs),
        maximum_hub_routes=max(route_counts, default=0),
        network_walk_distance_m=walk_distance,
    )


def classify_strategy(features: StrategyFeatures) -> StrategyPrediction:
    """Classify a strategy family with ordered, documented physical rules.

    Strength is a rule-evidence description, not a calibrated probability.
    Thresholds are planning breakpoints tested against the official host-city
    benchmark; exact operating commitments never come from this classifier.
    """

    coverage = features.scheduled_coverage
    stop = features.nearest_stop_mi if features.nearest_stop_mi is not None else inf
    hub = features.nearest_regional_hub_mi if features.nearest_regional_hub_mi is not None else inf
    walk = features.network_walk_distance_m
    score = features.transit_score or 0.0

    if stop > 2.0 and coverage < 0.10:
        return StrategyPrediction(
            REGIONAL_RAIL_BRIDGE,
            "strong",
            (
                f"Nearest scheduled stop is {stop:.1f} miles from the venue.",
                "Direct event-hour scheduled capacity covers less than 10% of the modeled peak.",
                "A regional rail hub is available, so the missing link is the venue transfer.",
            ),
            features,
        )

    if coverage < 0.08 and walk is None and hub >= 10.0:
        family = DISTRIBUTED_EXPRESS if features.route_count >= 250 else MULTI_HUB_SHUTTLE
        network_reason = (
            "The wider network has enough route diversity to support distributed express origins."
            if family == DISTRIBUTED_EXPRESS
            else "The isolated venue requires several external collection hubs rather than one local transfer."
        )
        return StrategyPrediction(
            family,
            "strong",
            (
                "No validated event-stop walking path is available.",
                f"The nearest high-connectivity regional hub is {hub:.1f} miles from the venue.",
                network_reason,
            ),
            features,
        )

    if (
        coverage < 0.20
        and stop <= 0.20
        and features.route_count <= 30
        and features.maximum_hub_routes >= 7
        and features.rail_hub_count >= 3
    ):
        return StrategyPrediction(
            CAPACITY_MANAGED_RAIL,
            "strong",
            (
                "A rail stop is adjacent to the venue but ordinary scheduled service understates the event requirement.",
                "Multiple high-connectivity regional rail hubs can meter and distribute demand.",
                "The topology supports ticketed rail allocation with supplemental shuttle and curb channels.",
            ),
            features,
        )

    if coverage >= 0.40 and stop <= 0.30 and walk is not None and walk <= 600:
        if walk <= 250 and features.stops_half_mile >= 30:
            return StrategyPrediction(
                DOWNTOWN_DISPERSAL,
                "strong",
                (
                    f"The modeled walk to event service is only {walk:.0f} m.",
                    f"{features.stops_half_mile} stops sit within a half mile of the venue.",
                    "High scheduled coverage supports distributing spectators across walking and transit channels.",
                ),
                features,
            )
        return StrategyPrediction(
            DIRECT_HIGH_CAPACITY,
            "strong",
            (
                f"Scheduled event-hour service covers {coverage:.0%} of the modeled peak.",
                f"The nearest scheduled stop is {stop:.2f} miles away.",
                "The primary action is to protect, lengthen, and manage the direct high-capacity service.",
            ),
            features,
        )

    if coverage >= 0.08 and stop <= 0.25:
        if hub <= 1.5 and features.rail_hub_count >= 3:
            return StrategyPrediction(
                MULTIMODAL_TRANSFER,
                "strong",
                (
                    "Direct stadium-area rail exists but covers less than 40% of the modeled peak.",
                    f"{features.rail_hub_count} regional rail hubs provide transfer paths into the final stadium service.",
                    "The network should coordinate transfer arrivals rather than default to a single shuttle origin.",
                ),
                features,
            )
        return StrategyPrediction(
            DIRECT_DISTRIBUTED_EGRESS,
            "moderate",
            (
                f"A scheduled stop is {stop:.2f} miles from the venue.",
                f"Existing scheduled capacity covers {coverage:.0%} of the modeled peak.",
                "Direct service should remain the trunk while park-and-ride, walking, and egress controls absorb the residual.",
            ),
            features,
        )

    if coverage < 0.08 and score >= 30 and features.route_count >= 80 and hub <= 4.0:
        return StrategyPrediction(
            PARK_RIDE_HYBRID,
            "moderate",
            (
                "Direct scheduled stadium capacity is small relative to the modeled peak.",
                "The wider transit network is substantial and its nearest regional hub is within four miles.",
                "Remote parking and rail/bus shuttle connections should split access across several approaches.",
            ),
            features,
        )

    if coverage < 0.08 and hub < inf and features.regional_hub_count >= 2:
        return StrategyPrediction(
            MULTI_HUB_SHUTTLE,
            "moderate",
            (
                f"Direct scheduled service covers only {coverage:.0%} of the modeled peak.",
                f"{features.regional_hub_count} event-valid regional hubs can distribute loading.",
                "The base bus-equivalent screen should be split across hubs rather than assigned to one curb.",
            ),
            features,
        )

    return StrategyPrediction(
        DEDICATED_SHUTTLE,
        "limited",
        (
            "The available scheduled-service and hub evidence does not support a stronger network-specific pattern.",
            "A staging location, operating plan, and local capacity checks remain required.",
        ),
        features,
    )


def compare_with_benchmark(
    prediction: StrategyPrediction | str,
    benchmark: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Compare a prediction to an analyst-coded official-plan benchmark."""

    row = dict(benchmark or {})
    target = str(row.get("strategy_family") or "")
    if not target:
        return {
            "benchmark_pattern": None,
            "benchmark_agreement": "not benchmarked",
            "benchmark_source_url": None,
            "benchmark_evidence_level": None,
        }
    predicted_family = prediction.family if isinstance(prediction, StrategyPrediction) else str(prediction)
    return {
        "benchmark_pattern": target,
        "benchmark_agreement": "matches" if predicted_family == target else "differs",
        "benchmark_source_url": row.get("source_url"),
        "benchmark_evidence_level": row.get("evidence_level"),
    }


def aggregate_city_predictions(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Choose each city's modal match-level prediction for QA reporting."""

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("city")), []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for city, city_rows in grouped.items():
        counts: dict[str, int] = {}
        for row in city_rows:
            family = str(row.get("predicted_pattern") or row.get("primary_pattern") or "")
            counts[family] = counts.get(family, 0) + 1
        family = sorted(counts, key=lambda value: (-counts[value], value))[0] if counts else ""
        exemplar = next(
            (row for row in city_rows if str(row.get("predicted_pattern") or row.get("primary_pattern")) == family),
            city_rows[0],
        )
        result[city] = {
            "predicted_pattern": family,
            "match_count": len(city_rows),
            "prediction_strength": exemplar.get("prediction_strength"),
            "benchmark_pattern": exemplar.get("benchmark_pattern"),
            "benchmark_agreement": exemplar.get("benchmark_agreement"),
        }
    return result


__all__ = [
    "STRATEGY_FAMILIES",
    "StrategyFeatures",
    "StrategyPrediction",
    "aggregate_city_predictions",
    "build_strategy_features",
    "classify_strategy",
    "compare_with_benchmark",
]
