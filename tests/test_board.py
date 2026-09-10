"""The review board — the live expert layer.

The deterministic board is the spine: instant, offline-safe, canon-grounded, and
the fallback the AI council degrades to. These tests hold that spine, and the two
properties the council layer must never break: it never raises, and it never
invents a figure the deterministic engine did not produce.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from packages.command.centre import CommandCentre
from packages.copilot import council as council_mod
from packages.copilot.board import live_board
from packages.copilot.council import review
from packages.history.store import MemoryHistoryStore
from packages.network.model import load_network
from packages.network.probe import CorridorReading
from packages.verification.store import MemoryDeploymentStore

NOW = datetime(2026, 9, 1, 18, 0)  # evening peak, NOT the night safety window


class _SlowProbe:
    name, is_live, retains_durations = "p", True, False

    def read(self, c, a, b, now):
        return CorridorReading(
            corridor_id=c.corridor_id,
            observed_at=now,
            duration_s=2000 / (10 / 3.6),
            static_duration_s=2000 / (14 / 3.6),
            distance_m=2000,
            roads="Rd",
        )

    def provenance(self):
        return {"source": "p"}


def _centre():
    c = CommandCentre(
        network=load_network(),
        probe=_SlowProbe(),
        history_store=MemoryHistoryStore(),
        deployment_store=MemoryDeploymentStore(),
    )
    c.poll(NOW)
    return c


@pytest.fixture(autouse=True)
def _clean_council_state(monkeypatch):
    # Isolate the module-level cache/budget between tests and keep ADK off by
    # default so nothing here ever touches Vertex.
    council_mod._CACHE.clear()
    council_mod._SPENT.clear()
    monkeypatch.setattr(council_mod, "ADK_ENABLED", False)
    yield


class TestDeterministicBoard:
    def test_issues_moves_for_the_live_situation(self):
        b = live_board(_centre(), NOW)
        assert b["generated_by"] == "deterministic"
        assert b["count"] > 0
        assert len(b["items"]) <= 6  # capped

    def test_every_move_names_its_seat_and_a_checkable_source(self):
        # the honest "council": a real discipline + a standard behind it, never
        # an asserted authority
        for it in live_board(_centre(), NOW)["items"]:
            assert it["seat"], "every move names the discipline it belongs to"
            assert it["source"], "and the checkable standard behind it"
            assert it["grade"]
            assert it["move"] and it["measure"] and it["do_not_claim"]

    def test_items_are_ranked_most_urgent_first(self):
        items = live_board(_centre(), NOW)["items"]
        scores = [it["score"] for it in items]
        assert scores == sorted(scores, reverse=True)

    def test_safety_only_junction_gets_no_congestion_move_by_day(self):
        # Venus More is danger, not delay — a congestion remedy there is a
        # category error, and at 18:00 it is outside its night risk window.
        junctions = {it["junction"] for it in live_board(_centre(), NOW)["items"]}
        assert not any("Venus" in j for j in junctions)

    def test_stand_down_is_stated_when_nothing_warrants_a_move(self):
        # An empty network (no readings) has nothing to act on — said out loud.
        c = CommandCentre(
            network=load_network(),
            probe=_SlowProbe(),
            history_store=MemoryHistoryStore(),
            deployment_store=MemoryDeploymentStore(),
        )
        b = live_board(c, NOW)  # never polled → no status
        assert b["count"] == 0
        assert "stand_down" in b


class TestCouncilLayer:
    def test_with_adk_off_the_review_is_the_deterministic_board(self):
        r = review(_centre(), NOW)
        assert r["generated_by"] == "deterministic"
        assert "synthesis" not in r

    def test_council_failure_degrades_and_never_raises(self, monkeypatch):
        monkeypatch.setattr(council_mod, "ADK_ENABLED", True)

        async def _boom(_brief):
            raise RuntimeError("vertex unreachable")

        monkeypatch.setattr(council_mod, "_run_council", _boom)
        r = review(_centre(), NOW)
        assert r["generated_by"] == "deterministic"  # spine still answers
        assert "unavailable" in r["council_status"]

    def test_council_enriches_without_inventing_a_figure(self, monkeypatch):
        monkeypatch.setattr(council_mod, "ADK_ENABLED", True)
        base = live_board(_centre(), NOW)
        first = base["items"][0]["junction"]

        async def _stub(brief):
            import json

            data = json.loads(brief)
            notes = [
                {"junction": it["junction"], "expert_note": "clear the block first."}
                for it in data["items"]
            ]
            return json.dumps({"synthesis": "Prioritise the located block.", "notes": notes})

        monkeypatch.setattr(council_mod, "_run_council", _stub)
        r = review(_centre(), NOW)
        assert r["generated_by"] == "adk-council"
        assert r["synthesis"] == "Prioritise the located block."
        enriched = {it["junction"]: it for it in r["items"]}
        assert enriched[first].get("expert_note")
        # the live figures must be untouched — the model annotates, it does not measure
        det = {it["junction"]: it for it in base["items"]}
        assert enriched[first]["live"] == det[first]["live"]
        assert enriched[first]["move"] == det[first]["move"]

    def test_budget_stops_spending(self, monkeypatch):
        monkeypatch.setattr(council_mod, "ADK_ENABLED", True)
        monkeypatch.setattr(council_mod, "DAILY_BUDGET", 0)  # already spent
        called = {"n": 0}

        async def _stub(_brief):
            called["n"] += 1
            return "{}"

        monkeypatch.setattr(council_mod, "_run_council", _stub)
        r = review(_centre(), NOW)
        assert r["generated_by"] == "deterministic"
        assert "budget" in r["council_status"]
        assert called["n"] == 0  # the model was never called
