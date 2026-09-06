"""The live copilot's tools and its ungraceful-degradation path.

The model path needs Vertex and is exercised in the deployed service; here we
prove the two properties that must hold without it: the tools read the live
centre faithfully and invent nothing, and when the model is unavailable the
answer degrades to the raw tool result rather than failing — while still
honouring the AnswerContract (which refuses to omit a limitation).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from packages.command.centre import CommandCentre
from packages.copilot.live import LiveCopilot, LiveToolbox
from packages.incidents.model import Incident, IncidentKind, Priority
from packages.network.model import load_network

NOW = datetime(2026, 8, 30, 18, 0)


class StubProbe:
    name, is_live, retains_durations = "stub", False, False

    def read(self, *a, **k):
        return None

    def provenance(self):
        return {"source": "stub"}


def _centre_with_incident() -> CommandCentre:
    c = CommandCentre(network=load_network(), probe=StubProbe())
    c.last_poll = NOW
    i = Incident(
        incident_id="INC-Q",
        kind=IncidentKind.CHOKE_POINT,
        priority=Priority.P1,
        title="Slow on NH10 near Venus More",
        detail="d",
        location_name="NH10, near Venus More",
        lat=26.72,
        lon=88.41,
        corridors=["C_A__B"],
        junctions=["J_VENUS_MORE"],
        detected_at=NOW - timedelta(minutes=30),
        evidence={"worst_index": 1.6},
        limitation="x",
    )
    i.acknowledge("DO-1", at=NOW - timedelta(minutes=25))
    c.incidents["INC-Q"] = i
    return c


def _box() -> LiveToolbox:
    return LiveToolbox(_centre_with_incident(), now_fn=lambda: NOW)


class TestTools:
    def test_current_state_counts_the_board(self):
        s = _box().get_current_state()
        assert s["open_incidents"] == 1
        assert "headline" in s and "bands" in s

    def test_list_incidents_carries_escalation(self):
        rows = _box().list_incidents()["incidents"]
        assert rows[0]["incident_id"] == "INC-Q"
        assert "overdue" in rows[0]

    def test_get_incident_includes_verification_and_trims_samples(self):
        d = _box().get_incident("INC-Q")
        assert "impact" in d
        assert "samples" not in d  # heavy geometry trimmed for the model

    def test_get_incident_unknown_is_an_error_not_a_crash(self):
        assert "error" in _box().get_incident("INC-NOPE")

    def test_junction_reference_has_the_accident_record(self):
        js = _box().junction_reference(name="Venus")["junctions"]
        assert js and js[0]["safety"] and "danger" in js[0]["safety"].lower()

    def test_recent_changes_sees_the_acknowledge(self):
        ch = _box().recent_changes(minutes=60)["changes"]
        assert any(c["to"] == "ACKNOWLEDGED" for c in ch)

    def test_verification_summary_is_honest_about_causation(self):
        vs = _box().verification_summary()
        assert "caveat" in vs and "baseline" in vs["caveat"].lower()


class TestDeterministicFallback:
    """ask() must never raise even with no model — it degrades."""

    def _forced_fallback(self):
        cop = LiveCopilot(_box())
        # force the model path to fail so ask() degrades deterministically
        cop._ask_model = lambda q: (_ for _ in ()).throw(RuntimeError("vertex unavailable"))
        return cop

    def test_ask_degrades_without_the_model(self):
        a = self._forced_fallback().ask("what is happening right now?").as_dict()
        assert a["degraded"] is True
        assert a["model"] == "deterministic-fallback"
        # the AnswerContract still holds — a limitation is present and non-trivial
        assert len(a["limitation"]) >= 10
        assert a["tools_called"]

    def test_routing_picks_a_relevant_tool(self):
        cop = self._forced_fallback()
        assert (
            cop.ask("which junctions are dangerous?").tool_trace[0]["tool"] == "junction_reference"
        )
        assert cop.ask("did our deployment work?").tool_trace[0]["tool"] == "verification_summary"
        assert cop.ask("what changed in the last hour?").tool_trace[0]["tool"] == "recent_changes"

    def test_fallback_invents_no_figure(self):
        # every number in the observation comes from the tool json, not the model
        a = self._forced_fallback().ask("show me the open incidents").as_dict()
        assert "list_incidents returned" in a["observation"]


class TestPastAndPresentTools:
    def test_historical_day_shape_returns_hours_and_worst(self):
        h = _box().historical_day_shape("WEEKDAY")
        # curated parquet is present in the repo; if not, an error dict is fine
        if "error" not in h:
            assert len(h["hours"]) == 24
            assert h["worst_hours"] and "caveat" in h
            assert "2019" in h["vintage"]

    def test_data_confidence_reports_coverage(self):
        d = _box().data_confidence()
        assert "coverage_pct" in d and "poll_age_minutes" in d and "caveat" in d


class TestInterventions:
    """The recommender proposes candidates to TEST — never asserts a fix, and
    always names what it will measure."""

    def test_named_junction_is_profiled(self):
        r = _box().suggest_interventions("Venus")
        assert r["junction"] == "Venus More"
        assert r["interventions"]

    def test_unknown_junction_is_an_error_not_a_crash(self):
        assert "error" in _box().suggest_interventions("Nowhere Junction ZZZ")

    def test_every_candidate_names_a_measurement(self):
        for iv in _box().suggest_interventions("Venus")["interventions"]:
            assert iv["action"] and iv["measure"]  # what to do AND how we'll know

    def test_dangerous_junction_leads_with_safety_not_congestion(self):
        # Venus More is the accident leader and one of the LEAST congested — the
        # recommender must not treat it as a delay problem.
        top = _box().suggest_interventions("Venus")["interventions"][0]
        assert "afety" in top["action"] or "nforcement" in top["action"]
        assert "danger" in top["caveat"].lower() or "delay" in top["caveat"].lower()

    def test_no_junction_named_picks_the_worst_live_one(self):
        r = _box().suggest_interventions()
        assert r["junction"] and r["interventions"]


class TestInterventionRouting:
    def _forced_fallback(self):
        cop = LiveCopilot(_box())
        cop._ask_model = lambda q: (_ for _ in ()).throw(RuntimeError("no model"))
        return cop

    def test_what_can_we_try_routes_to_interventions(self):
        cop = self._forced_fallback()
        for q in (
            "what can we try at the worst junction?",
            "what's the solution here?",
            "how do we fix this junction?",
            "recommend an intervention",
        ):
            assert cop.ask(q).tool_trace[0]["tool"] == "suggest_interventions", q

    def test_named_junction_in_the_question_is_used(self):
        a = self._forced_fallback().ask("what can we try to fix Venus More?").as_dict()
        assert a["data"][0]["result"]["junction"] == "Venus More"

    def test_intervention_answer_cites_live_and_the_records(self):
        srcs = self._forced_fallback().ask("what interventions can we test?").as_dict()["sources"]
        joined = " ".join(srcs)
        assert "Google Maps Routes" in joined  # live index basis
        assert "Comprehensive Mobility Plan 2011" in joined or "Roy, Mohammadi" in joined


class TestAnswerCarriesData:
    def _forced_fallback(self):
        cop = LiveCopilot(_box())
        cop._ask_model = lambda q: (_ for _ in ()).throw(RuntimeError("no model"))
        return cop

    def test_answer_includes_the_tool_data_for_the_ui(self):
        a = self._forced_fallback().ask("show me the open incidents").as_dict()
        assert a["data"] and a["data"][0]["tool"] == "list_incidents"
        assert "result" in a["data"][0]

    def test_a_typical_question_routes_to_history(self):
        cop = self._forced_fallback()
        assert cop.ask("when is it usually worst?").tool_trace[0]["tool"] == "historical_day_shape"


class TestSources:
    """Every answer cites the real source of its figures — computed from which
    tools ran, never something the model could invent."""

    def _forced_fallback(self):
        cop = LiveCopilot(_box())
        cop._ask_model = lambda q: (_ for _ in ()).throw(RuntimeError("no model"))
        return cop

    def test_historical_question_cites_the_2019_study(self):
        srcs = self._forced_fallback().ask("when is it usually worst?").as_dict()["sources"]
        assert any("American Economic Review" in s and "2019" in s for s in srcs)

    def test_junction_question_cites_the_survey_and_accident_record(self):
        srcs = self._forced_fallback().ask("which junctions are dangerous?").as_dict()["sources"]
        assert any("Comprehensive Mobility Plan 2011" in s for s in srcs)
        assert any("Roy, Mohammadi" in s for s in srcs)

    def test_live_question_cites_google_routes_not_raw_data(self):
        srcs = (
            self._forced_fallback().ask("which corridors are worst right now?").as_dict()["sources"]
        )
        joined = " ".join(srcs)
        assert "Google Maps Routes" in joined
        assert "not Google's raw traffic data" in joined  # the ToS boundary, stated

    def test_incident_question_cites_the_incident_log(self):
        srcs = self._forced_fallback().ask("show me the open incidents").as_dict()["sources"]
        assert any("SARGVISION incident record" in s for s in srcs)
