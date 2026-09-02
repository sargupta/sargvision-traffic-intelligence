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
from typing import ClassVar

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


class TestTheSuiteCannotSpendTheMapsBudget:
    """Startup must not replace an injected centre with a live probe.

    It used to. The stub below was constructed, TestClient entered, and the
    lifespan overwrote it with a RoutesProbe and started the poll loop — so
    every CI run made outbound calls to a metered API that is ~88% of this
    system's running cost, and the stubbed no-data path was never exercised.
    """

    def test_startup_keeps_the_injected_centre(self, client):
        from apps.api import main

        assert type(main.STATE["centre"].probe).__name__ == "StubProbe", (
            "startup replaced the test centre with a live probe"
        )

    def test_the_live_probe_is_not_constructed_under_test(self, client):
        from apps.api import main

        assert not main.STATE["centre"].probe.is_live


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

    def test_the_browser_preflight_permits_the_officer_token(self, client):
        """A curl-only smoke test cannot see this one.

        An Authorization header makes the browser preflight the request. When
        allow_headers omitted Authorization the preflight came back 400
        "Disallowed CORS headers", so every write from the control room failed
        while every curl against the same endpoint succeeded — the same shape
        as the dropped CORS_ORIGINS incident.
        """
        r = client.options(
            "/api/incidents/INC-NOPE/acknowledge",
            headers={
                "Origin": "http://localhost:3050",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert r.status_code == 200, r.text
        allowed = r.headers.get("access-control-allow-headers", "").lower()
        assert "authorization" in allowed, allowed

    def test_cors_does_not_default_to_wildcard(self):
        from apps.api import main

        assert "*" not in main._ORIGINS, "a missing CORS_ORIGINS must fail closed"


class TestIncidentActions:
    """The gate runs before the lookup, and that ordering is the point.

    These two used to assert 404 for an unauthenticated caller, which meant an
    anonymous request could tell a real incident id from an invented one and
    enumerate the register. Authentication first collapses both to 401.
    """

    AUTH: ClassVar[dict] = {"Authorization": "Bearer test-officer-token"}

    def _gated(self, client, path, **kw):
        from apps.api import main

        main.AUTH_MODE, main.WRITE_TOKEN = "token", "test-officer-token"
        try:
            return client.post(path, json={"by": "DO-1"}, **kw)
        finally:
            main.AUTH_MODE = "open"

    def test_an_unauthenticated_action_is_401(self, client):
        assert self._gated(client, "/api/incidents/INC-NOPE/acknowledge").status_code == 401

    def test_an_unauthenticated_caller_cannot_enumerate_incident_ids(self, client):
        """A real id and an invented one must be indistinguishable without a token."""
        real = self._gated(client, "/api/incidents/INC-NOPE/acknowledge").status_code
        fake = self._gated(client, "/api/incidents/INC-ALSO-NOPE/acknowledge").status_code
        assert real == fake == 401

    def test_unknown_incident_is_404_once_authenticated(self, client):
        r = self._gated(client, "/api/incidents/INC-NOPE/acknowledge", headers=self.AUTH)
        assert r.status_code == 404

    def test_unknown_action_is_404_once_authenticated(self, client):
        r = self._gated(client, "/api/incidents/INC-NOPE/teleport", headers=self.AUTH)
        assert r.status_code == 404


class TestPollingEconomy:
    """Cadence follows condition. This is both the API bill and the signal quality."""

    def test_quiet_hours_are_the_night(self):
        from datetime import datetime

        from packages.command.centre import _is_quiet

        assert _is_quiet(datetime(2026, 8, 30, 2, 0))
        assert _is_quiet(datetime(2026, 8, 30, 23, 30))
        assert not _is_quiet(datetime(2026, 8, 30, 9, 0))
        assert not _is_quiet(datetime(2026, 8, 30, 19, 0))

    def test_a_quiet_corridor_is_asked_less_often_than_a_failing_one(self):
        from packages.command.centre import CADENCE

        assert CADENCE["NORMAL"] > CADENCE["ELEVATED"] > CADENCE["HIGH"]

    def test_a_corridor_is_not_polled_before_it_is_due(self):
        from datetime import datetime, timedelta

        from packages.command.centre import CorridorStatus

        s = CorridorStatus(corridor_id="C_X", name="x")
        now = datetime(2026, 8, 30, 12, 0)
        assert s.is_due(now), "never-read corridors must be due immediately"
        s.band = "NORMAL"
        s.schedule(now)
        assert not s.is_due(now + timedelta(minutes=5))
        assert s.is_due(now + timedelta(minutes=16))

    def test_a_failing_corridor_comes_due_quickly(self):
        from datetime import datetime, timedelta

        from packages.command.centre import CorridorStatus

        s = CorridorStatus(corridor_id="C_X", name="x")
        now = datetime(2026, 8, 30, 12, 0)
        s.band = "HIGH"
        s.schedule(now)
        assert s.is_due(now + timedelta(minutes=4))

    def test_night_conditions_do_not_become_incidents(self):
        """There is no sergeant to send at 02:00. Alerting into an empty control
        room is how a feed gets ignored."""
        from datetime import datetime, timedelta

        from packages.command.centre import CommandCentre
        from packages.incidents.cluster import ChokeCluster
        from packages.network.model import load_network
        from packages.network.probe import ChokePoint

        class Stub:
            name, is_live, retains_durations = "stub", False, False

            def read(self, *a, **k):
                return None

            def provenance(self):
                return {}

        centre = CommandCentre(network=load_network(), probe=Stub())
        centre.confirm_after = timedelta(0)
        for st in centre.status.values():
            st.band = "HIGH"
        cluster = ChokeCluster(
            centre=(26.7245, 88.4156),
            severity="TRAFFIC_JAM",
            members=[
                (
                    "C_X",
                    ChokePoint(
                        severity="TRAFFIC_JAM",
                        start=(26.7245, 88.4156),
                        end=(26.7246, 88.4157),
                        midpoint=(26.7245, 88.4156),
                        length_m=400.0,
                        share_of_corridor=0.4,
                    ),
                )
            ],
        )
        at_night = centre._raise_incidents([cluster], datetime(2026, 8, 30, 2, 30))
        assert at_night == []
        by_day = centre._raise_incidents([cluster], datetime(2026, 8, 30, 10, 30))
        assert len(by_day) == 1
