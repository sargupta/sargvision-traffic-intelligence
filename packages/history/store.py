"""Persistence for the corridor memory — one document per corridor.

Mirrors the incident store's shape (a Protocol, a MemoryStore for tests and
local runs, a FirestoreStore for production, and a build_* that refuses to
guess). It persists only the derived aggregates the model produces; see
history/model.py for why that is within the Maps terms.

Writes are cadenced, not per-poll: the baselines change on every cycle but
matter over weeks, so flushing the touched corridors every few minutes trades a
few minutes of at-most-lost aggregation for a fraction of the write cost.
"""

from __future__ import annotations

import os
from typing import Protocol

from packages.history.model import (
    Bucket,
    CorridorHistory,
    DailyRollup,
    ObservationHistory,
)

COLLECTION = "corridor_history"


def to_document(ch: CorridorHistory) -> dict:
    return {
        "corridor_id": ch.corridor_id,
        "name": ch.name,
        "buckets": {
            f"{wd}:{hr}": {
                "n": b.n,
                "total": b.total,
                "total_sq": b.total_sq,
                "min_index": b.min_index,
                "max_index": b.max_index,
                "hist": b.hist,
                "congested_n": b.congested_n,
                "last_seen": b.last_seen,
            }
            for (wd, hr), b in ch.buckets.items()
        },
        "days": {
            d: {"n": r.n, "total": r.total, "peak": r.peak, "congested_n": r.congested_n}
            for d, r in ch.days.items()
        },
    }


def from_document(d: dict) -> CorridorHistory:
    ch = CorridorHistory(corridor_id=d["corridor_id"], name=d.get("name", ""))
    for key, bd in (d.get("buckets") or {}).items():
        wd, hr = key.split(":")
        b = Bucket(
            n=bd["n"],
            total=bd["total"],
            total_sq=bd["total_sq"],
            min_index=bd.get("min_index"),
            max_index=bd.get("max_index"),
            hist=list(bd.get("hist") or []),
            congested_n=bd.get("congested_n", 0),
            last_seen=bd.get("last_seen"),
        )
        # A doc from an older bin layout is discarded rather than mis-scaled.
        if len(b.hist) == len(Bucket().hist):
            ch.buckets[(int(wd), int(hr))] = b
    for date, rd in (d.get("days") or {}).items():
        ch.days[date] = DailyRollup(
            n=rd["n"], total=rd["total"], peak=rd.get("peak"), congested_n=rd.get("congested_n", 0)
        )
    return ch


class HistoryStore(Protocol):
    def load_all(self) -> ObservationHistory: ...
    def save(self, ch: CorridorHistory) -> None: ...
    def describe(self) -> dict: ...


class MemoryHistoryStore:
    """Tests and local runs. Learns within the process, forgets on exit."""

    durable = False

    def __init__(self) -> None:
        self._docs: dict[str, dict] = {}

    def load_all(self) -> ObservationHistory:
        h = ObservationHistory()
        for doc in self._docs.values():
            ch = from_document(doc)
            h.corridors[ch.corridor_id] = ch
        return h

    def save(self, ch: CorridorHistory) -> None:
        self._docs[ch.corridor_id] = to_document(ch)

    def describe(self) -> dict:
        return {
            "backend": "memory",
            "durable": False,
            "note": "The corridor memory is lost when this process exits.",
        }


class FirestoreHistoryStore:
    """Production. One document per corridor under `corridor_history`.

    Loading the whole board on boot resumes the learning where the last instance
    left it — the baselines are not thrown away by a deploy, which is the entire
    point of persisting them.
    """

    durable = True

    def __init__(self, project: str | None = None, collection: str = COLLECTION):
        from google.cloud import firestore

        self._db = firestore.Client(project=project or os.environ.get("GOOGLE_CLOUD_PROJECT"))
        self._collection = collection

    def load_all(self) -> ObservationHistory:
        h = ObservationHistory()
        for doc in self._db.collection(self._collection).limit(500).stream():
            try:
                ch = from_document(doc.to_dict())
                h.corridors[ch.corridor_id] = ch
            except (KeyError, ValueError):
                continue  # a malformed doc must not stop a control room booting
        return h

    def save(self, ch: CorridorHistory) -> None:
        self._db.collection(self._collection).document(ch.corridor_id).set(to_document(ch))

    def describe(self) -> dict:
        return {
            "backend": "firestore",
            "durable": True,
            "collection": self._collection,
            "note": (
                "Corridor baselines survive restarts. Only derived aggregates are written — a "
                "histogram of our own index per weekday-hour and coarse daily rollups; never a "
                "raw reading, so the Maps terms are honoured."
            ),
        }


def build_history_store() -> HistoryStore:
    """Firestore when configured, memory otherwise — the same explicit choice the
    incident store makes, for the same reason: no silent forgetting."""
    backend = os.environ.get("HISTORY_STORE", os.environ.get("INCIDENT_STORE", "memory")).lower()
    if backend == "firestore":
        return FirestoreHistoryStore()
    return MemoryHistoryStore()
