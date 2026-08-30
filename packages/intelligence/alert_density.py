"""Alert density — a product KPI, not a threshold constant.

Too few alerts and no habit forms, so the product becomes non-essential. Too many and
officers stop reading. The target band is monitored continuously and the thresholds
move to serve it — not the other way round.
"""
from __future__ import annotations

from dataclasses import dataclass

TARGET_MIN, TARGET_MAX = 3.0, 8.0


@dataclass(frozen=True)
class DensityReading:
    threshold_pct: float
    events: int
    days: int

    @property
    def per_day(self) -> float:
        return round(self.events / self.days, 1) if self.days else 0.0

    @property
    def status(self) -> str:
        v = self.per_day
        if v < TARGET_MIN:
            return "TOO FEW - adoption risk"
        if v > TARGET_MAX:
            return "TOO MANY - fatigue risk"
        return "IN TARGET"
