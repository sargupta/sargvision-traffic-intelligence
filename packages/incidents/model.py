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
class IndexSample:
    """The worst live congestion index across an incident's corridors, at a
    moment in its life. Captured while the incident is open so that "did the
    deployment work" can be answered from the road, not from memory.

    The index is duration / staticDuration — current travel time against
    Google's modelled typical. 1.0 is typical; above 1.0 is slower than usual.
    This is the same probe-travel-time signal NYC used to measure a ~10% gain
    from Midtown-in-Motion, and it is the only thing that makes the verification
    claim more than an assertion.
    """

    at: datetime
    index: float
    band: str

    def as_dict(self) -> dict:
        return {
            "at": self.at.isoformat(timespec="seconds"),
            "index": round(self.index, 3),
            "band": self.band,
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
    samples: list[IndexSample] = field(default_factory=list)
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

    # ── measurement (the verification raw material) ───────────────────────────
    _SAMPLE_CAP = 500  # ~25h at a 3-minute poll; FIFO beyond that

    def record_sample(
        self, at: datetime, index: float | None, band: str, *, anchor: bool = False
    ) -> None:
        """Record the live index for this incident, if there is one.

        A run of identical readings collapses to a single sample keeping its
        ONSET time — not the newest, which is what a previous version did and
        which quietly destroyed the whole point of the series: a sample recorded
        AT a transition (on-scene, resolved) would have its timestamp dragged
        forward by the next identical poll, moving it off the moment it was
        anchoring, so `_index_near` could no longer find it and the verification
        output vanished. Keeping the onset leaves "how long has it sat" answerable
        as (last_poll − onset), and leaves the anchor where it belongs.

        `anchor=True` forces an append even when the value repeats. It is used at
        every transition, so on-scene and resolved always carry an exact reading
        regardless of whether the index happened to be steady.
        """
        if index is None:
            return
        if not anchor and self.samples:
            last = self.samples[-1]
            if round(last.index, 3) == round(index, 3) and last.band == band:
                return  # a stable reading is one sample, timed at its onset
        self.samples.append(IndexSample(at, index, band))
        if len(self.samples) > self._SAMPLE_CAP:
            del self.samples[0 : len(self.samples) - self._SAMPLE_CAP]

    def _index_near(self, when: datetime | None, tol_minutes: float = 12.0) -> float | None:
        """The sampled index closest to a moment, within a tolerance.

        Transitions happen between polls, so the index at "on scene" is the
        nearest sample, not an exact one. The tolerance keeps a stale sample
        from being read as the value at a much later transition.
        """
        if when is None or not self.samples:
            return None
        best = min(self.samples, key=lambda s: abs((s.at - when).total_seconds()))
        if abs((best.at - when).total_seconds()) > tol_minutes * 60:
            return None
        return best.index

    def _transition_time(self, to: IncidentState) -> datetime | None:
        for h in self.history:
            if h.to is to:
                return h.at
        return None

    def impact(self, now: datetime | None = None) -> dict:
        """What the record can honestly say about this incident's course.

        This is a within-incident reading only: how the index moved while the
        incident was owned, and how quickly it was cleared. It is NOT a
        counterfactual — proving the officer *caused* the improvement needs the
        junction's own baseline for the same weekday and hour, which accrues as
        history is kept. Everything here is the raw material for that study;
        nothing here claims causation on its own.
        """
        detected = self.evidence.get("worst_index")
        if detected is None and self.samples:
            detected = self.samples[0].index

        on_scene_at = self._transition_time(IncidentState.ON_SCENE)
        assigned_at = self._transition_time(IncidentState.ASSIGNED)
        index_on_scene = self._index_near(on_scene_at)
        index_resolved = self._index_near(self.resolved_at)
        if index_resolved is None and self.resolved_at and self.samples:
            index_resolved = self.samples[-1].index

        def minutes_between(a: datetime | None, b: datetime | None) -> float | None:
            if a is None or b is None:
                return None
            return round((b - a).total_seconds() / 60, 1)

        peak = max((s.index for s in self.samples), default=detected)

        # Fell while the officer owned it — the honest, un-caveated observation.
        improved = None
        if index_on_scene is not None and index_resolved is not None:
            improved = round(index_on_scene - index_resolved, 3)

        return {
            "index_at_detection": round(detected, 3) if detected is not None else None,
            "index_on_scene": round(index_on_scene, 3) if index_on_scene is not None else None,
            "index_resolved": round(index_resolved, 3) if index_resolved is not None else None,
            "peak_index": round(peak, 3) if peak is not None else None,
            "minutes_to_scene": minutes_between(assigned_at, on_scene_at),
            "minutes_to_clear": minutes_between(
                on_scene_at or self.detected_at, self.resolved_at
            ),
            "index_fell_while_owned": improved,
            "samples": len(self.samples),
            "basis": (
                "Within-incident reading of the corridor's own index. Not a "
                "counterfactual: it does not prove the deployment caused the "
                "change until compared against this junction's baseline for the "
                "same weekday and hour."
            ),
        }

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
            "samples": [s.as_dict() for s in self.samples],
            "impact": self.impact(moment),
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
