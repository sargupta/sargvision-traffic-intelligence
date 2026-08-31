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
            def read(self, *a, **k): return None
            def provenance(self): return {}

        centre = CommandCentre(network=load_network(), probe=Stub())
        centre.confirm_after = timedelta(0)
        for st in centre.status.values():
            st.band = "HIGH"
        cluster = ChokeCluster(
            centre=(26.7245, 88.4156), severity="TRAFFIC_JAM",
            members=[("C_X", ChokePoint(
                severity="TRAFFIC_JAM", start=(26.7245, 88.4156), end=(26.7246, 88.4157),
                midpoint=(26.7245, 88.4156), length_m=400.0, share_of_corridor=0.4))],
        )
        at_night = centre._raise_incidents([cluster], datetime(2026, 8, 30, 2, 30))
        assert at_night == []
        by_day = centre._raise_incidents([cluster], datetime(2026, 8, 30, 10, 30))
        assert len(by_day) == 1
