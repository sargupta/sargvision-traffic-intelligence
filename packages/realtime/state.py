"""The current state of Siliguri mobility, and how it is calculated.

Nothing here is a colour or a mood. A movement's status is a number compared
against thresholds that were calibrated on Siliguri's own observations, and
every field the interface shows can be traced back to arithmetic on this page.

    deviation = (observed pace - expected pace) / expected pace

Pace, not journey time: a live sample carries its own distance, and the
expected figure has to be for a journey of *that* length or the comparison is
measuring geography. This is the same correction the historical baselines
needed — see packages/analytics/baselines.
"""

from __future__ import annotations

import statistics
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from packages.providers.live import Sample

# Calibrated on the Siliguri 2019 distribution, not copied from a generic table.
# These are configuration and must be recalibrated for any other city.
NORMAL, MODERATE, HIGH, CRITICAL = 0.0, 30.0, 45.0, 60.0
RESOLVE = 20.0            # hysteresis: leave a state below this, not at entry
WINDOW = timedelta(hours=2)
MIN_FOR_TREND = 4


class Status(str, Enum):
    NORMAL = "NORMAL"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"      # no baseline — we cannot say, and we say so


def classify(deviation_pct: float) -> Status:
    if deviation_pct >= CRITICAL:
        return Status.CRITICAL
    if deviation_pct >= HIGH:
        return Status.HIGH
    if deviation_pct >= MODERATE:
        return Status.MODERATE
    return Status.NORMAL


@dataclass
class Baseline:
    """What this movement normally does at this hour on this kind of day."""

    median_pace: float
    p25_pace: float
    p75_pace: float
    p90_pace: float
    sample_size: int
    confidence: str

    def expected_seconds(self, distance_m: float) -> float:
        return self.median_pace * distance_m / 1000

    def normal_range_seconds(self, distance_m: float) -> tuple[float, float]:
        return (
            self.p25_pace * distance_m / 1000,
            self.p75_pace * distance_m / 1000,
        )


@dataclass
class Reading:
    at: datetime
    traffic_seconds: float
    distance_m: float
    pace: float
    deviation_pct: float | None
    status: Status


@dataclass
class MovementState:
    movement_id: str
    name: str
    origin_zone: str
    dest_zone: str
    origin_name: str = ""
    dest_name: str = ""
    readings: deque[Reading] = field(default_factory=lambda: deque(maxlen=240))
    status: Status = Status.UNKNOWN
    since: datetime | None = None      # when the current status began

    # ── current values ───────────────────────────────────────────────────────
    @property
    def latest(self) -> Reading | None:
        return self.readings[-1] if self.readings else None

    @property
    def deviation_pct(self) -> float | None:
        return self.latest.deviation_pct if self.latest else None

    def window(self, now: datetime, span: timedelta = WINDOW) -> list[Reading]:
        return [r for r in self.readings if r.at >= now - span]

    # ── derived signals ──────────────────────────────────────────────────────
    def persistence_minutes(self, now: datetime) -> float:
        """How long the current non-normal status has held, unbroken."""
        if self.status in (Status.NORMAL, Status.UNKNOWN) or self.since is None:
            return 0.0
        return (now - self.since).total_seconds() / 60

    def velocity(self, now: datetime, span: timedelta = timedelta(minutes=30)) -> float | None:
        """Deterioration rate: percentage points of deviation per 10 minutes.

        A least-squares slope over the recent window rather than a difference
        between two readings, so one noisy sample cannot manufacture an alarm.
        """
        pts = [r for r in self.window(now, span) if r.deviation_pct is not None]
        if len(pts) < MIN_FOR_TREND:
            return None
        t0 = pts[0].at
        xs = [(r.at - t0).total_seconds() / 600 for r in pts]
        ys = [r.deviation_pct for r in pts]
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        denom = sum((x - mx) ** 2 for x in xs)
        if denom == 0:
            return None
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / denom

    def variability(self, now: datetime, span: timedelta = WINDOW) -> float | None:
        """Coefficient of variation of pace across the window, as a percentage."""
        pts = [r.pace for r in self.window(now, span)]
        if len(pts) < MIN_FOR_TREND:
            return None
        mean = statistics.fmean(pts)
        if mean == 0:
            return None
        return statistics.pstdev(pts) / mean * 100

    # ── ingestion ────────────────────────────────────────────────────────────
    def observe(self, sample: Sample, baseline: Baseline | None) -> Reading:
        pace = sample.traffic_seconds / (sample.distance_m / 1000)
        deviation = None
        status = Status.UNKNOWN
        if baseline is not None and baseline.median_pace > 0:
            deviation = (pace - baseline.median_pace) / baseline.median_pace * 100
            status = classify(deviation)
            # Hysteresis: do not drop out of an elevated state the moment the
            # deviation dips under the entry threshold, or the feed flickers.
            if (
                self.status not in (Status.NORMAL, Status.UNKNOWN)
                and status is Status.NORMAL
                and deviation > RESOLVE
            ):
                status = self.status

        reading = Reading(
            at=sample.observed_at,
            traffic_seconds=sample.traffic_seconds,
            distance_m=sample.distance_m,
            pace=pace,
            deviation_pct=deviation,
            status=status,
        )
        if status is not self.status:
            self.status = status
            self.since = sample.observed_at
        self.readings.append(reading)
        return reading


@dataclass
class CityState:
    movements: dict[str, MovementState] = field(default_factory=dict)
    zone_names: dict[str, str] = field(default_factory=dict)
    updated_at: datetime | None = None
    mode: str = "HISTORICAL_REPLAY"
    is_live: bool = False

    def counts(self) -> dict[str, int]:
        out = {s.value: 0 for s in Status}
        for m in self.movements.values():
            out[m.status.value] += 1
        return out

    def elevated(self) -> list[MovementState]:
        return [
            m
            for m in self.movements.values()
            if m.status in (Status.MODERATE, Status.HIGH, Status.CRITICAL)
        ]

    def headline(self) -> str:
        """The line the application opens with. Derived, never written."""
        counts = self.counts()
        bad = counts["CRITICAL"] + counts["HIGH"]
        moderate = counts["MODERATE"]
        if bad == 0 and moderate == 0:
            return "Siliguri mobility is operating within expected conditions."
        parts = []
        if bad:
            parts.append(f"{bad} movement{'s' if bad > 1 else ''} well above expected travel time")
        if moderate:
            parts.append(f"{moderate} moderately elevated")
        return "; ".join(parts).capitalize() + "."
