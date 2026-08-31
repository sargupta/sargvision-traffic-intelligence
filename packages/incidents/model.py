"""What an officer works on, and what happens to it.

The previous version of this product could detect and explain. It had no verbs.
An officer could see that Hill Cart Road was blocked and do nothing with that
inside the system — no way to own it, dispatch it, record what was found, or
hand it to the next shift.

This module is the verbs.

    DETECTED ─┬─► ACKNOWLEDGED ──► ASSIGNED ──► ON_SCENE ──► CLEARING ──► RESOLVED ──► CLOSED
              │                                                              ▲
              ├─► STOOD_DOWN  (looked at it, no action needed)                │
              └─► LAPSED      (cleared before anyone acted) ──────────────────┘

**STOOD_DOWN and LAPSED are not failures.** An officer deciding a condition
needs no action is a real, recordable outcome, and a system that only lets you
close things you acted on will be worked around within a week. LAPSED is how we
learn the system is raising things that do not matter: a high lapse rate is a
fault in the alerting, and hiding it would hide the fault.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class IncidentState(str, Enum):
    DETECTED = "DETECTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    ON_SCENE = "ON_SCENE"
    CLEARING = "CLEARING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"
    STOOD_DOWN = "STOOD_DOWN"
    LAPSED = "LAPSED"


TERMINAL = {IncidentState.CLOSED, IncidentState.STOOD_DOWN, IncidentState.LAPSED}

# What may follow what. Enforced, so an audit trail cannot contain a sequence
# that never happened.
TRANSITIONS: dict[IncidentState, set[IncidentState]] = {
    IncidentState.DETECTED: {
        IncidentState.ACKNOWLEDGED,
        IncidentState.STOOD_DOWN,
        IncidentState.LAPSED,
    },
    IncidentState.ACKNOWLEDGED: {
        IncidentState.ASSIGNED,
        IncidentState.CLEARING,
        IncidentState.STOOD_DOWN,
        IncidentState.LAPSED,
    },
    IncidentState.ASSIGNED: {
        IncidentState.ON_SCENE,
        IncidentState.ACKNOWLEDGED,
        IncidentState.STOOD_DOWN,
        IncidentState.LAPSED,
    },
    IncidentState.ON_SCENE: {IncidentState.CLEARING, IncidentState.RESOLVED},
    IncidentState.CLEARING: {IncidentState.RESOLVED, IncidentState.ON_SCENE},
    IncidentState.RESOLVED: {IncidentState.CLOSED, IncidentState.ACKNOWLEDGED},
    IncidentState.CLOSED: set(),
    IncidentState.STOOD_DOWN: {IncidentState.ACKNOWLEDGED},  # reopen if it returns
    IncidentState.LAPSED: {IncidentState.ACKNOWLEDGED},
}


class IncidentKind(str, Enum):
    """Congestion and safety are different problems and never share a score.

    Venus More has the highest accident density in Siliguri and one of its
    lowest V/C ratios. A single severity would rank it low and be wrong, or
    rank it high and be wrong about why.
    """

    CONGESTION = "CONGESTION"  # slower than typical, right now
    CHOKE_POINT = "CHOKE_POINT"  # a located stretch of stopped traffic
    SPREADING = "SPREADING"  # several corridors degrading together
    SAFETY = "SAFETY"  # structural accident risk, not congestion
    DATA_GAP = "DATA_GAP"  # we cannot see here


class Priority(str, Enum):
    P1 = "P1"  # act now
    P2 = "P2"  # act this shift
    P3 = "P3"  # watch
    P4 = "P4"  # record only


@dataclass(frozen=True)
class Note:
    at: datetime
    author: str
    text: str
    kind: str = "NOTE"  # NOTE | CAUSE | ACTION | OUTCOME

    def as_dict(self) -> dict:
        return {
            "at": self.at.isoformat(timespec="seconds"),
            "author": self.author,
            "text": self.text,
            "kind": self.kind,
        }


@dataclass(frozen=True)
class Assignment:
    at: datetime
    assigned_to: str
    assigned_by: str
    unit: str | None = None

    def as_dict(self) -> dict:
        return {
            "at": self.at.isoformat(timespec="seconds"),
            "assigned_to": self.assigned_to,
            "assigned_by": self.assigned_by,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class Transition:
    at: datetime
    frm: IncidentState
    to: IncidentState
    by: str
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "at": self.at.isoformat(timespec="seconds"),
            "from": self.frm.value,
            "to": self.to.value,
            "by": self.by,
            "reason": self.reason,
        }


class IllegalTransition(Exception):
    """Raised rather than logged. A refused transition is a bug, not a warning."""


@dataclass
class Incident:
    incident_id: str
    kind: IncidentKind
    priority: Priority
    title: str
    detail: str
    location_name: str  # "Hill Cart Road, near Air View More"
    lat: float
    lon: float
    corridors: list[str]
    junctions: list[str]
    detected_at: datetime
    evidence: dict
    limitation: str
    state: IncidentState = IncidentState.DETECTED
    owner: str | None = None
    assignments: list[Assignment] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    history: list[Transition] = field(default_factory=list)
    last_seen_at: datetime | None = None
    resolved_at: datetime | None = None

    # ── lifecycle ────────────────────────────────────────────────────────────
    def move(
        self, to: IncidentState, by: str, reason: str | None = None, at: datetime | None = None
    ) -> None:
        allowed = TRANSITIONS[self.state]
        if to not in allowed:
            raise IllegalTransition(
                f"{self.incident_id}: cannot go {self.state.value} → {to.value}. "
                f"Allowed: {', '.join(sorted(s.value for s in allowed)) or 'none'}"
            )
        moment = at or datetime.now()
        self.history.append(Transition(moment, self.state, to, by, reason))
        self.state = to
        if to is IncidentState.RESOLVED:
            self.resolved_at = moment

    def acknowledge(self, by: str, at: datetime | None = None) -> None:
        self.move(IncidentState.ACKNOWLEDGED, by, at=at)

    def assign(
        self, to_officer: str, by: str, unit: str | None = None, at: datetime | None = None
    ) -> None:
        moment = at or datetime.now()
        if self.state is IncidentState.DETECTED:
            self.acknowledge(by, at=moment)
        self.assignments.append(Assignment(moment, to_officer, by, unit))
        self.owner = to_officer
        self.move(IncidentState.ASSIGNED, by, reason=f"to {to_officer}", at=moment)

    def add_note(
        self, author: str, text: str, kind: str = "NOTE", at: datetime | None = None
    ) -> None:
        self.notes.append(Note(at or datetime.now(), author, text, kind))

    def stand_down(self, by: str, reason: str, at: datetime | None = None) -> None:
        """No action needed. A real outcome, recorded as one."""
        if not reason.strip():
            raise ValueError("standing an incident down requires a reason")
        self.add_note(by, reason, kind="OUTCOME", at=at)
        self.move(IncidentState.STOOD_DOWN, by, reason=reason, at=at)

    def lapse(self, at: datetime | None = None) -> None:
        """Cleared before anyone acted. Counted, because it grades the alerting."""
        self.move(
            IncidentState.LAPSED, by="system", reason="condition cleared before action", at=at
        )

    def close(self, by: str, outcome: str, at: datetime | None = None) -> None:
        if not outcome.strip():
            raise ValueError("closing an incident requires an outcome")
        self.add_note(by, outcome, kind="OUTCOME", at=at)
        self.move(IncidentState.CLOSED, by, reason=outcome, at=at)

    # ── views ────────────────────────────────────────────────────────────────
    @property
    def is_open(self) -> bool:
        return self.state not in TERMINAL

    @property
    def needs_attention(self) -> bool:
        """Nobody has taken responsibility for this yet."""
        return self.state in (IncidentState.DETECTED, IncidentState.ACKNOWLEDGED)

    def age_minutes(self, now: datetime) -> float:
        return (now - self.detected_at).total_seconds() / 60

    def unowned_minutes(self, now: datetime) -> float:
        if self.owner:
            return 0.0
        return self.age_minutes(now)

    def as_dict(self, now: datetime | None = None) -> dict:
        moment = now or datetime.now()
        return {
            "incident_id": self.incident_id,
            "kind": self.kind.value,
            "priority": self.priority.value,
            "state": self.state.value,
            "title": self.title,
            "detail": self.detail,
            "location_name": self.location_name,
            "lat": self.lat,
            "lon": self.lon,
            "corridors": self.corridors,
            "junctions": self.junctions,
            "detected_at": self.detected_at.isoformat(timespec="seconds"),
            "last_seen_at": self.last_seen_at.isoformat(timespec="seconds")
            if self.last_seen_at
            else None,
            "resolved_at": self.resolved_at.isoformat(timespec="seconds")
            if self.resolved_at
            else None,
            "age_minutes": round(self.age_minutes(moment), 1),
            "owner": self.owner,
            "is_open": self.is_open,
            "needs_attention": self.needs_attention,
            "evidence": self.evidence,
            "limitation": self.limitation,
            "assignments": [a.as_dict() for a in self.assignments],
            "notes": [n.as_dict() for n in self.notes],
            "history": [h.as_dict() for h in self.history],
            "next_actions": [
                s.value for s in sorted(TRANSITIONS[self.state], key=lambda x: x.value)
            ],
        }


def incident_id(kind: IncidentKind, lat: float, lon: float, detected_at: datetime) -> str:
    """Stable within a day for the same place and kind, so a flapping condition
    reattaches to the incident an officer already owns instead of spawning a new
    one every poll."""
    seed = f"{kind.value}:{lat:.4f}:{lon:.4f}:{detected_at:%Y-%m-%d}"
    return f"INC-{hashlib.sha1(seed.encode()).hexdigest()[:8].upper()}"
