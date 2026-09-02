"""The officer's verbs, over HTTP, the way the board actually calls them.

`test_incidents.py` proves the state machine. This proves the endpoint in front
of it: that a refused transition comes back as a refusal an interface can show
rather than a 500, that a half-filled form cannot record an anonymous action,
and that the two ways a control room double-submits — a double click and two
officers on the same incident — leave one honest record instead of two.

The distinction matters because every one of these is a police record. An
action that records the wrong actor, or records twice, is worse than an action
that fails loudly.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ROUTES_API_KEY", "test-key-not-used")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3050")

NOW = datetime(2026, 8, 30, 15, 0)

# These tests are about the verbs, not the gate — test_write_access.py covers
# that. The token is pinned on the module rather than through the environment
# because the gate is read at import time, and another module reloading it
# would otherwise decide whether this one is authenticated.
TOKEN = "test-officer-token"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client():
    """A centre holding exactly one open incident, rebuilt for every test."""
    from apps.api import main
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
    main.STATE["started_at"] = NOW - timedelta(hours=6)
    main.AUTH_MODE = "token"
    main.WRITE_TOKEN = TOKEN
    with TestClient(main.app) as c:
        yield c


def post(client, action: str, **body):
    return client.post(
        f"/api/incidents/INC-TEST/{action}", json={"by": "DO-1", **body}, headers=AUTH
    )


class TestTheVerbsWork:
    def test_acknowledge_advances_the_state_and_returns_the_incident(self, client):
        r = post(client, "acknowledge")
        assert r.status_code == 200
        assert r.json()["state"] == "ACKNOWLEDGED"

    def test_the_response_tells_the_interface_what_is_legal_next(self, client):
        """The board derives its buttons from next_actions, so it cannot be stale."""
        assert "ASSIGNED" in post(client, "acknowledge").json()["next_actions"]

    def test_assign_records_owner_and_the_officer_who_assigned(self, client):
        r = post(client, "assign", to="SI Barman", unit="TG-2")
        assert r.status_code == 200
        body = r.json()
        assert body["owner"] == "SI Barman"
        assert body["assignments"][-1]["assigned_by"] == "DO-1"

    def test_stand_down_is_a_first_class_outcome(self, client):
        r = post(client, "stand-down", text="local officer reports it cleared")
        assert r.status_code == 200
        assert r.json()["state"] == "STOOD_DOWN"

    def test_a_note_is_kept_verbatim(self, client):
        text = "Cause: lorry breakdown, Mahananda approach"
        assert post(client, "note", text=text).json()["notes"][-1]["text"] == text


class TestRefusalsAreRefusals:
    """A refused action must be a 4xx the interface can render, never a 500."""

    def test_a_transition_out_of_order_is_409_not_500(self, client):
        r = post(client, "resolve")  # nobody has been sent yet
        assert r.status_code == 409, f"got {r.status_code}: {r.text}"
        assert r.json()["detail"], "the refusal must carry a reason to show"

    def test_a_terminal_incident_refuses_further_action(self, client):
        post(client, "assign", to="SI Barman")
        post(client, "on-scene")
        post(client, "clearing")
        post(client, "resolve")
        assert post(client, "close", text="flow restored").status_code == 200
        assert post(client, "acknowledge").status_code == 409

    @pytest.mark.parametrize(
        "action,body",
        [
            ("assign", {}),  # no one to assign to
            ("note", {}),  # nothing to record
            ("stand-down", {}),  # no reason
            ("close", {}),  # no outcome
        ],
    )
    def test_an_action_missing_its_substance_is_refused(self, client, action, body):
        r = client.post(
            f"/api/incidents/INC-TEST/{action}", json={"by": "DO-1", **body}, headers=AUTH
        )
        assert r.status_code == 400, f"{action} was accepted empty: {r.text}"

    def test_stand_down_cannot_be_recorded_without_a_reason(self, client):
        """The reason is the whole point: it is what an audit reads later."""
        assert post(client, "stand-down", text="").status_code == 400


class TestNoAnonymousRecords:
    """Every row in an incident's history names a person. That is the audit."""

    @pytest.mark.parametrize("by", [None, "", " ", "x"])
    def test_an_action_without_a_real_actor_is_refused(self, client, by):
        body = {} if by is None else {"by": by}
        r = client.post("/api/incidents/INC-TEST/acknowledge", json=body, headers=AUTH)
        assert r.status_code == 422, f"recorded an action by {by!r}: {r.text}"

    def test_an_overlong_actor_is_refused(self, client):
        r = client.post("/api/incidents/INC-TEST/acknowledge", json={"by": "A" * 200}, headers=AUTH)
        assert r.status_code == 422


class TestDoubleSubmit:
    """Two ways a control room sends the same action twice."""

    def test_a_double_click_does_not_record_two_acknowledgements(self, client):
        """The button disables while in flight, but the network can still retry."""
        assert post(client, "acknowledge").status_code == 200
        second = post(client, "acknowledge")
        assert second.status_code == 409, "a repeat must be refused, not recorded"

        # And the audit trail must carry exactly one first-seen row.
        history = client.get("/api/incidents/INC-TEST").json()["history"]
        acks = [h for h in history if h["to"] == "ACKNOWLEDGED"]
        assert len(acks) == 1, f"acknowledged twice: {acks}"

    def test_the_refusal_names_the_state_it_is_already_in(self, client):
        """The board needs enough to tell the officer what actually happened."""
        post(client, "acknowledge")
        detail = post(client, "acknowledge").json()["detail"]
        assert "ACKNOWLEDGED" in detail

    def test_two_officers_cannot_both_own_the_same_incident(self, client):
        """Second assign must either be refused or replace, never silently both."""
        post(client, "assign", to="SI Barman")
        r = client.post(
            "/api/incidents/INC-TEST/assign",
            json={"by": "DO-2", "to": "SI Roy"},
            headers=AUTH,
        )
        if r.status_code == 200:
            assert r.json()["owner"] == "SI Roy", "an accepted reassign must take effect"
            # and the trail must show both, so a supervisor can see the handover
            assert len(r.json()["assignments"]) == 2
        else:
            assert r.status_code in (400, 409)


class TestTheRecordSurvives:
    def test_an_action_is_persisted_before_the_response_returns(self, client):
        """An officer who sees 'assigned' must not lose it to a restart."""
        from apps.api import main

        post(client, "assign", to="SI Barman")
        stored = {i.incident_id: i for i in main.STATE["centre"].store.load_open()}
        assert "INC-TEST" in stored, "the action was never written"
        assert stored["INC-TEST"].owner == "SI Barman"

    def test_text_is_stored_exactly_as_typed(self, client):
        """No escaping, stripping or mangling on the way in or out.

        The interface escapes on render; the record must stay faithful, because
        a note is evidence and '<' is a character an officer may legitimately
        type."""
        raw = "queue <2 km> back from the bridge & still growing"
        assert post(client, "note", text=raw).json()["notes"][-1]["text"] == raw
