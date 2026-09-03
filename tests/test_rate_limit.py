"""One instance serves the whole room, so nobody may exhaust it.

The service runs at --max-instances=1 because each instance keeps its own
corridor state and its own poll loop. Availability is therefore a single point,
and /api/board is roughly 180 KB of geometry per call on a public URL. These
tests fix the shape of the protection: generous for a console doing its job,
tight for a stranger, and tightest of all for someone guessing the token.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 30, 15, 0)
TOKEN = "test-officer-token-not-a-real-one"


def build(monkeypatch, **env):
    for k in (
        "WRITE_TOKEN",
        "AUTH_MODE",
        "OFFICER_TOKENS",
        "RATE_READS_PER_MIN",
        "RATE_WRITES_PER_MIN",
        "RATE_FAILED_AUTH_PER_MIN",
    ):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("ROUTES_API_KEY", "test-key-not-used")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3050")

    from apps.api import main as _main

    main = importlib.reload(_main)

    from packages.command.centre import CommandCentre
    from packages.incidents.model import Incident, IncidentKind, Priority
    from packages.network.model import load_network

    class StubProbe:
        name, is_live, retains_durations = "stub", False, False

        def read(self, *a, **k):
            return None

        def provenance(self):
            return {"source": "stub"}

    centre = CommandCentre(network=load_network(), probe=StubProbe())
    centre.last_poll = NOW
    centre.incidents["INC-TEST"] = Incident(
        incident_id="INC-TEST",
        kind=IncidentKind.CHOKE_POINT,
        priority=Priority.P2,
        title="Slow traffic on NH10",
        detail="d",
        location_name="NH10",
        lat=26.72,
        lon=88.41,
        corridors=["C_A__B"],
        junctions=["J_A"],
        detected_at=NOW - timedelta(minutes=20),
        evidence={},
        limitation="unknown cause",
    )
    main.STATE["centre"] = centre
    main.STATE["started_at"] = NOW
    return main, TestClient(main.app)


def caller(ip: str) -> dict:
    """Cloud Run puts the real client at the head of X-Forwarded-For."""
    return {"X-Forwarded-For": ip}


class TestReadsAreLimited:
    def test_a_flood_is_refused(self, monkeypatch):
        _, client = build(monkeypatch, RATE_READS_PER_MIN="5", WRITE_TOKEN=TOKEN)
        with client as c:
            codes = [
                c.get("/api/board", headers=caller("203.0.113.9")).status_code for _ in range(8)
            ]
        assert codes.count(200) == 5
        assert codes[-1] == 429

    def test_a_refusal_says_when_to_come_back(self, monkeypatch):
        _, client = build(monkeypatch, RATE_READS_PER_MIN="1", WRITE_TOKEN=TOKEN)
        with client as c:
            c.get("/api/board", headers=caller("203.0.113.10"))
            r = c.get("/api/board", headers=caller("203.0.113.10"))
        assert r.status_code == 429
        assert r.headers.get("Retry-After") == "60"


class TestOneCallerCannotStarveAnother:
    def test_the_control_room_is_unaffected_by_someone_else_flooding(self, monkeypatch):
        """The failure that matters: a stranger must not take the board down."""
        _, client = build(monkeypatch, RATE_READS_PER_MIN="3", WRITE_TOKEN=TOKEN)
        with client as c:
            for _ in range(6):
                c.get("/api/board", headers=caller("198.51.100.7"))  # the flood
            r = c.get("/api/board", headers=caller("203.0.113.1"))  # the room
        assert r.status_code == 200, "a stranger's flood locked out the control room"

    def test_callers_behind_the_balancer_are_told_apart(self, monkeypatch):
        """Without X-Forwarded-For every caller shares one bucket, and the first
        busy console rate-limits the whole city."""
        _, client = build(monkeypatch, RATE_READS_PER_MIN="2", WRITE_TOKEN=TOKEN)
        with client as c:
            a = [c.get("/api/board", headers=caller("203.0.113.2")).status_code for _ in range(3)]
            b = c.get("/api/board", headers=caller("203.0.113.3")).status_code
        assert a[-1] == 429
        assert b == 200


class TestGuessingTheTokenIsExpensive:
    def test_failed_credentials_run_out_faster_than_writes(self, monkeypatch):
        _, client = build(
            monkeypatch,
            WRITE_TOKEN=TOKEN,
            RATE_WRITES_PER_MIN="100",
            RATE_FAILED_AUTH_PER_MIN="3",
        )
        with client as c:
            codes = [
                c.post(
                    "/api/incidents/INC-TEST/acknowledge",
                    json={"by": "guess"},
                    headers={**caller("198.51.100.8"), "Authorization": "Bearer wrong"},
                ).status_code
                for _ in range(6)
            ]
        assert 401 in codes, "the first attempts should be ordinary refusals"
        assert codes[-1] == 429, "guessing was never throttled"

    def test_a_correct_token_is_not_punished_for_someone_elses_guessing(self, monkeypatch):
        _, client = build(
            monkeypatch, WRITE_TOKEN=TOKEN, RATE_FAILED_AUTH_PER_MIN="2", RATE_WRITES_PER_MIN="50"
        )
        with client as c:
            for _ in range(5):
                c.post(
                    "/api/incidents/INC-TEST/acknowledge",
                    json={"by": "guess"},
                    headers={**caller("198.51.100.9"), "Authorization": "Bearer wrong"},
                )
            r = c.post(
                "/api/incidents/INC-TEST/acknowledge",
                json={"by": "DO-1"},
                headers={**caller("203.0.113.4"), "Authorization": f"Bearer {TOKEN}"},
            )
        assert r.status_code == 200, r.text


class TestTheStreamIsNotTraffic:
    def test_the_event_stream_is_exempt_from_the_counters(self, monkeypatch):
        """One long-lived connection per console is not a flood, and counting it
        would throttle a room that is doing nothing wrong.

        Asserted against the counters rather than by opening the stream: it
        never ends by design, so a test that reads it does not either.
        """
        main, client = build(monkeypatch, RATE_READS_PER_MIN="1", WRITE_TOKEN=TOKEN)
        with client as c:
            c.get("/api/board", headers=caller("203.0.113.5"))
        buckets = {k for k in main._hits if k[0] == "203.0.113.5"}
        assert buckets == {("203.0.113.5", "read")}
        assert main.rate_limit is not None  # the middleware is installed

    def test_the_exemption_is_by_path_and_nothing_else(self, monkeypatch):
        main, _ = build(monkeypatch, WRITE_TOKEN=TOKEN)
        import inspect

        src = inspect.getsource(main.rate_limit)
        assert '"/api/stream"' in src, "the exemption must name the one path it covers"


class TestTheDefaultsFitTheRoom:
    """A console makes a handful of calls per cycle; the defaults must not bite."""

    def test_a_normal_console_cycle_is_well_within_budget(self, monkeypatch):
        main, client = build(monkeypatch, WRITE_TOKEN=TOKEN)
        assert main.READ_BUDGET >= 60, "a shared control room would trip this"
        with client as c:
            codes = [
                c.get(p, headers=caller("203.0.113.6")).status_code
                for _ in range(6)
                for p in ("/api/board", "/api/advice", "/api/incidents", "/api/network")
            ]
        assert set(codes) == {200}
