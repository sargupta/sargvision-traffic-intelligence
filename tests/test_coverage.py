"""Coverage: the console names what it does not watch, and surfaces the slow
roads no officer is on — and a posting removes a road from that list.
"""

from __future__ import annotations

from datetime import datetime

from packages.command.centre import CommandCentre
from packages.coverage.gaps import SIGNIFICANT_GAPS, coverage_summary, unwatched_slow
from packages.history.store import MemoryHistoryStore
from packages.network.model import load_network
from packages.network.probe import CorridorReading
from packages.verification.store import MemoryDeploymentStore

NOW = datetime(2026, 9, 1, 18, 0)


class _SlowProbe:
    name, is_live, retains_durations = "p", True, False

    def read(self, c, a, b, now):
        return CorridorReading(
            corridor_id=c.corridor_id,
            observed_at=now,
            duration_s=2000 / (12 / 3.6),
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


class TestGapRegister:
    def test_names_significant_uninstrumented_roads(self):
        names = {g["name"] for g in SIGNIFICANT_GAPS}
        assert "Matigara" in names  # the founder's named gap
        for g in SIGNIFICANT_GAPS:
            # every gap states why it matters, its grade, and why it is not watched
            assert g["significance"] and g["grade"] and g["why_not_watched"]

    def test_summary_states_the_cost_boundary(self):
        s = coverage_summary(_centre())
        assert s["corridors_instrumented"] == 68
        assert "cost" in s["note"].lower()


class TestUnwatchedSlow:
    def test_lists_slow_corridors_with_no_officer(self):
        u = unwatched_slow(_centre(), NOW)
        assert u["count"] > 0
        assert all(r["condition"] in ("ACUTE", "CHRONIC") for r in u["corridors"])

    def test_each_row_carries_how_slow_vs_usual(self):
        # not just "slow" — the deviation an officer reads: speed, its usual, excess
        for r in unwatched_slow(_centre(), NOW)["corridors"]:
            assert r["speed_kmh"] is not None
            assert r["typical_speed_kmh"] is not None
            assert "excess_minutes" in r and "index" in r

    def test_a_posting_removes_a_corridor_from_the_list(self):
        c = _centre()
        first = unwatched_slow(c, NOW)["corridors"][0]["corridor_id"]
        c.start_deployment([first], by="DO-1", unit="TG-2", purpose="x", now=NOW)
        after = {r["corridor_id"] for r in unwatched_slow(c, NOW)["corridors"]}
        assert first not in after, "a covered corridor is no longer 'unwatched'"

    def test_acute_is_counted_and_sorted_first(self):
        u = unwatched_slow(_centre(), NOW)
        assert u["acute"] + u["chronic"] == u["count"]
        # if any acute exist, they lead
        conds = [r["condition"] for r in u["corridors"]]
        if "ACUTE" in conds and "CHRONIC" in conds:
            assert conds.index("ACUTE") < conds.index("CHRONIC")
