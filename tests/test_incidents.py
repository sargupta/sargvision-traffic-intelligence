"""The officer workflow must not lose a step or permit one that never happened."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from packages.incidents.cluster import cluster_chokes
from packages.incidents.model import (
    IllegalTransition,
    Incident,
    IncidentKind,
    IncidentState,
    Priority,
    incident_id,
)
from packages.network.probe import ChokePoint

NOW = datetime(2026, 8, 30, 15, 0)


def make(**kw) -> Incident:
    base = dict(
        incident_id="INC-TEST",
        kind=IncidentKind.CHOKE_POINT,
        priority=Priority.P1,
        title="t",
        detail="d",
        location_name="NH10",
        lat=26.72,
        lon=88.41,
        corridors=["C_A__B"],
        junctions=["J_A"],
        detected_at=NOW,
        evidence={},
        limitation="unknown cause",
    )
    return Incident(**{**base, **kw})


class TestLifecycle:
    def test_full_path_to_closed(self):
        i = make()
        i.assign("SI Barman", by="DO Ghosh", at=NOW + timedelta(minutes=2))
        assert i.state is IncidentState.ASSIGNED and i.owner == "SI Barman"
        i.move(IncidentState.ON_SCENE, "SI Barman")
        i.move(IncidentState.CLEARING, "SI Barman")
        i.move(IncidentState.RESOLVED, "SI Barman")
        i.close("DO Ghosh", "flow restored")
        assert i.state is IncidentState.CLOSED
        assert not i.is_open
        # Acknowledged is inserted automatically by assign, so the trail is complete.
        assert [h.to for h in i.history][0] is IncidentState.ACKNOWLEDGED

    def test_illegal_transition_raises(self):
        i = make()
        with pytest.raises(IllegalTransition):
            i.move(IncidentState.RESOLVED, "someone")

    def test_closed_is_terminal(self):
        i = make()
        i.acknowledge("DO")
        i.move(IncidentState.CLEARING, "DO")
        i.move(IncidentState.RESOLVED, "DO")
        i.close("DO", "done")
        with pytest.raises(IllegalTransition):
            i.acknowledge("DO")


class TestOutcomesThatAreNotAction:
    """A system that only lets you close what you acted on gets worked around."""

    def test_stand_down_requires_a_reason(self):
        i = make()
        with pytest.raises(ValueError):
            i.stand_down("DO Ghosh", "   ")

    def test_stand_down_records_an_outcome(self):
        i = make()
        i.stand_down("DO Ghosh", "Market day, expected, no deployment needed")
        assert i.state is IncidentState.STOOD_DOWN
        assert i.notes[-1].kind == "OUTCOME"
        assert not i.is_open

    def test_stood_down_can_be_reopened(self):
        i = make()
        i.stand_down("DO", "expected")
        i.acknowledge("DO")
        assert i.is_open

    def test_lapse_is_attributed_to_the_system(self):
        """A high lapse rate grades the alerting, so it must be visible."""
        i = make()
        i.lapse()
        assert i.state is IncidentState.LAPSED
        assert i.history[-1].by == "system"

    def test_close_requires_an_outcome(self):
        i = make()
        i.acknowledge("DO")
        i.move(IncidentState.CLEARING, "DO")
        i.move(IncidentState.RESOLVED, "DO")
        with pytest.raises(ValueError):
            i.close("DO", "")


class TestAttention:
    def test_unowned_incident_needs_attention(self):
        i = make()
        assert i.needs_attention
        assert i.unowned_minutes(NOW + timedelta(minutes=9)) == pytest.approx(9)

    def test_assigned_incident_is_owned(self):
        i = make()
        i.assign("SI Barman", by="DO")
        assert not i.needs_attention
        assert i.unowned_minutes(NOW + timedelta(minutes=99)) == 0.0


class TestIdentity:
    def test_same_place_same_day_is_the_same_incident(self):
        """A flapping condition must reattach, not spawn a new incident per poll."""
        a = incident_id(IncidentKind.CHOKE_POINT, 26.72456, 88.41562, NOW)
        b = incident_id(IncidentKind.CHOKE_POINT, 26.72461, 88.41559, NOW + timedelta(hours=3))
        assert a == b

    def test_different_kind_is_a_different_incident(self):
        a = incident_id(IncidentKind.CHOKE_POINT, 26.72, 88.41, NOW)
        b = incident_id(IncidentKind.SAFETY, 26.72, 88.41, NOW)
        assert a != b


class TestClustering:
    """One jam seen from four corridors is one dispatch, not four."""

    def choke(self, lat, lon, severity="TRAFFIC_JAM", length=300.0):
        return ChokePoint(
            severity=severity,
            start=(lat, lon),
            end=(lat + 0.001, lon),
            midpoint=(lat, lon),
            length_m=length,
            share_of_corridor=0.3,
        )

    def test_same_jam_on_several_corridors_merges(self):
        clusters = cluster_chokes(
            {
                "C_1": [self.choke(26.7245, 88.4156)],
                "C_2": [self.choke(26.7246, 88.4157)],
                "C_3": [self.choke(26.7244, 88.4155)],
            }
        )
        assert len(clusters) == 1
        assert clusters[0].corroboration == 3

    def test_distant_jams_stay_separate(self):
        clusters = cluster_chokes(
            {
                "C_1": [self.choke(26.7245, 88.4156)],
                "C_2": [self.choke(26.7500, 88.4400)],
            }
        )
        assert len(clusters) == 2

    def test_cluster_takes_the_worst_severity(self):
        clusters = cluster_chokes(
            {
                "C_1": [self.choke(26.7245, 88.4156, severity="SLOW")],
                "C_2": [self.choke(26.7246, 88.4157, severity="TRAFFIC_JAM")],
            }
        )
        assert clusters[0].severity == "TRAFFIC_JAM"

    def test_no_chokes_gives_no_clusters(self):
        assert cluster_chokes({"C_1": [], "C_2": []}) == []


class TestIncidentContinuity:
    """A jam whose extent changes must stay one incident.

    Cluster centroids wander tens of metres between polls as the tail grows and
    shrinks. Keyed on a hashed coordinate, that spawned a fresh incident every
    few minutes and the handover listed the same stretch of NH10 three times.
    """

    def build(self, lat, lon):
        from packages.command.centre import CommandCentre
        from packages.network.model import load_network

        class Stub:
            name, is_live, retains_durations = "stub", False, False

            def read(self, *a, **k):
                return None

            def provenance(self):
                return {}

        centre = CommandCentre(network=load_network(), probe=Stub())
        return centre

    def cluster_at(self, lat, lon, length=400.0):
        from packages.incidents.cluster import ChokeCluster

        return ChokeCluster(
            centre=(lat, lon),
            severity="TRAFFIC_JAM",
            members=[
                (
                    "C_X",
                    ChokePoint(
                        severity="TRAFFIC_JAM",
                        start=(lat, lon),
                        end=(lat, lon),
                        midpoint=(lat, lon),
                        length_m=length,
                        share_of_corridor=0.4,
                    ),
                )
            ],
        )

    def test_drifting_centroid_stays_one_incident(self):
        centre = self.build(26.7245, 88.4156)
        centre.confirm_after = timedelta(0)
        # Force the corridor to look elevated so the cluster is worth raising.
        for status in centre.status.values():
            status.band = "HIGH"
        first = centre._raise_incidents([self.cluster_at(26.72450, 88.41560)], NOW)
        assert len(first) == 1
        # 40 m away on the next poll — the same jam breathing.
        again = centre._raise_incidents(
            [self.cluster_at(26.72486, 88.41560)], NOW + timedelta(minutes=5)
        )
        assert again == [], "a drifting centroid must reattach, not spawn a second incident"
        assert len([i for i in centre.incidents.values() if i.is_open]) == 1

    def test_a_genuinely_different_place_is_a_new_incident(self):
        centre = self.build(26.7245, 88.4156)
        centre.confirm_after = timedelta(0)
        for status in centre.status.values():
            status.band = "HIGH"
        centre._raise_incidents([self.cluster_at(26.72450, 88.41560)], NOW)
        far = centre._raise_incidents(
            [self.cluster_at(26.74000, 88.43000)], NOW + timedelta(minutes=5)
        )
        assert len(far) == 1
