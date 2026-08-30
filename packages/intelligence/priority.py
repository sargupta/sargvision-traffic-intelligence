"""Operational priority — a different question from severity.

    Severity  = how abnormal is this?
    Priority  = how much attention does it deserve?

              = Magnitude x Persistence x Corridor Importance

A +35% delay lasting 45 minutes on a critical corridor outranks a +70% spike lasting
5 minutes on a minor one. Deviation alone cannot express that, which is why the two
are separate quantities.
"""
from __future__ import annotations

import numpy as np

from packages.domain.models import CorridorImportance, Priority

MAGNITUDE_REFERENCE = 60.0   # the CRITICAL threshold
MAGNITUDE_CEILING = 2.0      # a +120% event is not four times as urgent as +30%


def magnitude_factor(deviation_pct: float) -> float:
    return float(np.clip(deviation_pct / MAGNITUDE_REFERENCE, 0.0, MAGNITUDE_CEILING))


def persistence_factor(minutes: float) -> float:
    """Ladder: 5 min monitor, 20 min event, 45 min high priority."""
    if minutes >= 45:
        return 2.0
    if minutes >= 20:
        return 1.5
    if minutes >= 10:
        return 1.0
    return 0.4


def importance_factor(importance: CorridorImportance) -> float:
    return {
        CorridorImportance.CRITICAL: 2.0,
        CorridorImportance.HIGH: 1.5,
        CorridorImportance.NORMAL: 1.0,
        CorridorImportance.LOW: 0.6,
    }[importance]


def score(
    deviation_pct: float,
    duration_minutes: float,
    importance: CorridorImportance = CorridorImportance.NORMAL,
) -> tuple[float, Priority]:
    value = (
        magnitude_factor(deviation_pct)
        * persistence_factor(duration_minutes)
        * importance_factor(importance)
    )
    if value >= 3.0:
        band = Priority.P1
    elif value >= 1.8:
        band = Priority.P2
    elif value >= 0.9:
        band = Priority.P3
    else:
        band = Priority.P4
    return round(value, 2), band
