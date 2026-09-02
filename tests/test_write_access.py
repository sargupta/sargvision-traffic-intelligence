"""Nobody records a police action without a credential.

Before the gate these tests describe, the deployed API published real incident
ids at GET /api/incidents and accepted POST /api/incidents/{id}/{action} from
anyone on the internet — verified against production, which answered the
application's own 404 rather than a 401. With a Firestore store behind it, a
stranger could have stood down or closed a live incident permanently.

Reads stay open on purpose: the board's figures are aggregates and /api/roster
already withholds names and duty state. Writes are the asymmetry — an accepted
anonymous record is worse than a refused genuine one, so the gate fails closed.
"""

from __future__ import annotations

import importlib
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 30, 15, 0)
TOKEN = "test-officer-token-not-a-real-one"


def build(monkeypatch, **env):
    """Reimport the API with a given environment, since the gate reads it once."""
    for k in ("WRITE_TOKEN", "AUTH_MODE"):
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


@pytest.fixture
def gated(monkeypatch):
    main, client = build(monkeypatch, WRITE_TOKEN=TOKEN)
    with client as c:
        yield main, c


class TestAnonymousWritesAreRefused:
    def test_no_header_is_401(self, gated):
        _, c = gated
        r = c.post("/api/incidents/INC-TEST/acknowledge", json={"by": "DO-1"})
        assert r.status_code == 401, r.text

    @pytest.mark.parametrize(
        "header",
        [
            "",
            "Bearer",
            "Bearer ",
            "Bearer wrong-token",
            f"Basic {TOKEN}",
            TOKEN,  # the raw token without the scheme
        ],
    )
    def test_a_malformed_or_wrong_credential_is_401(self, gated, header):
        _, c = gated
        r = c.post(
            "/api/incidents/INC-TEST/acknowledge",
            json={"by": "DO-1"},
            headers={"Authorization": header},
        )
        assert r.status_code == 401, f"{header!r} was accepted"

    def test_a_refused_write_changes_nothing(self, gated):
        main, c = gated
        c.post("/api/incidents/INC-TEST/acknowledge", json={"by": "intruder"})
        item = main.STATE["centre"].incidents["INC-TEST"]
        assert item.state.name == "DETECTED"
        assert item.history == []


class TestTheRightTokenWorks:
    def test_a_valid_bearer_token_records_the_action(self, gated):
        _, c = gated
        r = c.post(
            "/api/incidents/INC-TEST/acknowledge",
            json={"by": "DO-1"},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["state"] == "ACKNOWLEDGED"

    def test_the_scheme_is_accepted_case_insensitively(self, gated):
        _, c = gated
        r = c.post(
            "/api/incidents/INC-TEST/acknowledge",
            json={"by": "DO-1"},
            headers={"Authorization": f"bearer {TOKEN}"},
        )
        assert r.status_code == 200, r.text


class TestReadsStayOpen:
    """The board must still render for anyone who can reach it."""

    @pytest.mark.parametrize(
        "path", ["/health", "/api/board", "/api/incidents", "/api/network", "/api/roster"]
    )
    def test_a_read_needs_no_credential(self, gated, path):
        _, c = gated
        assert c.get(path).status_code == 200


class TestItFailsClosed:
    def test_with_no_token_configured_writes_are_refused_not_opened(self, monkeypatch):
        """The dangerous default. An unset secret must not mean 'let everyone in'."""
        main, client = build(monkeypatch)  # no WRITE_TOKEN at all
        with client as c:
            r = c.post("/api/incidents/INC-TEST/acknowledge", json={"by": "DO-1"})
            assert r.status_code == 503, r.text
            assert main.STATE["centre"].incidents["INC-TEST"].history == []

    def test_health_declares_that_recording_is_disabled(self, monkeypatch):
        _, client = build(monkeypatch)
        with client as c:
            assert "no WRITE_TOKEN" in c.get("/health").json()["writes"]

    def test_health_declares_a_gated_deployment(self, gated):
        _, c = gated
        assert c.get("/health").json()["writes"] == "gated"

    def test_open_mode_is_explicit_and_declares_itself(self, monkeypatch):
        """AUTH_MODE=open is for local development; it must never be quiet."""
        _, client = build(monkeypatch, AUTH_MODE="open")
        with client as c:
            assert (
                c.post("/api/incidents/INC-TEST/acknowledge", json={"by": "DO-1"}).status_code
                == 200
            )
            assert c.get("/health").json()["writes"].startswith("OPEN")
