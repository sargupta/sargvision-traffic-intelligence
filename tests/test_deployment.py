"""Deployment verification: the before/after is honest, the counterfactual uses
the road's own baseline, and it never claims cause it cannot show.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from packages.command.centre import CommandCentre
from packages.history.model import ObservationHistory
from packages.history.store import MemoryHistoryStore
from packages.network.model import load_network
from packages.network.probe import CorridorReading
from packages.verification.deployment import Deployment, DeploySample
from packages.verification.store import MemoryDeploymentStore, from_document, to_document

MON_6PM = datetime(2026, 9, 1, 18, 0)  # a Monday


def _dep(before_speeds, during_speeds, before_idx, during_idx, primary="C1") -> Deployment:
    d = Deployment(
        deployment_id="DEP-x",
        corridor_ids=[primary],
        primary_corridor_id=primary,
        location_name="Test Rd",
        by="DO-1",
        unit="TG-2",
        purpose="manage peak",
        started_at=MON_6PM,
    )
    for i, (s, ix) in enumerate(zip(before_speeds, before_idx, strict=True)):
        d.before.append(DeploySample(MON_6PM - timedelta(minutes=30 - i * 10), s, ix, "HEAVY"))
    for i, (s, ix) in enumerate(zip(during_speeds, during_idx, strict=True)):
        d.during.append(DeploySample(MON_6PM + timedelta(minutes=15 + i * 15), s, ix, "HEAVY"))
    return d


class TestEffectMagnitude:
    def test_improvement_shows_positive_speed_delta(self):
        e = _dep([11, 12], [19, 21], [1.6, 1.5], [1.05, 1.0]).effect()
        assert e["before_speed_kmh"] and e["during_speed_kmh"]
        assert e["delta_speed_kmh"] > 0
        assert e["delta_index"] < 0  # index fell = improved
        assert "improved" in e["verdict"]

    def test_no_change_is_admitted(self):
        e = _dep([12, 12], [12, 12], [1.5, 1.5], [1.5, 1.5]).effect()
        assert e["verdict"] == "no measurable change while posted"

    def test_worsening_is_admitted(self):
        e = _dep([18, 18], [10, 10], [1.1, 1.1], [1.7, 1.7]).effect()
        assert e["verdict"] == "worse while posted"

    def test_thin_data_is_not_yet_measurable(self):
        d = Deployment(
            deployment_id="DEP-y",
            corridor_ids=["C1"],
            primary_corridor_id="C1",
            location_name="Rd",
            by="DO-1",
            unit="TG-2",
            purpose="x",
            started_at=MON_6PM,
        )
        assert d.effect()["verdict"] == "not yet measurable"


class TestCounterfactual:
    def _history_with_typical(self, typical_index: float) -> ObservationHistory:
        h = ObservationHistory()
        for wk in range(8):  # 8 Mondays at 18:00 → a firm baseline
            h.fold("C1", "Test Rd", MON_6PM + timedelta(weeks=wk), typical_index, True)
        return h

    def test_beating_the_roads_usual_is_the_strong_verdict(self):
        # road usually runs at index 1.5 here; during the posting it ran at ~1.0
        h = self._history_with_typical(1.5)
        e = _dep([11, 12], [20, 21], [1.55, 1.5], [1.0, 1.0]).effect(history=h)
        assert e["vs_typical"] == "better than this road's usual for the hour"
        assert "beat this road's usual" in e["verdict"]
        assert e["confidence"] == "good"

    def test_without_a_baseline_it_only_observes(self):
        # improved, but no history → cannot separate the posting from usual easing
        e = _dep([11, 12], [20, 21], [1.55, 1.5], [1.0, 1.0]).effect(history=ObservationHistory())
        assert e["vs_typical"] is None
        assert e["verdict"] == "improved while posted"
        assert "not yet enough history" in e["limitation"]

    def test_limitation_never_claims_proof(self):
        h = self._history_with_typical(1.5)
        e = _dep([11], [20], [1.5], [1.0]).effect(history=h)
        assert "evidence, not proof" in e["limitation"]


class TestCentreIntegration:
    class _Probe:
        name, is_live, retains_durations = "p", True, False

        def __init__(self):
            self.speed = 12.0

        def read(self, c, a, b, now):
            return CorridorReading(
                corridor_id=c.corridor_id,
                observed_at=now,
                duration_s=2000 / (self.speed / 3.6),
                static_duration_s=2000 / (14 / 3.6),
                distance_m=2000,
                roads="Rd",
            )

        def provenance(self):
            return {"source": "p"}

    def _centre(self):
        return CommandCentre(
            network=load_network(),
            probe=self._Probe(),
            history_store=MemoryHistoryStore(),
            deployment_store=MemoryDeploymentStore(),
        )

    def test_start_seeds_before_and_poll_fills_during(self):
        c = self._centre()
        cid = next(iter(c.network.corridors))
        for k in range(3):
            c.poll(MON_6PM - timedelta(minutes=45 - 15 * k))
        dep = c.start_deployment([cid], by="DO-1", unit="TG-2", purpose="peak", now=MON_6PM)
        assert dep.before, "before-window seeded from prior readings"
        c.probe.speed = 22.0
        for k in range(1, 4):
            c.poll(MON_6PM + timedelta(minutes=16 * k))
        assert dep.during, "poll records during-samples"
        e = dep.effect(c.history)
        assert e["delta_speed_kmh"] is not None and e["delta_speed_kmh"] > 0

    def test_unknown_corridor_refused(self):
        c = self._centre()
        try:
            c.start_deployment(["NOPE"], by="DO-1", unit="TG-2", purpose="x", now=MON_6PM)
            raise AssertionError("should have refused")
        except ValueError:
            pass

    def test_end_marks_ended(self):
        c = self._centre()
        cid = next(iter(c.network.corridors))
        c.poll(MON_6PM)
        dep = c.start_deployment([cid], by="DO-1", unit="TG-2", purpose="x", now=MON_6PM)
        assert dep.is_active
        c.end_deployment(dep.deployment_id, MON_6PM + timedelta(hours=1))
        assert not dep.is_active


class TestPersistence:
    def test_round_trips(self):
        d = _dep([11, 12], [20], [1.5, 1.5], [1.0])
        d.incident_id = "INC-9"
        back = from_document(to_document(d))
        assert back.primary_corridor_id == "C1"
        assert len(back.before) == 2 and len(back.during) == 1
        assert back.incident_id == "INC-9"

    def test_store_saves_and_loads(self):
        store = MemoryDeploymentStore()
        store.save(_dep([12], [20], [1.5], [1.0]))
        assert len(store.load_recent()) == 1
