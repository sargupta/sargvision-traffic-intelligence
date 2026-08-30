"""Event engine — a deterministic state machine. No LLM.

    NORMAL → ELEVATED → ACTIVE → RESOLVED

A single abnormal reading is not an event. Persistence is required, and exit uses
hysteresis so a corridor hovering at the threshold does not flap.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from packages.analytics.anomalies import SILIGURI, Thresholds
from packages.domain.models import EventState

SAMPLES_TO_ACTIVATE = 2


@dataclass
class CorridorTracker:
    corridor_id: str
    state: EventState = EventState.NORMAL
    consecutive: int = 0
    started_hour: int | None = None
    peak_deviation: float = 0.0
    transitions: list[tuple[str, int, float]] = field(default_factory=list)

    def observe(self, deviation_pct: float, hour: int, t: Thresholds = SILIGURI) -> str | None:
        previous = self.state
        self.peak_deviation = max(self.peak_deviation, deviation_pct)

        if deviation_pct >= t.moderate:
            self.consecutive += 1
            if self.state is EventState.NORMAL:
                self.state, self.started_hour = EventState.ELEVATED, hour
            elif self.state is EventState.ELEVATED and self.consecutive >= SAMPLES_TO_ACTIVATE:
                self.state = EventState.ACTIVE
        elif deviation_pct < t.resolve:
            if self.state in (EventState.ELEVATED, EventState.ACTIVE):
                self.state = EventState.RESOLVED
            self.consecutive = 0
        # between resolve and moderate: hold state (hysteresis band)

        if self.state is not previous:
            label = f"{previous.value}->{self.state.value}"
            self.transitions.append((label, hour, self.peak_deviation))
            if self.state is EventState.RESOLVED:
                self.state = EventState.NORMAL
                self.started_hour, self.peak_deviation, self.consecutive = None, 0.0, 0
            return label
        return None

    @property
    def duration_hours(self) -> int:
        return 0 if self.started_hour is None else max(0, self.started_hour)
