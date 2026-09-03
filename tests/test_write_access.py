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
import json
from datetime import datetime, timedelta
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

NOW = datetime(2026, 8, 30, 15, 0)
TOKEN = "test-officer-token-not-a-real-one"


def build(monkeypatch, **env):
    """Reimport the API with a given environment, since the gate reads it once."""
    for k in ("WRITE_TOKEN", "AUTH_MODE", "OFFICER_TOKENS"):
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
            assert "no officer tokens" in c.get("/health").json()["writes"]

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


class TestPerOfficerAttribution:
    """With one token per officer the record names a person, not a console."""

    TOKENS: ClassVar[dict] = {"tok-do": "DO-1", "tok-tg2": "TG-2"}

    @pytest.fixture
    def officers(self, monkeypatch):
        main, client = build(monkeypatch, OFFICER_TOKENS=json.dumps(self.TOKENS))
        with client as c:
            yield main, c

    def act(self, c, token, **body):
        return c.post(
            "/api/incidents/INC-TEST/acknowledge",
            json=body,
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_the_actor_comes_from_the_token(self, officers):
        _, c = officers
        r = self.act(c, "tok-tg2")
        assert r.status_code == 200, r.text
        assert r.json()["history"][-1]["by"] == "TG-2"

    def test_a_console_cannot_record_in_another_officers_name(self, officers):
        """The whole point. A claimed `by` must not override the credential."""
        _, c = officers
        r = self.act(c, "tok-tg2", by="DO-1")
        assert r.status_code == 200, r.text
        assert r.json()["history"][-1]["by"] == "TG-2", "the body overrode the token"

    def test_no_body_is_needed_when_the_token_identifies_the_officer(self, officers):
        _, c = officers
        assert self.act(c, "tok-do").status_code == 200

    def test_an_unknown_token_is_still_refused(self, officers):
        _, c = officers
        assert self.act(c, "tok-nobody").status_code == 401

    def test_health_reports_per_officer_attribution(self, officers):
        _, c = officers
        assert c.get("/health").json()["attribution"] == "per-officer"

    def test_the_shared_token_stops_working_once_officers_have_their_own(self, monkeypatch):
        """Otherwise it is a credential that writes without attribution, while
        /health advertises per-officer attribution."""
        _, client = build(
            monkeypatch,
            OFFICER_TOKENS=json.dumps(self.TOKENS),
            WRITE_TOKEN="the-old-room-token",
        )
        with client as c:
            r = c.post(
                "/api/incidents/INC-TEST/acknowledge",
                json={"by": "whoever"},
                headers={"Authorization": "Bearer the-old-room-token"},
            )
            assert r.status_code == 401, "the shared token bypassed attribution"
            assert c.get("/health").json()["attribution"] == "per-officer"

    def test_per_officer_tokens_still_work_alongside_a_stale_shared_secret(self, monkeypatch):
        _, client = build(
            monkeypatch,
            OFFICER_TOKENS=json.dumps(self.TOKENS),
            WRITE_TOKEN="the-old-room-token",
        )
        with client as c:
            r = c.post(
                "/api/incidents/INC-TEST/acknowledge",
                json={},
                headers={"Authorization": "Bearer tok-do"},
            )
            assert r.status_code == 200, r.text
            assert r.json()["history"][-1]["by"] == "DO-1"


class TestAttributionIsStatedHonestly:
    def test_a_shared_token_admits_it_cannot_name_a_person(self, gated):
        _, c = gated
        assert c.get("/health").json()["attribution"] == "shared"

    def test_a_shared_token_still_requires_a_claimed_actor(self, gated):
        """Degraded mode: the server cannot name the officer, so it insists the
        console does, rather than recording an action by nobody."""
        _, c = gated
        r = c.post(
            "/api/incidents/INC-TEST/acknowledge",
            json={},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert r.status_code == 422

    def test_open_mode_reports_no_attribution(self, monkeypatch):
        _, client = build(monkeypatch, AUTH_MODE="open")
        with client as c:
            assert c.get("/health").json()["attribution"] == "none"
