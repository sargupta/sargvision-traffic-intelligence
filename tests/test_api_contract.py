"""Endpoints that must not break, and one that did.

Every route the interface depends on is exercised here against a stubbed probe.
The handover test exists because a timezone fix renamed a local and left one
reference pointing at the function object instead of calling it — the endpoint
returned 500 in production for the better part of an hour, and nothing caught
it because it had been tested before the change and not after.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ROUTES_API_KEY", "test-key-not-used")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3050")


@pytest.fixture(scope="module")
def client():
    from apps.api import main
    from packages.command.centre import CommandCentre
    from packages.network.model import load_network

    class StubProbe:
        name, is_live, retains_durations = "stub", False, False
        def read(self, *a, **k):
            return None
        def provenance(self):
            return {"source": "stub"}

    main.STATE["centre"] = CommandCentre(network=load_network(), probe=StubProbe())
    main.STATE["centre"].last_poll = datetime(2026, 8, 30, 16, 0)
    main.STATE["started_at"] = datetime(2026, 8, 30, 9, 0)
    with TestClient(main.app) as c:
        yield c


class TestEveryRouteTheUIDependsOn:
    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/api/board",
            "/api/network",
            "/api/roster",
            "/api/incidents",
            "/api/shift/handover?hours=8",
            "/api/city-profile?day_type=WEEKDAY",
        ],
    )
    def test_returns_200(self, client, path):
        assert client.get(path).status_code == 200, f"{path} must not break"

    def test_handover_returns_a_usable_record(self, client):
        """The regression. This endpoint returned 500 in production."""
        body = client.get("/api/shift/handover?hours=8").json()
        assert "handing_over" in body
        assert "needs_an_owner" in body["handing_over"]
        assert "alerting_quality" in body
        assert set(body["this_shift"]) == {"closed", "stood_down", "lapsed"}

    def test_handover_window_is_honoured(self, client):
        body = client.get("/api/shift/handover?hours=4").json()
        start = datetime.fromisoformat(body["from"])
        end = datetime.fromisoformat(body["to"])
        assert end - start == timedelta(hours=4)


class TestOperationalSecurity:
    def test_roster_does_not_leak_officer_names(self, client):
        """A public list of who is on duty maps where enforcement is absent."""
        body = client.get("/api/roster").json()
        served = " ".join(o["name"] for o in body["officers"])
        for real_name in ("Barman", "Chhetri", "Roy", "Lama", "Sarkar"):
            assert real_name not in served, f"{real_name} must not be served unauthenticated"

    def test_roster_does_not_leak_duty_state(self, client):
        body = client.get("/api/roster").json()
        assert all(o["on_duty"] for o in body["officers"]), "duty state must not be public"

    def test_cors_does_not_default_to_wildcard(self):
        from apps.api import main
        assert "*" not in main._ORIGINS, "a missing CORS_ORIGINS must fail closed"


class TestIncidentActions:
    def test_unknown_incident_is_404(self, client):
        r = client.post("/api/incidents/INC-NOPE/acknowledge", json={"by": "DO-1"})
        assert r.status_code == 404

    def test_unknown_action_is_404(self, client):
        r = client.post("/api/incidents/INC-NOPE/teleport", json={"by": "DO-1"})
        assert r.status_code == 404
