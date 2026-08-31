"""Canonical data model — Blueprint v2 §10.

These are the stable contracts every provider must produce and every engine consumes.
The intelligence layer must not care where an observation came from.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from packages.domain.models import Severity


class Confidence(str):
    """Confidence is a first-class output, never an afterthought.

    The spike found only 9.5% of spatial units carry usable evidence. Publishing a
    number without its confidence would imply city-wide intelligence the data cannot
    support.
    """

    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"

    @staticmethod
    def from_sample(n: int) -> str:
        if n >= 300:
            return Confidence.HIGH
        if n >= 100:
            return Confidence.MODERATE
        if n >= 30:
            return Confidence.LOW
        return Confidence.INSUFFICIENT

    @staticmethod
    def factor(level: str) -> float:
        """Priority weighting — Blueprint §15 includes a confidence factor."""
        return {"HIGH": 1.0, "MODERATE": 0.8, "LOW": 0.5, "INSUFFICIENT": 0.0}[level]


class BaselineSource(str):
    """Which level of the hierarchy actually produced this baseline.

    Blueprint §12: fallbacks must be visible in metadata. A user must be able to see
    that a figure came from a coarser fallback rather than the preferred unit.
    """

    UNIT_1KM = "UNIT_1KM"
    UNIT_2KM_FALLBACK = "UNIT_2KM_FALLBACK"
    CITY_FALLBACK = "CITY_FALLBACK"
    NONE = "NONE"


@dataclass(frozen=True)
class TrafficObservation:
    """§10 — the canonical observation. Every provider emits this shape."""

    observation_id: str
    source_id: str
    source_type: str
    observed_at: datetime
    trip_id: str
    route_rank: int
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    unit_id: str  # OD zone pair. NOT a segment - see the spike.
    distance_m: int
    traffic_duration_s: int
    free_flow_duration_s: int
    quality_flags: list[str] = field(default_factory=list)

    @property
    def travel_time_ratio(self) -> float:
        return (
            self.traffic_duration_s / self.free_flow_duration_s
            if self.free_flow_duration_s
            else 0.0
        )

    @property
    def delay_s(self) -> int:
        return self.traffic_duration_s - self.free_flow_duration_s

    @property
    def speed_proxy_kmh(self) -> float:
        return (
            (self.distance_m / 1000) / (self.traffic_duration_s / 3600)
            if self.traffic_duration_s
            else 0.0
        )


@dataclass(frozen=True)
class UnitMetric:
    """§10 SegmentMetric, renamed. The spike removed segments; the unit is an OD zone pair."""

    unit_id: str
    time_bucket: str
    observation_count: int
    median_travel_ratio: float
    median_delay_s: float
    p25: float
    p50: float
    p75: float
    baseline_ratio: float | None
    deviation_percent: float | None
    confidence: str
    baseline_source: str


@dataclass(frozen=True)
class TrafficAnomaly:
    """§10 — one abnormal reading. Not yet an event."""

    anomaly_id: str
    unit_id: str
    observed_at: datetime
    metric_name: str
    observed_value: float
    expected_value: float
    deviation_percent: float
    severity: Severity
    confidence: str
    baseline_source: str


@dataclass(frozen=True)
class Investigation:
    """§10 — the assembled evidence behind one event. What the Copilot is handed."""

    investigation_id: str
    event_id: str
    evidence_items: list[dict] = field(default_factory=list)
    historical_matches: list[dict] = field(default_factory=list)
    related_units: list[dict] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    generated_summary: str | None = None

    def __post_init__(self) -> None:
        if not self.limitations:
            raise ValueError(
                "An Investigation must state its limitations. Blueprint §13: the system "
                "distinguishes observation from interpretation from hypothesis."
            )
