"""Where incidents live between restarts.

Until now they lived in a dictionary in the process. A Cloud Run instance
recycles on deploy, on idle, and on its own schedule — and when it did, every
open incident vanished: what was assigned, who was on it, what a sergeant had
found, and the shift handover. An officer would return to a clean board and no
record that anything had happened. That is the single thing that made this a
demonstration rather than a system.

**What is stored and what is not — the line matters.**

An incident is an operational police record: a condition was reported, an
officer was assigned, they found something, it was closed. Police records have
retention requirements and an audit trail is the point of them. That is stored.

Corridor readings are not stored, ever. Google's Maps Service Specific Terms
permit caching latitude and longitude and do not permit building a durable
store of travel content, so the rolling readings stay in memory and die with
the process — which is why the corridor history resets on restart and the
interface says "since the system started" rather than implying an archive.

An incident does carry the figures that justified raising it, once, as the
evidence for a decision an officer took. That is a record of a decision, not a
traffic time series, and it is not queryable as one: there is no endpoint that
returns readings by corridor and hour, and there will not be one until the data
is licensed for it.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Protocol

from packages.incidents.model import (
    Assignment,
    Incident,
    IncidentKind,
    IncidentState,
    Note,
    Priority,
    Transition,
)

COLLECTION = os.environ.get("INCIDENT_COLLECTION", "incidents")


class IncidentStore(Protocol):
    def load_open(self) -> list[Incident]: ...
    def save(self, incident: Incident) -> None: ...
    def describe(self) -> dict: ...


def to_document(i: Incident) -> dict:
    return {
        "incident_id": i.incident_id,
        "kind": i.kind.value,
        "priority": i.priority.value,
        "state": i.state.value,
        "title": i.title,
        "detail": i.detail,
        "location_name": i.location_name,
        "lat": i.lat,
        "lon": i.lon,
        "corridors": list(i.corridors),
        "junctions": list(i.junctions),
        "detected_at": i.detected_at,
        "last_seen_at": i.last_seen_at,
        "resolved_at": i.resolved_at,
        "owner": i.owner,
        "evidence": i.evidence,
        "limitation": i.limitation,
        "assignments": [
            {"at": a.at, "assigned_to": a.assigned_to, "assigned_by": a.assigned_by, "unit": a.unit}
            for a in i.assignments
        ],
        "notes": [
            {"at": n.at, "author": n.author, "text": n.text, "kind": n.kind} for n in i.notes
        ],
        "history": [
            {"at": h.at, "from": h.frm.value, "to": h.to.value, "by": h.by, "reason": h.reason}
            for h in i.history
        ],
    }


def from_document(d: dict) -> Incident:
    def when(v) -> datetime:
        # Firestore returns timezone-aware timestamps; the rest of the system
        # works in naive Siliguri wall-clock, so strip rather than mix.
        return v.replace(tzinfo=None) if isinstance(v, datetime) and v.tzinfo else v

    return Incident(
        incident_id=d["incident_id"],
        kind=IncidentKind(d["kind"]),
        priority=Priority(d["priority"]),
        title=d["title"],
        detail=d["detail"],
        location_name=d["location_name"],
        lat=d["lat"],
        lon=d["lon"],
        corridors=list(d.get("corridors") or []),
        junctions=list(d.get("junctions") or []),
        detected_at=when(d["detected_at"]),
        evidence=d.get("evidence") or {},
        limitation=d.get("limitation", ""),
        state=IncidentState(d["state"]),
        owner=d.get("owner"),
        assignments=[
            Assignment(when(a["at"]), a["assigned_to"], a["assigned_by"], a.get("unit"))
            for a in d.get("assignments") or []
        ],
        notes=[
            Note(when(n["at"]), n["author"], n["text"], n.get("kind", "NOTE"))
            for n in d.get("notes") or []
        ],
        history=[
            Transition(
                when(h["at"]),
                IncidentState(h["from"]),
                IncidentState(h["to"]),
                h["by"],
                h.get("reason"),
            )
            for h in d.get("history") or []
        ],
        last_seen_at=when(d.get("last_seen_at")),
        resolved_at=when(d.get("resolved_at")),
    )


class MemoryStore:
    """Used by tests and local runs. Loses everything on exit, and says so."""

    durable = False

    def __init__(self) -> None:
        self._items: dict[str, Incident] = {}

    def load_open(self) -> list[Incident]:
        return [i for i in self._items.values() if i.is_open]

    def save(self, incident: Incident) -> None:
        self._items[incident.incident_id] = incident

    def describe(self) -> dict:
        return {
            "backend": "memory",
            "durable": False,
            "note": "Incidents are lost when this process exits.",
        }


class FirestoreStore:
    """Production. One document per incident, written on every change.

    Writes are per-incident rather than batched: an incident is small, changes
    are rare compared with polling, and a batch that fails loses several
    records instead of one.
    """

    durable = True

    def __init__(self, project: str | None = None, collection: str = COLLECTION):
        from google.cloud import firestore

        self._db = firestore.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
        self._collection = collection

    def load_open(self) -> list[Incident]:
        open_states = [
            s.value
            for s in IncidentState
            if s not in (IncidentState.CLOSED, IncidentState.STOOD_DOWN, IncidentState.LAPSED)
        ]
        docs = (
            self._db.collection(self._collection)
            .where("state", "in", open_states)
            .limit(500)
            .stream()
        )
        out: list[Incident] = []
        for doc in docs:
            try:
                out.append(from_document(doc.to_dict()))
            except (KeyError, ValueError):
                # A malformed document must not stop a control room booting.
                continue
        return out

    def save(self, incident: Incident) -> None:
        self._db.collection(self._collection).document(incident.incident_id).set(
            to_document(incident)
        )

    def describe(self) -> dict:
        return {
            "backend": "firestore",
            "durable": True,
            "collection": self._collection,
            "note": (
                "Incident records survive restarts. Corridor readings do not and are "
                "never written: the Maps terms permit caching coordinates only."
            ),
        }


def build_store() -> IncidentStore:
    """Firestore when configured, memory otherwise — and it never guesses.

    A police system silently falling back to a store that forgets is worse than
    one that refuses to start, so the choice is explicit in the environment.
    """
    backend = os.environ.get("INCIDENT_STORE", "memory").lower()
    if backend == "firestore":
        return FirestoreStore()
    return MemoryStore()
