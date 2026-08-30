"""The intelligence loop.

    provider  →  state  →  detectors  →  consolidation  →  feed

One tick: take a sample of every due movement, update the city state, ask each
detector what it sees, consolidate what comes back, and update the feed.

Two things this file is careful about.

**Findings have a life.** A detector fires on every tick that the condition
holds. If each firing were a new feed entry, twenty minutes of one problem would
produce twenty identical alerts. Findings are therefore keyed, and a repeat
updates the existing entry rather than adding one — so the feed shows what is
happening, not how often it was checked.

**Consolidation beats enumeration.** When three movements through one zone
deteriorate together, the useful statement is about the cluster, not three
statements about movements. The individual findings are kept as the cluster's
components rather than surfaced beside it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

import polars as pl

from packages.providers.live import ObservationProvider, Sample
from packages.realtime import detectors as det
from packages.realtime.detectors import LiveFinding, Signal
from packages.realtime.state import Baseline, CityState, MovementState, Status
from packages.registry.movements import Registry

RESOLVE_AFTER = timedelta(minutes=15)
FEED_LIMIT = 40


@dataclass
class FeedEntry:
    finding: LiveFinding
    first_seen: datetime
    last_seen: datetime
    state: str = "ACTIVE"          # ACTIVE | RESOLVED
    components: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            **self.finding.as_dict(),
            "first_seen": self.first_seen.isoformat(timespec="seconds"),
            "last_seen": self.last_seen.isoformat(timespec="seconds"),
            "state": self.state,
            "components": self.components,
        }


def load_baselines(frame: pl.DataFrame) -> dict[tuple[str, str, int], Baseline]:
    return {
        (r["movement_id"], r["day_type"], int(r["hour"])): Baseline(
            median_pace=r["median_pace"],
            p25_pace=r["p25_pace"],
            p75_pace=r["p75_pace"],
            p90_pace=r["p90_pace"],
            sample_size=int(r["sample_size"]),
            confidence=r["confidence"],
        )
        for r in frame.iter_rows(named=True)
    }


def _consolidate(findings: list[LiveFinding]) -> tuple[list[LiveFinding], dict[str, list[str]]]:
    """Collapse findings that are the same story told more than once.

    Two passes, both of which exist because a feed that enumerates is a feed
    nobody reads.

    1. A cluster finding absorbs the single-movement findings it explains. Three
       movements failing together is one statement, not four.
    2. Among what is left, findings of the same kind touching the same zone are
       collapsed onto the strongest one. Three separate "unstable" entries for
       three movements through Champasari is one observation about Champasari,
       and the other two are attached as components rather than repeated.
    """
    absorbed: dict[str, list[str]] = {}
    covered: set[str] = set()

    for c in (f for f in findings if f.signal is Signal.CLUSTER):
        members = [
            f.id
            for f in findings
            if f.signal is not Signal.CLUSTER and set(f.movements) <= set(c.movements)
        ]
        absorbed[c.id] = members
        covered.update(members)

    remaining = [f for f in findings if f.signal is Signal.CLUSTER or f.id not in covered]

    by_signal_zone: dict[tuple[str, str], list[LiveFinding]] = {}
    for f in remaining:
        if f.signal is Signal.CLUSTER or len(f.zones) != 1:
            continue
        by_signal_zone.setdefault((f.signal.value, f.zones[0]), []).append(f)

    for group in by_signal_zone.values():
        if len(group) < 2:
            continue
        group.sort(key=lambda f: f.priority, reverse=True)
        lead, rest = group[0], group[1:]
        absorbed.setdefault(lead.id, []).extend(f.id for f in rest)
        covered.update(f.id for f in rest)

    kept = [f for f in remaining if f.id not in covered]
    return kept, absorbed


@dataclass
class IntelligenceLoop:
    registry: Registry
    provider: ObservationProvider
    baselines: dict[tuple[str, str, int], Baseline]
    city: CityState = field(default_factory=CityState)
    feed: dict[str, FeedEntry] = field(default_factory=dict)
    ticks: int = 0

    def __post_init__(self) -> None:
        self.city.mode = self.provider.provenance()["mode"]
        self.city.is_live = self.provider.is_live
        for m in self.registry.active:
            self.city.movements[m.movement_id] = MovementState(
                movement_id=m.movement_id,
                name=m.name,
                origin_zone=m.origin_zone,
                dest_zone=m.dest_zone,
                origin_name=m.origin_name,
                dest_name=m.dest_name,
            )
            self.city.zone_names[m.origin_zone] = m.origin_name
            self.city.zone_names[m.dest_zone] = m.dest_name

    def _baseline_for(self, movement_id: str, at: datetime) -> Baseline | None:
        day_type = "WEEKEND" if at.weekday() >= 5 else "WEEKDAY"
        return self.baselines.get((movement_id, day_type, at.hour))

    def reset(self) -> None:
        """Clear all accumulated state.

        Called when the replay clock wraps back to the start of the day. Without
        it, `since` still points at yesterday and persistence is computed across
        a backwards jump in time, so a movement reports having been elevated for
        four hours on a day that is ten minutes old. Readings would also arrive
        out of order, which the velocity slope assumes cannot happen.
        """
        for state in self.city.movements.values():
            state.readings.clear()
            state.status = Status.UNKNOWN
            state.since = None
        self.feed.clear()

    def tick(self, now: datetime) -> dict:
        """Advance the system by one collection cycle."""
        self.ticks += 1
        samples: list[Sample] = self.provider.sample(self.registry.active, now)

        for s in samples:
            state = self.city.movements.get(s.movement_id)
            if state is None:
                continue
            state.observe(s, self._baseline_for(s.movement_id, now))

        self.city.updated_at = now

        found: list[LiveFinding] = []
        for detector in det.ALL:
            found.extend(detector(self.city, now))
        found, absorbed = _consolidate(found)

        seen_now = set()
        for f in found:
            seen_now.add(f.id)
            existing = self.feed.get(f.id)
            if existing:
                existing.finding = f
                existing.last_seen = now
                existing.state = "ACTIVE"
                existing.components = absorbed.get(f.id, existing.components)
            else:
                self.feed[f.id] = FeedEntry(
                    finding=f,
                    first_seen=now,
                    last_seen=now,
                    components=absorbed.get(f.id, []),
                )

        for key, entry in self.feed.items():
            if key not in seen_now and entry.state == "ACTIVE":
                if now - entry.last_seen >= RESOLVE_AFTER:
                    entry.state = "RESOLVED"

        return {
            "at": now.isoformat(timespec="seconds"),
            "tick": self.ticks,
            "samples": len(samples),
            "headline": self.city.headline(),
            "counts": self.city.counts(),
            "new": [f.id for f in found if self.feed[f.id].first_seen == now],
            "active": sum(1 for e in self.feed.values() if e.state == "ACTIVE"),
        }

    # ── views the API serves ─────────────────────────────────────────────────
    def snapshot(self) -> dict:
        prov = self.provider.provenance()
        return {
            "mode": self.city.mode,
            "is_live": self.city.is_live,
            "provenance": prov,
            "updated_at": self.city.updated_at.isoformat(timespec="seconds")
            if self.city.updated_at
            else None,
            "headline": self.city.headline(),
            "counts": self.city.counts(),
            "movements": [
                {
                    "movement_id": m.movement_id,
                    "name": m.name,
                    "origin_zone": m.origin_zone,
                    "dest_zone": m.dest_zone,
                    "status": m.status.value,
                    "deviation_pct": round(m.deviation_pct, 1) if m.deviation_pct is not None else None,
                    "current_minutes": round(m.latest.traffic_seconds / 60, 1) if m.latest else None,
                    "expected_minutes": (
                        round(
                            self._baseline_for(m.movement_id, self.city.updated_at).expected_seconds(
                                m.latest.distance_m
                            )
                            / 60,
                            1,
                        )
                        if m.latest
                        and self.city.updated_at
                        and self._baseline_for(m.movement_id, self.city.updated_at)
                        else None
                    ),
                    "persistence_minutes": round(m.persistence_minutes(self.city.updated_at), 1)
                    if self.city.updated_at
                    else 0.0,
                    "readings": len(m.readings),
                }
                for m in self.city.movements.values()
            ],
        }

    def feed_entries(self, include_resolved: bool = False) -> list[dict]:
        entries = [
            e
            for e in self.feed.values()
            if include_resolved or e.state == "ACTIVE"
        ]
        entries.sort(key=lambda e: e.finding.priority, reverse=True)
        return [e.as_dict() for e in entries[:FEED_LIMIT]]

    def history(self, movement_id: str) -> list[dict]:
        state = self.city.movements.get(movement_id)
        if state is None:
            return []
        return [
            {
                "at": r.at.isoformat(timespec="seconds"),
                "minutes": round(r.traffic_seconds / 60, 2),
                "deviation_pct": round(r.deviation_pct, 1) if r.deviation_pct is not None else None,
                "status": r.status.value,
            }
            for r in state.readings
        ]
