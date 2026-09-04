"""The verification raw material: does the record capture how an incident moved?

This is the foundation of the "we verify" claim. It does not test causation —
that needs the junction baseline — it tests that the index at each lifecycle
moment is captured faithfully, deduplicated without losing the newest value, and
turned into an honest within-incident reading.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from packages.incidents.model import Incident, IncidentKind, IncidentState, Priority

NOW = datetime(2026, 8, 30, 18, 0)


def make(**kw) -> Incident:
    base = dict(
        incident_id="INC-TEST",
        kind=IncidentKind.CHOKE_POINT,
        priority=Priority.P2,
        title="Slow on NH10",
        detail="d",
        location_name="NH10",
        lat=26.72,
        lon=88.41,
        corridors=["C_A__B"],
        junctions=["J_A"],
        detected_at=NOW,
        evidence={"worst_index": 1.62},
        limitation="x",
    )
    return Incident(**{**base, **kw})


class TestSampling:
    def test_a_reading_is_recorded(self):
        i = make()
        i.record_sample(NOW, 1.62, "HIGH")
        assert len(i.samples) == 1
        assert i.samples[0].index == 1.62

    def test_a_missing_index_records_nothing(self):
        """A corridor with no reading must not create a phantom sample."""
        i = make()
        i.record_sample(NOW, None, "UNKNOWN")
        assert i.samples == []

    def test_a_stable_reading_coalesces_and_keeps_its_onset(self):
        i = make()
        for m in range(0, 30, 3):
            i.record_sample(NOW + timedelta(minutes=m), 1.60, "HIGH")
        assert len(i.samples) == 1, "identical readings should coalesce"
        # The ONSET is kept, not the newest — otherwise a transition-anchored
        # sample would be dragged forward off the moment it anchors.
        assert i.samples[0].at == NOW

    def test_an_anchored_sample_appends_even_when_the_value_repeats(self):
        i = make()
        i.record_sample(NOW, 1.60, "HIGH")
        # a transition anchor at a later time with the same value must still land
        i.record_sample(NOW + timedelta(minutes=10), 1.60, "HIGH", anchor=True)
        assert len(i.samples) == 2
        assert i.samples[-1].at == NOW + timedelta(minutes=10)

    def test_a_changed_reading_appends(self):
        i = make()
        i.record_sample(NOW, 1.60, "HIGH")
        i.record_sample(NOW + timedelta(minutes=3), 1.20, "ELEVATED")
        assert len(i.samples) == 2

    def test_the_series_is_capped(self):
        i = make()
        for m in range(0, i._SAMPLE_CAP + 50):
            # vary the index so nothing coalesces
            i.record_sample(NOW + timedelta(minutes=m), 1.0 + m * 0.001, "ELEVATED")
        assert len(i.samples) == i._SAMPLE_CAP
        # the oldest were dropped, the newest kept
        assert i.samples[-1].at == NOW + timedelta(minutes=i._SAMPLE_CAP + 49)


class TestImpact:
    def _worked_incident(self) -> Incident:
        """An incident that was owned, worked, and cleared — index falling."""
        i = make()
        i.record_sample(NOW, 1.62, "HIGH")  # at detection
        i.acknowledge("DO-1", at=NOW + timedelta(minutes=2))
        i.assign("SI Barman", by="DO-1", at=NOW + timedelta(minutes=4))
        i.record_sample(NOW + timedelta(minutes=10), 1.55, "HIGH")
        i.move(IncidentState.ON_SCENE, "SI Barman", at=NOW + timedelta(minutes=12))
        i.record_sample(NOW + timedelta(minutes=12), 1.50, "HIGH")  # at on-scene
        i.record_sample(NOW + timedelta(minutes=20), 1.15, "ELEVATED")
        i.move(IncidentState.RESOLVED, "SI Barman", at=NOW + timedelta(minutes=24))
        i.record_sample(NOW + timedelta(minutes=24), 1.05, "NORMAL")  # at resolved
        return i

    def test_index_at_each_moment_is_read(self):
        imp = self._worked_incident().impact()
        assert imp["index_at_detection"] == 1.62
        assert imp["index_on_scene"] == 1.50
        assert imp["index_resolved"] == 1.05

    def test_it_reports_the_fall_while_owned(self):
        imp = self._worked_incident().impact()
        # 1.50 on scene → 1.05 resolved
        assert imp["index_fell_while_owned"] == 0.45

    def test_response_and_clearance_times(self):
        imp = self._worked_incident().impact()
        assert imp["minutes_to_scene"] == 8.0  # assigned at 4, on scene at 12
        assert imp["minutes_to_clear"] == 12.0  # on scene at 12, resolved at 24

    def test_peak_is_the_worst_seen(self):
        imp = self._worked_incident().impact()
        assert imp["peak_index"] == 1.62

    def test_it_does_not_overclaim_without_samples(self):
        """No measurement → no fabricated effect, only what detection knew."""
        i = make()
        i.acknowledge("DO-1", at=NOW + timedelta(minutes=2))
        imp = i.impact()
        assert imp["index_on_scene"] is None
        assert imp["index_fell_while_owned"] is None
        assert imp["index_at_detection"] == 1.62  # still known from evidence

    def test_a_far_off_sample_is_not_read_as_the_transition_value(self):
        """A sample hours from the transition must not be claimed as its index."""
        i = make()
        i.record_sample(NOW, 1.62, "HIGH")
        i.acknowledge("DO-1", at=NOW + timedelta(minutes=2))
        i.assign("SI", by="DO-1", at=NOW + timedelta(minutes=4))
        i.move(IncidentState.ON_SCENE, "SI", at=NOW + timedelta(hours=3))
        # only sample is 3h before on-scene → outside tolerance
        assert i.impact()["index_on_scene"] is None

    def test_impact_appears_in_the_api_view(self):
        d = self._worked_incident().as_dict(NOW + timedelta(minutes=30))
        assert "impact" in d
        assert d["impact"]["index_fell_while_owned"] == 0.45
        assert len(d["samples"]) >= 3
