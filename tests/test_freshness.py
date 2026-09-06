"""The freshness guarantee: a dead Google feed can never sit behind a green
"LIVE" badge, and a cold instance never declares the city clear.

This is the founder's stated fear made into a test. last_poll advances on every
cycle whether or not data arrived; the board's liveness must derive from
last_read_ok, which advances only when a read actually succeeded.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from packages.command.centre import CommandCentre
from packages.history.store import MemoryHistoryStore
from packages.incidents.model import Incident, IncidentKind, Priority
from packages.network.model import load_network
from packages.network.probe import CorridorReading

NOW = datetime(2026, 9, 1, 12, 0)


class LiveProbe:
    name, is_live, retains_durations = "live", True, False

    def __init__(self, index: float = 1.1):
        self.index = index
        self.fail = False

    def read(self, corridor, a, b, now):
        if self.fail:
            return None
        return CorridorReading(
            corridor_id=corridor.corridor_id,
            observed_at=now,
            duration_s=120 * self.index,
            static_duration_s=120,
            distance_m=2000,
            roads="Rd",
        )

    def provenance(self):
        return {"source": "live"}


def _centre(probe=None):
    return CommandCentre(
        network=load_network(),
        probe=probe or LiveProbe(),
        history_store=MemoryHistoryStore(),
    )


class TestFeedState:
    def test_cold_centre_is_warming_not_live(self):
        c = _centre()
        h = c.feed_health(NOW)
        assert h["state"] == "WARMING" and h["is_live"] is False
        assert "Warming up" in c.board(NOW)["headline"]

    def test_a_good_cycle_goes_live(self):
        c = _centre()
        c.poll(NOW)
        b = c.board(NOW)
        assert b["data_state"] == "LIVE" and b["is_live"] is True
        assert c.last_read_ok == NOW

    def test_a_dead_feed_goes_stale_not_live(self):
        # Steps are >= the 15-min NORMAL cadence so corridors are actually DUE on
        # each failing cycle — that is when a dead feed reveals itself.
        probe = LiveProbe()
        c = _centre(probe)
        c.poll(NOW)  # one good cycle
        assert c.board(NOW)["is_live"] is True
        # feed dies: every due read now returns None
        probe.fail = True
        c.poll(NOW + timedelta(minutes=16))
        c.poll(NOW + timedelta(minutes=32))  # second consecutive full failure
        b = c.board(NOW + timedelta(minutes=32))
        assert b["data_state"] == "STALE"
        assert b["is_live"] is False, "a dead feed must never read as live"
        # last_poll advanced, but last_read_ok did NOT — the whole point
        assert c.last_poll == NOW + timedelta(minutes=32)
        assert c.last_read_ok == NOW

    def test_stale_board_headline_warns_not_reassures(self):
        probe = LiveProbe()
        c = _centre(probe)
        c.poll(NOW)
        probe.fail = True
        c.poll(NOW + timedelta(minutes=16))
        c.poll(NOW + timedelta(minutes=32))
        assert "interrupted" in c.board(NOW + timedelta(minutes=32))["headline"].lower()

    def test_feed_recovers_back_to_live(self):
        probe = LiveProbe()
        c = _centre(probe)
        c.poll(NOW)
        probe.fail = True
        c.poll(NOW + timedelta(minutes=16))
        c.poll(NOW + timedelta(minutes=32))
        assert c.board(NOW + timedelta(minutes=32))["is_live"] is False
        probe.fail = False
        c.poll(NOW + timedelta(minutes=48))  # a good read arrives
        assert c.board(NOW + timedelta(minutes=48))["is_live"] is True


class TestHeadlinePriority:
    """The feed-state message must never bury a queue of waiting incidents."""

    def _centre_with_waiting(self):
        c = _centre()  # NOT polled — so feed is WARMING
        i = Incident(
            incident_id="INC-W",
            kind=IncidentKind.CHOKE_POINT,
            priority=Priority.P1,
            title="Slow",
            detail="d",
            location_name="NH10",
            lat=26.7,
            lon=88.4,
            corridors=["C"],
            junctions=["J"],
            detected_at=NOW - timedelta(minutes=5),
            evidence={},
            limitation="x",
        )
        c.incidents["INC-W"] = i
        return c

    def test_waiting_incident_wins_over_warming(self):
        c = self._centre_with_waiting()
        headline = c.board(NOW)["headline"]
        assert "waiting" in headline.lower() or "action now" in headline.lower()
        assert "Warming" not in headline
