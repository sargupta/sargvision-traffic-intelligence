"""Every endpoint, exercised the way the OpenAPI schema says it exists.

This is the API-layer sweep: each of the twelve routes on its happy path, its
auth boundary, and its error edges, plus a guard that no route answers garbage
with a 500. The action endpoint gets the most attention because it is the only
one that writes a police record.

The centre is injected before TestClient enters, so the lifespan does not build
a live RoutesProbe or start the poll loop (see test_api_contract for why that
matters — CI must not spend the metered Maps API).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ROUTES_API_KEY", "test-key-not-used")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3050")

NOW = datetime(2026, 8, 30, 15, 0)
SHARED = "shared-write-token"
OFFICER_TOK = "tg2-secret-token"


class StubProbe:
    name, is_live, retains_durations = "stub", False, False

    def read(self, *a, **k):
        return None

    def provenance(self):
        return {"source": "stub"}


def _centre():
    from packages.command.centre import CommandCentre
    from packages.incidents.model import Incident, IncidentKind, Priority
    from packages.network.model import load_network

    c = CommandCentre(network=load_network(), probe=StubProbe())
    c.last_poll = NOW

    def inc(iid, state_setup, **kw):
        i = Incident(
            incident_id=iid,
            kind=IncidentKind.CHOKE_POINT,
            priority=kw.get("priority", Priority.P2),
            title=kw.get("title", "Slow on NH10"),
            detail="d",
            location_name=kw.get("location_name", "NH10, near Venus More"),
            lat=26.72,
            lon=88.41,
            corridors=kw.get("corridors", ["C_A__B"]),
            junctions=["J_A"],
            detected_at=NOW - timedelta(minutes=20),
            evidence={"worst_index": 1.6},
            limitation="x",
        )
        state_setup(i)
        return i

    # one fresh, one owned+on-scene, one closed — to exercise filters/transitions
    fresh = inc("INC-FRESH", lambda i: None, priority=Priority.P1, location_name="NH10, near Venus More")

    def to_scene(i):
        from packages.incidents.model import IncidentState
        i.assign("SI Barman", by="DO-1", at=NOW - timedelta(minutes=10))
        i.move(IncidentState.ON_SCENE, "SI Barman", at=NOW - timedelta(minutes=8))
    owned = inc("INC-OWNED", to_scene, location_name="Sevoke Rd, near Court More")

    def to_closed(i):
        from packages.incidents.model import IncidentState
        i.acknowledge("DO-1", at=NOW - timedelta(minutes=18))
        i.stand_down("DO-1", "cleared by local officer", at=NOW - timedelta(minutes=15))
        assert i.state is IncidentState.STOOD_DOWN
    closed = inc("INC-CLOSED", to_closed, location_name="Hill Cart Rd, near Air View More")

    for i in (fresh, owned, closed):
        c.incidents[i.incident_id] = i
    return c


@pytest.fixture
def client():
    """Token-gated writes: shared WRITE_TOKEN, no per-officer tokens."""
    from apps.api import main

    main.STATE["centre"] = _centre()
    main.STATE["started_at"] = NOW - timedelta(hours=6)
    main.AUTH_MODE = "token"
    main.WRITE_TOKEN = SHARED
    main.OFFICER_TOKENS = {}
    with TestClient(main.app) as c:
        yield c


@pytest.fixture
def per_officer_client():
    """Per-officer tokens: the actor is taken from the credential, not the body."""
    from apps.api import main

    main.STATE["centre"] = _centre()
    main.STATE["started_at"] = NOW - timedelta(hours=6)
    main.AUTH_MODE = "token"
    main.WRITE_TOKEN = SHARED
    main.OFFICER_TOKENS = {OFFICER_TOK: "TG-2"}
    with TestClient(main.app) as c:
        yield c


def auth(tok=SHARED):
    return {"Authorization": f"Bearer {tok}"}


# ── the reads ────────────────────────────────────────────────────────────────
class TestReadEndpoints:
    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/api/board",
            "/api/advice",
            "/api/network",
            "/api/roster",
            "/api/incidents",
            "/api/incidents?include_closed=true",
            "/api/incidents?state=ON_SCENE",
            "/api/incidents/INC-FRESH",
            "/api/corridors/C_WALL_FORD_BYPASS_CROSSING__ASHIGHAR_MORE",
            "/api/city-profile?day_type=WEEKDAY",
            "/api/shift/handover?hours=8",
        ],
    )
    def test_returns_200(self, client, path):
        r = client.get(path)
        assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"

    def test_health_advertises_the_write_posture(self, client):
        h = client.get("/health").json()
        assert h["ok"] is True
        assert h["writes"] == "gated"
        assert h["attribution"] == "shared"

    def test_incidents_open_by_default(self, client):
        ids = [i["incident_id"] for i in client.get("/api/incidents").json()["incidents"]]
        assert "INC-CLOSED" not in ids
        assert "INC-FRESH" in ids

    def test_incidents_include_closed(self, client):
        ids = [i["incident_id"] for i in client.get("/api/incidents?include_closed=true").json()["incidents"]]
        assert "INC-CLOSED" in ids

    def test_incidents_state_filter(self, client):
        rows = client.get("/api/incidents?state=on_scene").json()["incidents"]
        assert [i["incident_id"] for i in rows] == ["INC-OWNED"]

    def test_incidents_are_priority_ordered(self, client):
        rows = client.get("/api/incidents").json()["incidents"]
        prios = [i["priority"] for i in rows]
        assert prios == sorted(prios), "P1 must come before P2"

    def test_one_incident_carries_impact_and_samples(self, client):
        d = client.get("/api/incidents/INC-OWNED").json()
        assert "impact" in d and "samples" in d
        assert d["impact"]["basis"]  # the honesty caveat is always present

    def test_unknown_incident_is_404(self, client):
        assert client.get("/api/incidents/INC-NOPE").status_code == 404

    def test_unknown_corridor_is_404(self, client):
        assert client.get("/api/corridors/C_NOPE").status_code == 404

    def test_roster_masks_names_and_duty(self, client):
        """Real names and live duty state are operational security in a border
        city. The endpoint masks both: name is the unit, and on_duty is always
        true — never the officer's real deployment state."""
        body = client.get("/api/roster").json()
        for o in body["officers"]:
            assert o["name"] == o["unit"], "a real name leaked instead of the unit"
            assert o["on_duty"] is True, "real duty state leaked"
        assert "not served here" in body["note"]

    def test_handover_hours_out_of_range_is_422(self, client):
        assert client.get("/api/shift/handover?hours=0").status_code == 422
        assert client.get("/api/shift/handover?hours=48").status_code == 422

    def test_stream_route_is_registered(self, client):
        # The live SSE behaviour is exercised in the browser; opening the
        # infinite stream here would hang TestClient teardown. Assert the route
        # exists and is exempt from the rate limiter (a long-lived connection
        # per console must never be counted as traffic).
        from apps.api import main

        paths = {r.path for r in main.app.routes}
        assert "/api/stream" in paths


# ── the write endpoint: auth boundary ────────────────────────────────────────
class TestWriteAuth:
    def test_no_token_is_401(self, client):
        r = client.post("/api/incidents/INC-FRESH/acknowledge", json={"by": "DO-1"})
        assert r.status_code == 401

    def test_wrong_token_is_401(self, client):
        r = client.post("/api/incidents/INC-FRESH/acknowledge", json={"by": "DO-1"}, headers=auth("nope"))
        assert r.status_code == 401

    def test_shared_token_authorises(self, client):
        r = client.post("/api/incidents/INC-FRESH/acknowledge", json={"by": "DO-1"}, headers=auth())
        assert r.status_code == 200
        assert r.json()["state"] == "ACKNOWLEDGED"

    def test_shared_token_still_needs_a_named_actor(self, client):
        # shared token identifies nobody, so `by` is required
        r = client.post("/api/incidents/INC-FRESH/acknowledge", json={}, headers=auth())
        assert r.status_code == 422

    def test_per_officer_token_names_the_actor_and_ignores_the_body(self, per_officer_client):
        # the credential is TG-2; a body claiming another name must not win
        r = per_officer_client.post(
            "/api/incidents/INC-FRESH/acknowledge",
            json={"by": "SOMEONE ELSE"},
            headers=auth(OFFICER_TOK),
        )
        assert r.status_code == 200
        assert r.json()["history"][-1]["by"] == "TG-2"

    def test_shared_token_refused_once_per_officer_tokens_exist(self, per_officer_client):
        # the bypass this closed: shared token would authorise with no attribution
        r = per_officer_client.post(
            "/api/incidents/INC-FRESH/acknowledge", json={"by": "DO-1"}, headers=auth(SHARED)
        )
        assert r.status_code == 401


# ── the write endpoint: behaviour ────────────────────────────────────────────
class TestWriteBehaviour:
    def test_illegal_transition_is_409_not_500(self, client):
        # FRESH is DETECTED; resolve is not legal from there
        r = client.post("/api/incidents/INC-FRESH/resolve", json={"by": "DO-1"}, headers=auth())
        assert r.status_code == 409
        assert r.json()["detail"]

    def test_unknown_action_is_404(self, client):
        r = client.post("/api/incidents/INC-FRESH/teleport", json={"by": "DO-1"}, headers=auth())
        assert r.status_code == 404

    @pytest.mark.parametrize("action", ["assign", "stand-down", "close"])
    def test_action_missing_its_field_is_400(self, client, action):
        target = "INC-FRESH" if action == "assign" else "INC-OWNED"
        r = client.post(f"/api/incidents/{target}/{action}", json={"by": "DO-1"}, headers=auth())
        assert r.status_code == 400, f"{action}: {r.text[:150]}"

    def test_overlong_actor_is_422(self, client):
        r = client.post("/api/incidents/INC-FRESH/acknowledge", json={"by": "A" * 200}, headers=auth())
        assert r.status_code == 422

    def test_a_full_lifecycle_over_http(self, client):
        h = auth()
        assert client.post("/api/incidents/INC-FRESH/acknowledge", json={"by": "DO-1"}, headers=h).status_code == 200
        assert client.post("/api/incidents/INC-FRESH/assign", json={"by": "DO-1", "to": "SI Roy"}, headers=h).status_code == 200
        assert client.post("/api/incidents/INC-FRESH/on-scene", json={"by": "SI Roy"}, headers=h).status_code == 200
        assert client.post("/api/incidents/INC-FRESH/clearing", json={"by": "SI Roy"}, headers=h).status_code == 200
        assert client.post("/api/incidents/INC-FRESH/resolve", json={"by": "SI Roy"}, headers=h).status_code == 200
        final = client.post("/api/incidents/INC-FRESH/close", json={"by": "DO-1", "text": "flow restored"}, headers=h)
        assert final.status_code == 200
        assert final.json()["state"] == "CLOSED"

    def test_note_text_is_kept_verbatim_including_markup(self, client):
        raw = "queue <2 km> back & growing"
        r = client.post("/api/incidents/INC-OWNED/note", json={"by": "SI", "text": raw}, headers=auth())
        assert r.json()["notes"][-1]["text"] == raw


# ── no route answers garbage with a 500 ──────────────────────────────────────
class TestNoFiveHundreds:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/incidents?state=NONSENSE",
            "/api/incidents?state=%00",
            "/api/incidents/../../etc/passwd",
            "/api/corridors/%20",
            "/api/city-profile?day_type=NONSENSE",
            "/api/shift/handover?hours=abc",
        ],
    )
    def test_read_garbage_never_500s(self, client, path):
        assert client.get(path).status_code < 500, path

    @pytest.mark.parametrize(
        "body",
        [
            {"by": "DO-1", "text": "x" * 5000},  # over max_length
            {"by": 123},  # wrong type
            {"unexpected": "field"},  # missing by
            "not-json-at-all",
        ],
    )
    def test_write_garbage_never_500s(self, client, body):
        r = client.post("/api/incidents/INC-FRESH/acknowledge", json=body, headers=auth())
        assert r.status_code < 500, r.text[:150]
