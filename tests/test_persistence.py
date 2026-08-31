"""Incidents must survive a restart with their whole record intact.

Before this existed, a Cloud Run recycle emptied the board: what was assigned,
who was on it, what a sergeant found, and the handover. An officer came back to
a clean screen and no evidence anything had happened.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from packages.command.centre import CommandCentre
from packages.incidents.model import Incident, IncidentKind, IncidentState, Priority
from packages.incidents.store import (
    MemoryStore,
    build_store,
    from_document,
    to_document,
)
from packages.network.model import load_network

NOW = datetime(2026, 8, 31, 10, 0)


def worked_incident() -> Incident:
    """An incident that has been through the whole officer workflow."""
    i = Incident(
        incident_id="INC-ROUNDTRIP",
        kind=IncidentKind.CHOKE_POINT,
        priority=Priority.P1,
        title="Stopped traffic on NH10 near Siliguri Junction",
        detail="449 m affected, 41% of the corridor, seen from 4 corridors.",
        location_name="NH10, near Siliguri Junction",
        lat=26.72456,
        lon=88.41562,
        corridors=["C_AIR_VIEW_MORE__SILIGURI_JUNCTION"],
        junctions=["J_SILIGURI_JUNCTION"],
        detected_at=NOW,
        evidence={"severity": "TRAFFIC_JAM", "length_m": 449, "worst_index": 1.59},
        limitation="Shows where traffic is slow, not why.",
        last_seen_at=NOW + timedelta(minutes=5),
    )
    i.assign("Traffic Guard 2", by="DO-1", unit="Traffic Guard 2", at=NOW + timedelta(minutes=3))
    i.move(IncidentState.ON_SCENE, "Traffic Guard 2", at=NOW + timedelta(minutes=11))
    i.add_note(
        "Traffic Guard 2",
        "Auto stand overflowing onto carriageway",
        kind="CAUSE",
        at=NOW + timedelta(minutes=12),
    )
    return i


class TestRoundTrip:
    def test_nothing_is_lost_in_serialisation(self):
        original = worked_incident()
        restored = from_document(to_document(original))

        assert restored.incident_id == original.incident_id
        assert restored.state is original.state
        assert restored.priority is original.priority
        assert restored.kind is original.kind
        assert restored.owner == original.owner
        assert restored.lat == original.lat and restored.lon == original.lon
        assert restored.evidence == original.evidence
        assert restored.limitation == original.limitation

    def test_the_audit_trail_survives(self):
        """The transitions ARE the record. Losing them loses the account of
        what the force did."""
        original = worked_incident()
        restored = from_document(to_document(original))

        assert len(restored.history) == len(original.history)
        assert [h.to for h in restored.history] == [h.to for h in original.history]
        assert [h.by for h in restored.history] == [h.by for h in original.history]
        assert [h.at for h in restored.history] == [h.at for h in original.history]

    def test_the_officers_own_words_survive(self):
        original = worked_incident()
        restored = from_document(to_document(original))

        assert [n.text for n in restored.notes] == [n.text for n in original.notes]
        assert [n.author for n in restored.notes] == [n.author for n in original.notes]
        assert [n.kind for n in restored.notes] == [n.kind for n in original.notes]

    def test_assignments_survive(self):
        original = worked_incident()
        restored = from_document(to_document(original))
        assert [a.assigned_to for a in restored.assignments] == [
            a.assigned_to for a in original.assignments
        ]
        assert [a.unit for a in restored.assignments] == [a.unit for a in original.assignments]

    def test_a_restored_incident_can_still_be_worked(self):
        """Not merely readable — the state machine must still accept the next
        legal step."""
        restored = from_document(to_document(worked_incident()))
        restored.move(IncidentState.CLEARING, "Traffic Guard 2")
        restored.move(IncidentState.RESOLVED, "Traffic Guard 2")
        restored.close("DO-1", "Stand relocated 40 m, flow restored")
        assert restored.state is IncidentState.CLOSED


class TestRestartRecovery:
    def test_open_incidents_come_back_after_a_restart(self):
        store = MemoryStore()
        store.save(worked_incident())

        class Stub:
            name, is_live, retains_durations = "stub", False, False

            def read(self, *a, **k):
                return None

            def provenance(self):
                return {}

        # A fresh centre is what a recycled instance builds.
        centre = CommandCentre(network=load_network(), probe=Stub(), store=store)
        assert "INC-ROUNDTRIP" in centre.incidents
        recovered = centre.incidents["INC-ROUNDTRIP"]
        assert recovered.owner == "Traffic Guard 2"
        assert recovered.state is IncidentState.ON_SCENE
        assert len(recovered.notes) == 1

    def test_closed_incidents_do_not_come_back(self):
        """A closed incident belongs in the record, not on the board."""
        store = MemoryStore()
        i = worked_incident()
        i.move(IncidentState.CLEARING, "x")
        i.move(IncidentState.RESOLVED, "x")
        i.close("DO-1", "done")
        store.save(i)

        class Stub:
            name, is_live, retains_durations = "stub", False, False

            def read(self, *a, **k):
                return None

            def provenance(self):
                return {}

        centre = CommandCentre(network=load_network(), probe=Stub(), store=store)
        assert "INC-ROUNDTRIP" not in centre.incidents


class TestStoreSelection:
    def test_the_backend_is_never_guessed(self, monkeypatch):
        """A police system silently falling back to a store that forgets is
        worse than one that refuses to start."""
        monkeypatch.delenv("INCIDENT_STORE", raising=False)
        assert build_store().describe()["durable"] is False

    def test_memory_store_admits_it_forgets(self):
        d = MemoryStore().describe()
        assert d["durable"] is False
        assert "lost" in d["note"].lower()


class TestComplianceBoundary:
    def test_no_corridor_readings_are_persisted(self):
        """The Maps terms permit caching coordinates only. An incident carries
        the figures that justified it, once, as evidence for a decision — not a
        travel-time series."""
        doc = to_document(worked_incident())
        forbidden = {
            "readings",
            "runs",
            "speed_runs",
            "polyline",
            "duration_s",
            "static_duration_s",
        }
        assert not forbidden & set(doc), f"leaked travel content: {forbidden & set(doc)}"

    def test_the_store_documents_why_readings_are_excluded(self):
        """The reasoning has to live next to the code, not only in a commit
        message, or the next person adds a readings collection."""
        import packages.incidents.store as store

        assert store.__doc__ is not None
        text = store.__doc__.lower()
        assert "permit caching" in text
        assert "not stored" in text or "never" in text
