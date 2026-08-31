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


class TestDriftingQueueConfirms:
    """The defect that made the product unable to raise an incident for a real jam.

    Candidates were keyed on incident_id, which hashes the coordinate rounded to
    four decimals — about eleven metres. A queue whose tail grows moves further
    than that between polls, so every poll minted a fresh key, restarted the
    confirmation clock, and the condition never confirmed. Two hours of
    continuous stopped traffic raised nothing and left forty orphan keys.

    Every queue worth dispatching to is growing. This is the regression guard.
    """

    def centre(self):
        from packages.command.centre import CommandCentre
        from packages.network.model import load_network

        class Stub:
            name, is_live, retains_durations = "stub", False, False

            def read(self, *a, **k):
                return None

            def provenance(self):
                return {}

        c = CommandCentre(network=load_network(), probe=Stub())
        for st in c.status.values():
            st.band = "HIGH"
        return c

    def jam_at(self, lat, lon):
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
                        length_m=450.0,
                        share_of_corridor=0.41,
                    ),
                )
            ],
        )

    def simulate(self, drift_m: float, polls: int = 40):
        c = self.centre()
        start = datetime(2026, 8, 31, 10, 0)
        lat, lon = 26.72450, 88.41560
        raised = 0
        for i in range(polls):
            lat += drift_m / 111_320.0
            at = start + timedelta(minutes=3 * i)
            raised += len(c._raise_incidents([self.jam_at(lat, lon)], at))
            c._prune_candidates(at)
        return c, raised

    @pytest.mark.parametrize("drift_m", [0.0, 5.0, 10.0, 20.0])
    def test_a_growing_queue_still_becomes_an_incident(self, drift_m):
        _, raised = self.simulate(drift_m)
        assert raised >= 1, f"a jam drifting {drift_m} m per poll never confirmed — this is the bug"

    def test_a_realistic_queue_becomes_exactly_one_incident(self):
        c, raised = self.simulate(10.0)
        assert raised == 1
        assert len([i for i in c.incidents.values() if i.is_open]) == 1

    def test_the_confirmation_hold_is_still_enforced(self):
        """Fixing drift must not mean everything confirms instantly."""
        c = self.centre()
        at = datetime(2026, 8, 31, 10, 0)
        assert c._raise_incidents([self.jam_at(26.7245, 88.4156)], at) == []
        assert c._raise_incidents([self.jam_at(26.7245, 88.4156)], at + timedelta(minutes=3)) == []
        raised = c._raise_incidents([self.jam_at(26.7245, 88.4156)], at + timedelta(minutes=9))
        assert len(raised) == 1, "should confirm once past the 8-minute hold"

    def test_candidates_do_not_accumulate_forever(self):
        """One entry per poll, never pruned, is a slow leak in a process that
        must not be restarted casually."""
        c, _ = self.simulate(10.0, polls=60)
        assert len(c._candidates) <= 3, f"{len(c._candidates)} candidates left holding"

    def test_the_board_says_why_nothing_was_raised(self):
        c = self.centre()
        at = datetime(2026, 8, 31, 10, 0)
        c._raise_incidents([self.jam_at(26.7245, 88.4156)], at)
        assert c.suppressed["holding"] == 1


class TestQueueBudget:
    """A cap that admits anything outranking the weakest, and never removes the
    weakest, is not a cap. The board showed "6/5"."""

    def centre_with_unowned(self, priorities):
        from packages.command.centre import CommandCentre
        from packages.network.model import load_network

        class Stub:
            name, is_live, retains_durations = "stub", False, False
            def read(self, *a, **k): return None
            def provenance(self): return {}

        c = CommandCentre(network=load_network(), probe=Stub())
        for n, p in enumerate(priorities):
            c.incidents[f"INC-{n}"] = Incident(
                incident_id=f"INC-{n}", kind=IncidentKind.CHOKE_POINT, priority=p,
                title="t", detail="d", location_name="NH10", lat=26.7, lon=88.4,
                corridors=[], junctions=[], detected_at=NOW, evidence={}, limitation="x",
            )
        return c

    def test_a_low_priority_condition_is_refused_at_the_cap(self):
        c = self.centre_with_unowned([Priority.P3] * 5)
        assert c._within_budget(Priority.P3) is False
        assert c._within_budget(Priority.P4) is False

    def test_a_severe_condition_is_never_hidden_by_a_full_queue(self):
        """Suppressing a genuine P1 because a counter is full is the wrong
        failure for a police system."""
        c = self.centre_with_unowned([Priority.P3] * 8)
        assert c._within_budget(Priority.P1) is True
        assert c._within_budget(Priority.P2) is True

    def test_below_the_cap_anything_is_admitted(self):
        c = self.centre_with_unowned([Priority.P1] * 2)
        assert c._within_budget(Priority.P4) is True

    def test_the_board_declares_an_overloaded_shift(self):
        c = self.centre_with_unowned([Priority.P1] * 7)
        assert c.board(NOW)["over_budget"] is True

    def test_a_healthy_queue_is_not_flagged(self):
        c = self.centre_with_unowned([Priority.P1] * 2)
        assert c.board(NOW)["over_budget"] is False


class TestHeadlineCountsTheWholeQueue:
    def centre_with(self, priorities):
        return TestQueueBudget().centre_with_unowned(priorities)

    def test_it_does_not_undercount_behind_the_p1s(self):
        """It said "2 incidents needing action now" while six sat unowned."""
        c = self.centre_with([Priority.P1, Priority.P1, Priority.P2, Priority.P3, Priority.P3, Priority.P3])
        headline = c.board(NOW)["headline"]
        assert "2 incidents needing action now" in headline
        assert "4 more waiting" in headline

    def test_a_queue_with_no_p1_still_reports_itself(self):
        c = self.centre_with([Priority.P3, Priority.P3])
        assert "2 incidents waiting for an officer" in c.board(NOW)["headline"]

    def test_an_empty_queue_falls_through_to_the_corridor_bands(self):
        c = self.centre_with([])
        assert "waiting for an officer" not in c.board(NOW)["headline"]
