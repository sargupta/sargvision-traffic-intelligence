"""The command centre: poll, cluster, raise, age, close.

    corridors ──► probe ──► readings ──► choke clusters ──► incidents
                                │                              │
                                └──► corridor status ──────────┘

One pass per cycle. Everything an officer sees comes out of this loop, and
nothing in it asks a language model anything.

**The alert budget is a first-class constraint, not a setting.** A duty officer
working an eight-hour shift can meaningfully act on a handful of things. A
system that raises forty will be ignored by the second week, and an ignored
system is worse than no system because it looks like coverage. So the number of
incidents that may be OPEN and unowned at once is capped: below the cap, raise
freely; at the cap, a new condition must outrank something already there.
"""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from packages.incidents.cluster import ChokeCluster, cluster_chokes, metres
from packages.incidents.model import (
    Incident,
    IncidentKind,
    IncidentState,
    Priority,
    incident_id,
)
from packages.incidents.store import IncidentStore, MemoryStore
from packages.network.model import Network
from packages.network.probe import CorridorReading, RoutesProbe


@dataclass(frozen=True)
class Thresholds:
    """Calibrated on Siliguri's live index distribution. Configuration, not law.

    The index is `duration / staticDuration` — current travel time against
    Google's modelled typical time. It reads below 1.0 when the road is running
    better than typical, which is common overnight, so these bands describe
    "worse than usual here" and never "free flow".
    """

    elevated: float = 1.25
    high: float = 1.45
    severe: float = 1.75
    clear: float = 1.15  # hysteresis: leave a state below this
    min_excess_minutes: float = 1.0  # ignore a big ratio on a two-minute hop

    def band(self, index: float, excess_minutes: float) -> str:
        if excess_minutes < self.min_excess_minutes:
            return "NORMAL"
        if index >= self.severe:
            return "SEVERE"
        if index >= self.high:
            return "HIGH"
        if index >= self.elevated:
            return "ELEVATED"
        return "NORMAL"


SILIGURI = Thresholds()

# How many unowned open incidents may exist at once. Above this, a new
# condition has to be worse than the weakest thing already waiting.
#
# The arithmetic behind the number: 68 segments evaluated every cycle is
# roughly 2,000 evaluations per six-hour shift. A rule with a 1% false-positive
# rate — which sounds excellent — produces twenty spurious alerts a shift, one
# every eighteen minutes, from noise alone. The duty officer is also on
# wireless, taking public calls and clearing VIP movement, so the screen has
# perhaps a fifth of their attention. The real currency is deployments, not
# clicks, and nobody deploys twenty times a shift.
ALERT_BUDGET = 5

# Not every corridor deserves the same attention.
#
# Polling all 68 segments on a fixed three-minute clock is 980,000 requests a
# month and treats a road running normally as though it were about to fail.
# Cadence follows condition instead: a corridor that is quiet is asked rarely,
# one that is deteriorating is watched closely. This costs less AND resolves
# the thing that matters better, which is the rare case where those agree.
CADENCE = {
    "SEVERE": timedelta(minutes=3),
    "HIGH": timedelta(minutes=3),
    "ELEVATED": timedelta(minutes=6),
    "NORMAL": timedelta(minutes=15),
    "UNKNOWN": timedelta(minutes=2),  # never seen: get a first reading soon
}

# Overnight there is no sergeant to send. Conditions are still recorded so the
# morning shift inherits them, but the network is asked far less often because
# nothing turns on the answer until there is someone to act on it.
QUIET_HOURS = range(23, 24), range(0, 5)
QUIET_CADENCE = timedelta(minutes=30)


def _is_quiet(at: datetime) -> bool:
    return at.hour >= 23 or at.hour < 5


# A condition must hold this long before it becomes an incident. Traffic
# fluctuates; a single poll is not a problem. Tunable because the right value
# depends on the polling cadence, and because a demonstration cannot wait
# eight minutes to show anything.
CONFIRM_AFTER = timedelta(minutes=float(os.environ.get("CONFIRM_MINUTES", "8")))

# An incident nobody acted on, whose condition has cleared, lapses after this.
LAPSE_AFTER = timedelta(minutes=float(os.environ.get("LAPSE_MINUTES", "20")))

# A new choke cluster within this distance of an open incident is that
# incident, not a new one. Slightly wider than the clustering radius because a
# jam's centroid wanders as its tail grows and shrinks.
MATCH_RADIUS_M = 450.0


@dataclass
class _Candidate:
    """A condition that is not yet an incident.

    Position is updated as the cluster moves; `first_seen` is not. That
    distinction is the whole point: a queue is confirmed on how long it has
    persisted, not on how still it has stood.
    """

    lat: float
    lon: float
    severity: str
    first_seen: datetime
    last_seen: datetime


@dataclass
class CorridorStatus:
    """Current and recent condition of one corridor. Memory only."""

    corridor_id: str
    name: str
    readings: deque[CorridorReading] = field(default_factory=lambda: deque(maxlen=180))
    band: str = "UNKNOWN"
    band_since: datetime | None = None
    due_at: datetime | None = None

    def is_due(self, now: datetime) -> bool:
        return self.due_at is None or now >= self.due_at

    def schedule(self, now: datetime) -> None:
        interval = QUIET_CADENCE if _is_quiet(now) else CADENCE.get(self.band, CADENCE["NORMAL"])
        self.due_at = now + interval

    @property
    def latest(self) -> CorridorReading | None:
        return self.readings[-1] if self.readings else None

    @property
    def index(self) -> float | None:
        return self.latest.congestion_index if self.latest else None

    def held_for(self, now: datetime) -> timedelta:
        if self.band_since is None:
            return timedelta(0)
        return now - self.band_since

    def trend(self, window: timedelta = timedelta(minutes=30)) -> float | None:
        """Change in index per 10 minutes, least squares over the window."""
        if not self.readings:
            return None
        cutoff = self.readings[-1].observed_at - window
        pts = [r for r in self.readings if r.observed_at >= cutoff]
        if len(pts) < 3:
            return None
        t0 = pts[0].observed_at
        xs = [(p.observed_at - t0).total_seconds() / 600 for p in pts]
        ys = [p.congestion_index for p in pts]
        mx = sum(xs) / len(xs)
        my = sum(ys) / len(ys)
        denom = sum((x - mx) ** 2 for x in xs)
        if denom == 0:
            return None
        return sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / denom

    def observe(self, reading: CorridorReading, thresholds: Thresholds) -> str:
        self.readings.append(reading)
        band = thresholds.band(reading.congestion_index, reading.excess_minutes)
        # Hysteresis so a corridor hovering on a threshold does not flicker.
        # UNKNOWN is excluded: it means "not yet observed", not "elevated", and
        # holding it would strand a corridor's first reading forever.
        if (
            self.band not in ("NORMAL", "UNKNOWN")
            and band == "NORMAL"
            and reading.congestion_index >= thresholds.clear
        ):
            band = self.band
        if band != self.band:
            self.band = band
            self.band_since = reading.observed_at
        return band


@dataclass
class CommandCentre:
    network: Network
    probe: RoutesProbe
    thresholds: Thresholds = SILIGURI
    alert_budget: int = ALERT_BUDGET
    confirm_after: timedelta = CONFIRM_AFTER
    store: IncidentStore = field(default_factory=MemoryStore)
    status: dict[str, CorridorStatus] = field(default_factory=dict)
    incidents: dict[str, Incident] = field(default_factory=dict)
    cycles: int = 0
    last_poll: datetime | None = None
    suppressed: dict[str, int] = field(
        default_factory=lambda: {"holding": 0, "below_threshold": 0, "quiet_hours": 0, "budget": 0}
    )
    # Candidate conditions, held until they have persisted long enough to be
    # worth an officer's attention. Matched by PROXIMITY, not by a hash of the
    # rounded coordinate — see _confirm_candidate.
    _candidates: list[_Candidate] = field(default_factory=list)

    def __post_init__(self) -> None:
        for cid, c in self.network.corridors.items():
            self.status[cid] = CorridorStatus(corridor_id=cid, name=c.name)

        # Whatever was open when the last instance stopped is open now. Without
        # this a deploy handed the incoming shift a clean board and no record
        # that anything had been happening.
        for incident in self.store.load_open():
            self.incidents[incident.incident_id] = incident

    def remember(self, incident: Incident) -> None:
        """Persist one incident. Called after every change an officer makes."""
        self.store.save(incident)

    # ── the cycle ────────────────────────────────────────────────────────────
    def poll(self, now: datetime) -> dict:
        self.cycles += 1
        self.last_poll = now

        chokes: dict[str, list] = {}
        read = 0
        skipped = 0
        for cid, corridor in self.network.corridors.items():
            status = self.status[cid]
            if not status.is_due(now):
                skipped += 1
                # A corridor not polled this cycle keeps whatever choke points
                # its last reading found, so a jam does not blink out of the
                # incident view simply because its corridor was not due.
                if status.latest and status.latest.choke_points:
                    chokes[cid] = list(status.latest.choke_points)
                continue

            reading = self.probe.read(
                corridor,
                self.network.junctions[corridor.from_junction],
                self.network.junctions[corridor.to_junction],
                now,
            )
            if reading is None:
                status.schedule(now)
                continue
            read += 1
            status.observe(reading, self.thresholds)
            status.schedule(now)
            if reading.choke_points:
                chokes[cid] = list(reading.choke_points)

        clusters = cluster_chokes(chokes)
        raised = self._raise_incidents(clusters, now)
        lapsed = self._age_incidents(now)
        self._prune_candidates(now)

        return {
            "at": now.isoformat(timespec="seconds"),
            "cycle": self.cycles,
            "corridors_read": read,
            "corridors_skipped": skipped,
            "quiet_hours": _is_quiet(now),
            "choke_clusters": len(clusters),
            "suppressed": dict(self.suppressed),
            "raised": raised,
            "lapsed": lapsed,
            "open": sum(1 for i in self.incidents.values() if i.is_open),
            "unowned": sum(1 for i in self.incidents.values() if i.needs_attention),
        }

    # ── incidents ────────────────────────────────────────────────────────────
    def _nearest_junction(self, lat: float, lon: float) -> tuple[str, str, float]:
        import math

        best_id, best_name, best_d = "", "", 1e12
        for j in self.network.junctions.values():
            la = math.radians((lat + j.lat) / 2)
            d = math.hypot((j.lat - lat) * 111_320.0, (j.lon - lon) * 111_320.0 * math.cos(la))
            if d < best_d:
                best_id, best_name, best_d = j.junction_id, j.name, d
        return best_id, best_name, best_d

    def _worth_raising(self, cluster: ChokeCluster) -> bool:
        """Does this deserve an officer's attention at all?

        Google marks short stretches SLOW on roads that are running perfectly
        well — a bus stop, a turn, a pedestrian crossing. Raising those produced
        four incidents whose corridors were BELOW their typical travel time,
        which is the fastest way to teach a duty officer to ignore the feed.

        So a choke earns an incident when the road it sits on is genuinely
        slower than typical, or when traffic has actually stopped.
        """
        worst_index = max(
            (st.index or 1.0 for c in cluster.corridors if (st := self.status.get(c))),
            default=1.0,
        )
        if cluster.severity == "TRAFFIC_JAM":
            # A jam still has to be doing something to the journey.
            return worst_index >= self.thresholds.clear or cluster.worst_share >= 0.25
        return worst_index >= self.thresholds.elevated

    def _priority(self, cluster: ChokeCluster, corridors: list[str]) -> Priority:
        worst_index = max(
            (st.index or 1.0 for c in corridors if (st := self.status.get(c))), default=1.0
        )
        jam = cluster.severity == "TRAFFIC_JAM"
        if jam and (cluster.corroboration >= 2 or worst_index >= self.thresholds.severe):
            return Priority.P1
        if jam or worst_index >= self.thresholds.high:
            return Priority.P2
        if worst_index >= self.thresholds.elevated:
            return Priority.P3
        return Priority.P4

    def _existing_near(self, lat: float, lon: float) -> Incident | None:
        """Find an incident already covering this spot.

        A jam is not a fixed point: its extent grows and shrinks between polls,
        so the cluster centroid moves tens of metres each cycle. Keying
        incidents on a hash of the rounded coordinate therefore spawned a fresh
        incident for the same jam every few minutes — the handover showed the
        same stretch of NH10 three times, and a duty officer would have
        dispatched three times.

        Matching by proximity is what an officer means by "the same problem".
        """
        best: Incident | None = None
        best_d = MATCH_RADIUS_M
        for incident in self.incidents.values():
            if incident.kind is not IncidentKind.CHOKE_POINT or not incident.is_open:
                continue
            d = metres((lat, lon), (incident.lat, incident.lon))
            if d < best_d:
                best, best_d = incident, d
        return best

    def _raise_incidents(self, clusters: list[ChokeCluster], now: datetime) -> list[str]:
        # Why a cluster did not become an incident is as important as the fact.
        # An empty queue under a red headline reads as a broken screen unless
        # the interface can say which gate stopped it.
        self.suppressed = {"holding": 0, "below_threshold": 0, "quiet_hours": 0, "budget": 0}
        raised: list[str] = []
        for cluster in clusters:
            lat, lon = cluster.centre

            existing = self._existing_near(lat, lon)
            if existing is not None:
                existing.last_seen_at = now
                continue  # last_seen is refreshed every cycle; not worth a write

            iid = incident_id(IncidentKind.CHOKE_POINT, lat, lon, now)
            revived = self.incidents.get(iid)
            if revived is not None:
                revived.last_seen_at = now
                if revived.state is IncidentState.LAPSED:
                    revived.move(IncidentState.ACKNOWLEDGED, "system", "condition returned", at=now)
                continue

            # A condition must hold before it becomes an officer's problem —
            # and holding is measured on the condition, not on a coordinate.
            first = self._confirm_candidate(lat, lon, cluster.severity, now)
            if first is None:
                self.suppressed["holding"] += 1
                continue

            if not self._worth_raising(cluster):
                self.suppressed["below_threshold"] += 1
                continue

            # Overnight there is nobody to send. The condition is still tracked
            # and appears in the handover, but it does not become an incident
            # demanding an owner who does not exist. Alerting into an empty
            # control room trains people to ignore the feed.
            if _is_quiet(now):
                self.suppressed["quiet_hours"] += 1
                continue

            priority = self._priority(cluster, cluster.corridors)
            if not self._within_budget(priority):
                self.suppressed["budget"] += 1
                continue

            jid, jname, dist = self._nearest_junction(lat, lon)
            roads = next(
                (
                    r.roads
                    for c in cluster.corridors
                    if (st := self.status.get(c)) is not None
                    and (r := st.latest) is not None
                    and r.roads
                ),
                "",
            )
            where = f"{roads}, near {jname}" if roads else f"near {jname}"
            junction = self.network.junctions[jid]

            incident = Incident(
                incident_id=iid,
                kind=IncidentKind.CHOKE_POINT,
                priority=priority,
                title=(
                    f"{'Stopped traffic' if cluster.severity == 'TRAFFIC_JAM' else 'Slow traffic'}"
                    f" on {roads or 'the network'} near {jname}"
                ),
                detail=(
                    f"{cluster.length_m:.0f} m affected, "
                    f"{cluster.worst_share:.0%} of the corridor, "
                    f"seen from {cluster.corroboration} "
                    f"corridor{'s' if cluster.corroboration != 1 else ''}."
                ),
                location_name=where,
                lat=lat,
                lon=lon,
                corridors=cluster.corridors,
                junctions=[jid],
                detected_at=first,
                evidence={
                    "severity": cluster.severity,
                    "length_m": round(cluster.length_m),
                    "share_of_corridor": round(cluster.worst_share, 3),
                    "corroborating_corridors": cluster.corroboration,
                    "worst_index": round(
                        max(
                            (
                                st.index or 1.0
                                for c in cluster.corridors
                                if (st := self.status.get(c))
                            ),
                            default=1.0,
                        ),
                        3,
                    ),
                    "distance_to_junction_m": round(dist),
                    "junction_vc_ratio_2011": junction.vc_ratio,
                    "junction_pin": junction.match_quality,
                },
                limitation=(
                    "Location comes from Google traffic data on the route polyline. "
                    "It shows where traffic is slow, not why. "
                    + (
                        "The nearest junction pin is approximate. "
                        if junction.pin_is_approximate
                        else ""
                    )
                    + "No cause is known until an officer reports one."
                ),
                last_seen_at=now,
            )
            self.incidents[iid] = incident
            self.remember(incident)
            raised.append(iid)
        return raised

    def _confirm_candidate(
        self, lat: float, lon: float, severity: str, now: datetime
    ) -> datetime | None:
        """Track how long this condition has persisted; None until it qualifies.

        The previous version keyed candidates on `incident_id`, which hashes the
        coordinate rounded to four decimals — about eleven metres. A queue whose
        tail grows moves further than that between polls, so every poll minted a
        fresh key, restarted the clock, and the condition never confirmed. A
        simulation of two hours of continuous stopped traffic raised nothing and
        left forty orphan keys behind.

        Every queue worth dispatching to is growing. So candidates are matched
        the way an officer would match them — by being in the same place — and
        the position is updated while `first_seen` is kept.
        """
        for candidate in self._candidates:
            if metres((lat, lon), (candidate.lat, candidate.lon)) <= MATCH_RADIUS_M:
                candidate.lat, candidate.lon = lat, lon
                candidate.last_seen = now
                if severity == "TRAFFIC_JAM":
                    candidate.severity = severity
                if now - candidate.first_seen >= self.confirm_after:
                    return candidate.first_seen
                return None

        self._candidates.append(
            _Candidate(lat=lat, lon=lon, severity=severity, first_seen=now, last_seen=now)
        )
        return None if self.confirm_after > timedelta(0) else now

    def _prune_candidates(self, now: datetime) -> None:
        """Forget conditions that stopped being observed.

        Without this the list grew by one entry per poll forever, which on a
        service that runs for weeks is a slow leak in a process that must not
        be restarted casually.
        """
        self._candidates = [c for c in self._candidates if now - c.last_seen < LAPSE_AFTER]

    def _within_budget(self, priority: Priority) -> bool:
        """Whether this condition may be raised given how full the queue is.

        The old rule admitted anything that outranked the weakest thing already
        waiting, and never removed the weakest — so a queue capped at five grew
        to six and then further, one priority step at a time, while the screen
        showed "6/5" as though the counter were broken.

        Hiding a genuine severe condition because a counter is full is the
        wrong failure, so the cap now bites only on the low end: below it
        anything may be raised, at or above it only P1 and P2 get through. A
        queue past its budget means the shift is overloaded, which the board
        states rather than conceals.
        """
        unowned = sum(1 for i in self.incidents.values() if i.needs_attention)
        if unowned < self.alert_budget:
            return True
        return priority in (Priority.P1, Priority.P2)

    def _age_incidents(self, now: datetime) -> list[str]:
        lapsed: list[str] = []
        for iid, incident in self.incidents.items():
            if not incident.needs_attention:
                continue
            last = incident.last_seen_at or incident.detected_at
            if now - last >= LAPSE_AFTER:
                incident.lapse(at=now)
                self.remember(incident)
                lapsed.append(iid)
        return lapsed

    # ── views ────────────────────────────────────────────────────────────────
    def board(self, now: datetime | None = None) -> dict:
        moment = now or self.last_poll or datetime.now()
        bands: dict[str, int] = {}
        for s in self.status.values():
            bands[s.band] = bands.get(s.band, 0) + 1

        open_incidents = sorted(
            (i for i in self.incidents.values() if i.is_open),
            key=lambda i: (
                {"P1": 0, "P2": 1, "P3": 2, "P4": 3}[i.priority.value],
                -i.age_minutes(moment),
            ),
        )
        return {
            "at": moment.isoformat(timespec="seconds"),
            "cycle": self.cycles,
            "is_live": True,
            "bands": bands,
            "headline": self._headline(bands, open_incidents),
            "alert_budget": self.alert_budget,
            "over_budget": sum(1 for i in self.incidents.values() if i.needs_attention)
            > self.alert_budget,
            "suppressed": dict(self.suppressed),
            "candidates_holding": len(self._candidates),
            "unowned": sum(1 for i in self.incidents.values() if i.needs_attention),
            "incidents": [i.as_dict(moment) for i in open_incidents],
            "corridors": [
                {
                    "corridor_id": s.corridor_id,
                    "name": s.name,
                    "band": s.band,
                    "index": round(s.index, 3) if s.index is not None else None,
                    "excess_minutes": round(s.latest.excess_minutes, 1) if s.latest else None,
                    "duration_minutes": round(s.latest.duration_s / 60, 1) if s.latest else None,
                    "typical_minutes": round(s.latest.static_duration_s / 60, 1)
                    if s.latest
                    else None,
                    "roads": s.latest.roads if s.latest else "",
                    "trend_per_10min": round(t, 3) if (t := s.trend()) is not None else None,
                    "held_minutes": round(s.held_for(moment).total_seconds() / 60, 1),
                    "speed_kmh": round(s.latest.mean_speed_kmh, 1) if s.latest else None,
                    "choke_points": [
                        c.as_dict() for c in (s.latest.choke_points if s.latest else ())
                    ],
                    # The carriageway Google routed over, split at every change
                    # of traffic classification. This is what lets the map draw
                    # the road instead of a line between two dots.
                    "runs": [r.as_dict() for r in (s.latest.speed_runs if s.latest else ())],
                    "observed_at": s.latest.observed_at.isoformat(timespec="seconds")
                    if s.latest
                    else None,
                    "approximate_location": self.network.corridors[
                        s.corridor_id
                    ].located_approximately,
                }
                for s in sorted(self.status.values(), key=lambda x: -(x.index or 0))
            ],
        }

    @staticmethod
    def _headline(bands: dict[str, int], open_incidents: list[Incident]) -> str:
        severe = bands.get("SEVERE", 0)
        high = bands.get("HIGH", 0)
        elevated = bands.get("ELEVATED", 0)
        p1 = sum(1 for i in open_incidents if i.priority is Priority.P1)
        waiting = sum(1 for i in open_incidents if i.needs_attention)

        # Counting P1 only said "2 incidents needing action now" while six sat
        # unowned. The headline is the one line an officer reads on sitting
        # down, and it must not undercount the queue behind it.
        if p1 and waiting > p1:
            others = waiting - p1
            return (
                f"{p1} incident{'s' if p1 > 1 else ''} needing action now, "
                f"and {others} more waiting for an officer."
            )
        if waiting:
            return f"{waiting} incident{'s' if waiting > 1 else ''} waiting for an officer."
        if severe or high:
            n = severe + high
            return f"{n} corridor{'s' if n > 1 else ''} well above typical travel time."
        if elevated:
            return f"{elevated} corridor{'s' if elevated > 1 else ''} slower than typical."
        return "Siliguri is moving at close to typical travel times."
