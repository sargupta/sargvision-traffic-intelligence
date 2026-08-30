"""What the system looks for in the live stream.

Four questions, asked of the state on every tick. Each is deterministic and
each produces evidence a person can check. None of them names a cause: the data
can establish that something changed and roughly how much, and it cannot
establish why, so no detector here is permitted to imply one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from packages.realtime.state import CityState, MovementState, Status

# Calibrated against the Siliguri distribution. Configuration, not constants.
VELOCITY_ALARM = 6.0        # deviation points gained per 10 minutes
PERSISTENCE_ALARM = 20.0    # minutes a movement must hold an elevated state
VARIABILITY_ALARM = 22.0    # coefficient of variation, %
CLUSTER_MIN = 2             # movements sharing a zone before it is a cluster


class Signal(str, Enum):
    DETERIORATION = "DETERIORATION"
    PERSISTENCE = "PERSISTENCE"
    VARIABILITY = "VARIABILITY"
    CLUSTER = "CLUSTER"


@dataclass
class LiveFinding:
    id: str
    signal: Signal
    severity: str
    title: str
    claim: str
    evidence: dict
    movements: list[str]
    zones: list[str]
    detected_at: datetime
    persistence_minutes: float
    confidence: str
    limitation: str
    view: dict = field(default_factory=dict)

    @property
    def priority(self) -> float:
        """Severity × persistence × confidence × breadth.

        Multiplicative, so a severe but momentary blip does not outrank a
        moderate condition that has held for an hour across three movements.
        """
        sev = {"CRITICAL": 1.0, "HIGH": 0.75, "MODERATE": 0.5, "NORMAL": 0.2}.get(self.severity, 0.3)
        conf = {"HIGH": 1.0, "MODERATE": 0.7, "LOW": 0.4}.get(self.confidence, 0.4)
        persist = min(1.0, self.persistence_minutes / 45) if self.persistence_minutes else 0.35
        breadth = min(1.0, 0.5 + 0.25 * len(self.movements))
        return round(sev * conf * persist * breadth, 4)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "signal": self.signal.value,
            "severity": self.severity,
            "title": self.title,
            "claim": self.claim,
            "evidence": self.evidence,
            "movements": self.movements,
            "zones": self.zones,
            "detected_at": self.detected_at.isoformat(timespec="seconds"),
            "persistence_minutes": round(self.persistence_minutes, 1),
            "confidence": self.confidence,
            "limitation": self.limitation,
            "priority": self.priority,
            "view": self.view,
        }


def _confidence(state: MovementState, now: datetime) -> str:
    n = len(state.window(now))
    if n >= 12:
        return "HIGH"
    if n >= 6:
        return "MODERATE"
    return "LOW"


def detect_deterioration(city: CityState, now: datetime) -> list[LiveFinding]:
    """Conditions getting worse quickly, before they have finished getting worse."""
    out = []
    for m in city.movements.values():
        v = m.velocity(now)
        if v is None or v < VELOCITY_ALARM or m.deviation_pct is None:
            continue
        if m.status is Status.NORMAL:
            continue
        out.append(
            LiveFinding(
                id=f"LIVE_DET_{m.movement_id}",
                signal=Signal.DETERIORATION,
                severity=m.status.value,
                title=f"{m.name} is deteriorating",
                claim=(
                    f"{m.name} has gained {v:.0f} points of deviation every 10 minutes and "
                    f"now sits {m.deviation_pct:.0f}% above its expected travel time."
                ),
                evidence={
                    "deviation_pct": round(m.deviation_pct, 1),
                    "velocity_points_per_10min": round(v, 2),
                    "readings_in_window": len(m.window(now)),
                    "latest_minutes": round(m.latest.traffic_seconds / 60, 1) if m.latest else None,
                    "test": "least-squares slope of deviation over the last 30 minutes",
                },
                movements=[m.movement_id],
                zones=sorted({m.origin_zone, m.dest_zone}),
                detected_at=now,
                persistence_minutes=m.persistence_minutes(now),
                confidence=_confidence(m, now),
                limitation=(
                    "A trend over half an hour. It shows the direction conditions are "
                    "moving, not how long they will stay there, and it carries no cause."
                ),
                view={
                    "layout": "map+timeline",
                    "focus_movements": [m.movement_id],
                    "encode": "deviation",
                },
            )
        )
    return out


def detect_persistence(city: CityState, now: datetime) -> list[LiveFinding]:
    """Conditions that are not resolving."""
    out = []
    for m in city.movements.values():
        held = m.persistence_minutes(now)
        if held < PERSISTENCE_ALARM or m.deviation_pct is None:
            continue
        if m.status in (Status.NORMAL, Status.UNKNOWN):
            continue
        out.append(
            LiveFinding(
                id=f"LIVE_PER_{m.movement_id}",
                signal=Signal.PERSISTENCE,
                severity=m.status.value,
                title=f"{m.name} has been elevated for {held:.0f} minutes",
                claim=(
                    f"{m.name} has held a {m.status.value.lower()} condition for "
                    f"{held:.0f} minutes, currently {m.deviation_pct:.0f}% above expected."
                ),
                evidence={
                    "deviation_pct": round(m.deviation_pct, 1),
                    "persistence_minutes": round(held, 1),
                    "readings_in_window": len(m.window(now)),
                    "test": "continuous minutes in a non-normal state, with hysteresis",
                },
                movements=[m.movement_id],
                zones=sorted({m.origin_zone, m.dest_zone}),
                detected_at=now,
                persistence_minutes=held,
                confidence=_confidence(m, now),
                limitation=(
                    "Sustained does not mean worsening, and it does not mean unusual for "
                    "this hour — only that the condition has not cleared."
                ),
                view={
                    "layout": "map+timeline",
                    "focus_movements": [m.movement_id],
                    "encode": "deviation",
                },
            )
        )
    return out


def detect_variability(city: CityState, now: datetime) -> list[LiveFinding]:
    """Conditions that are unstable rather than simply bad."""
    out = []
    for m in city.movements.values():
        cv = m.variability(now)
        if cv is None or cv < VARIABILITY_ALARM:
            continue
        out.append(
            LiveFinding(
                id=f"LIVE_VAR_{m.movement_id}",
                signal=Signal.VARIABILITY,
                severity="MODERATE" if m.status is Status.NORMAL else m.status.value,
                title=f"{m.name} is unstable",
                claim=(
                    f"Travel times on {m.name} are swinging by {cv:.0f}% around their own "
                    "recent average — the movement is not settling at any value."
                ),
                evidence={
                    "coefficient_of_variation_pct": round(cv, 1),
                    "readings_in_window": len(m.window(now)),
                    "deviation_pct": round(m.deviation_pct, 1) if m.deviation_pct is not None else None,
                    "test": "coefficient of variation of pace over 2 hours",
                },
                movements=[m.movement_id],
                zones=sorted({m.origin_zone, m.dest_zone}),
                detected_at=now,
                persistence_minutes=m.persistence_minutes(now),
                confidence=_confidence(m, now),
                limitation=(
                    "Instability can be the road or it can be the sampling. With readings "
                    "minutes apart, a single stopped vehicle can move this number."
                ),
                view={
                    "layout": "timeline",
                    "focus_movements": [m.movement_id],
                    "encode": "variability",
                },
            )
        )
    return out


def detect_clusters(city: CityState, now: datetime) -> list[LiveFinding]:
    """Several movements through the same zone going wrong together.

    This is the finding that is worth more than the sum of its parts, and it is
    also the one most easily over-claimed. The system reports that connected
    movements are elevated at the same time. It does not say a road is blocked,
    because it cannot see roads.
    """
    elevated = city.elevated()
    if len(elevated) < CLUSTER_MIN:
        return []

    by_zone: dict[str, list[MovementState]] = {}
    for m in elevated:
        for z in {m.origin_zone, m.dest_zone}:
            by_zone.setdefault(z, []).append(m)

    out = []
    for zone, members in by_zone.items():
        if len(members) < CLUSTER_MIN:
            continue
        zone_name = city.zone_names.get(zone, zone)
        devs = [m.deviation_pct for m in members if m.deviation_pct is not None]
        if not devs:
            continue
        worst = max(members, key=lambda m: m.deviation_pct or 0)
        held = max(m.persistence_minutes(now) for m in members)
        out.append(
            LiveFinding(
                id=f"LIVE_CLU_{zone}",
                signal=Signal.CLUSTER,
                severity=worst.status.value,
                title=f"{len(members)} movements through {zone_name} are elevated together",
                claim=(
                    f"{len(members)} movements touching {zone_name} are simultaneously above "
                    f"expected travel time, between {min(devs):.0f}% and {max(devs):.0f}%."
                ),
                evidence={
                    "movements_affected": len(members),
                    "deviation_range_pct": [round(min(devs), 1), round(max(devs), 1)],
                    "longest_persistence_minutes": round(held, 1),
                    "test": "co-occurrence of elevated states across movements sharing a zone",
                },
                movements=[m.movement_id for m in members],
                zones=[zone],
                detected_at=now,
                persistence_minutes=held,
                confidence="MODERATE" if len(members) < 3 else "HIGH",
                limitation=(
                    "Co-occurrence is not causation and these movements may share no road "
                    "at all — they share a zone. The system is reporting that several "
                    "things went wrong at once near the same place, and nothing more."
                ),
                view={
                    "layout": "map+detail",
                    "focus_zones": [zone],
                    "focus_movements": [m.movement_id for m in members],
                    "encode": "deviation",
                },
            )
        )
    return out


ALL = (detect_deterioration, detect_persistence, detect_variability, detect_clusters)
