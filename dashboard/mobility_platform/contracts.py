"""Stable data contracts shared by ETL, models, UI, and tests."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

try:
    from enum import StrEnum
except ImportError:  # Python 3.8-3.10 preview compatibility
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value


CONTRACT_VERSION = "0.2.0"


class EvidenceStatus(StrEnum):
    OBSERVED = "observed"
    DERIVED = "derived"
    PARTIAL = "partial"
    ESTIMATED = "estimated"
    UNAVAILABLE = "unavailable"
    SCENARIO = "scenario"


@dataclass(frozen=True)
class EvidenceMetric:
    value: float | int | str | None
    unit: str
    status: EvidenceStatus
    source: str
    coverage_start: date | str | None = None
    coverage_end: date | str | None = None
    sample_size: int | None = None
    uncertainty_low: float | None = None
    uncertainty_high: float | None = None
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["assumptions"] = list(self.assumptions)
        return data


@dataclass(frozen=True)
class DataManifest:
    dataset: str
    source_root: str
    expected_partitions: int
    discovered_partitions: int
    rows_read: int
    rows_written: int
    generated_at_utc: str
    source_version: str | None = None
    coverage_start: str | None = None
    coverage_end: str | None = None
    artifact_path: str | None = None
    artifact_sha256: str | None = None
    status: EvidenceStatus = EvidenceStatus.OBSERVED
    warnings: tuple[str, ...] = field(default_factory=tuple)
    quality: DataQualityReport | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["warnings"] = list(self.warnings)
        data["quality"] = self.quality.to_dict() if self.quality else None
        return data


@dataclass(frozen=True)
class DataQualityReport:
    generated_at_utc: str
    checks: tuple[dict[str, Any], ...]
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    rows_read: int = 0
    coverage_start: str | None = None
    coverage_end: str | None = None

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CityMetrics:
    city: str
    venue: str
    state: str
    score: float | None
    score_status: EvidenceStatus
    rankable: bool
    transit_score: float | None
    heat_score: float | None
    uhi_score: float | None
    accessibility_score: float | None
    first_last_mile_gap: float | None
    peak_visitors: int | None
    games: int
    data_coverage: float
    evidence: dict[str, EvidenceMetric] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["score_status"] = self.score_status.value
        data["evidence"] = {key: metric.to_dict() for key, metric in self.evidence.items()}
        return data


@dataclass(frozen=True)
class ScenarioConfig:
    city: str
    shuttle_buses_per_hour: int = 10
    shuttle_hours: float = 6.0
    bike_stations: int = 5
    park_ride_spaces: int = 2000
    pedestrian_upgrade_pct: int = 20
    average_trip_km_round_trip: float = 25.0
    average_vehicle_occupancy: float = 2.2
    vehicle_emissions_kg_per_km: float = 0.21
    bus_capacity: int = 50
    uptake_rate: float = 0.70

    def __post_init__(self) -> None:
        nonnegative = {
            "shuttle_buses_per_hour": self.shuttle_buses_per_hour,
            "shuttle_hours": self.shuttle_hours,
            "bike_stations": self.bike_stations,
            "park_ride_spaces": self.park_ride_spaces,
            "pedestrian_upgrade_pct": self.pedestrian_upgrade_pct,
            "average_trip_km_round_trip": self.average_trip_km_round_trip,
            "bus_capacity": self.bus_capacity,
        }
        invalid = [name for name, value in nonnegative.items() if value < 0]
        if invalid:
            raise ValueError(f"Scenario values must be nonnegative: {', '.join(invalid)}")
        if self.average_vehicle_occupancy <= 0:
            raise ValueError("average_vehicle_occupancy must be greater than zero")
        if not 0 <= self.vehicle_emissions_kg_per_km:
            raise ValueError("vehicle_emissions_kg_per_km must be nonnegative")
        if not 0 <= self.uptake_rate <= 1:
            raise ValueError("uptake_rate must be between zero and one")


@dataclass(frozen=True)
class ScenarioResult:
    config: ScenarioConfig
    transit_capacity_added: int
    potential_mode_shift: int
    residual_vehicle_trips: int
    vehicle_km_avoided: float
    emissions_avoided_kg: float
    capital_cost: float
    operating_cost_per_match: float
    status: EvidenceStatus = EvidenceStatus.SCENARIO
    assumptions: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data
