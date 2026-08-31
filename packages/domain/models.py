"""Domain entities. No I/O, no framework, no dataframes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Severity(str, Enum):
    """How abnormal is it? Calibrated against Siliguri observations."""

    EXPECTED = "EXPECTED"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Priority(str, Enum):
    """How much attention does it deserve? Not the same question as severity."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class EventState(str, Enum):
    NORMAL = "NORMAL"
    ELEVATED = "ELEVATED"
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


class CorridorImportance(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class DayType(str, Enum):
    WEEKDAY = "WEEKDAY"
    WEEKEND = "WEEKEND"


@dataclass(frozen=True)
class Corridor:
    corridor_id: str
    name: str
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    importance: CorridorImportance = CorridorImportance.NORMAL
    note: str | None = None


@dataclass(frozen=True)
class Observation:
    corridor_id: str
    observed_at: datetime
    traffic_seconds: int
    freeflow_seconds: int
    distance_m: int

    @property
    def delay_seconds(self) -> int:
        return self.traffic_seconds - self.freeflow_seconds

    @property
    def travel_time_index(self) -> float:
        return self.traffic_seconds / self.freeflow_seconds if self.freeflow_seconds else 0.0

    @property
    def speed_kmh(self) -> float:
        return (
            (self.distance_m / 1000) / (self.traffic_seconds / 3600)
            if self.traffic_seconds
            else 0.0
        )


@dataclass(frozen=True)
class Baseline:
    corridor_id: str
    day_type: DayType
    hour: int
    median_seconds: float
    p25_seconds: float
    p75_seconds: float
    p90_seconds: float
    sample_size: int


@dataclass
class TrafficEvent:
    corridor_id: str
    state: EventState
    started_at: datetime
    peak_deviation_pct: float
    severity: Severity
    priority: Priority
    priority_score: float
    duration_minutes: float
    resolved_at: datetime | None = None
