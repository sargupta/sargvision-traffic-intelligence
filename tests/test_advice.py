"""Advice must be actionable, ranked, and honest about what it dropped."""

from __future__ import annotations

from datetime import datetime

from packages.command.advice import CONVERGENCE_MIN, recommend
from packages.network.model import load_network

NOW = datetime(2026, 8, 31, 10, 0)
NET = load_network()


def board_with(degraded: list[tuple[str, float, float]]) -> dict:
    """degraded: (corridor_id, index, excess_minutes)"""
    by_id = {c.corridor_id: c for c in NET.corridors.values()}
    corridors = []
    for cid, corridor in by_id.items():
        hit = next((d for d in degraded if d[0] == cid), None)
        corridors.append(
            {
                "corridor_id": cid,
                "name": corridor.name,
                "band": "HIGH" if hit else "NORMAL",
                "index": hit[1] if hit else 1.0,
                "excess_minutes": hit[2] if hit else 0.0,
                "duration_minutes": 10.0,
                "typical_minutes": 8.0,
                "roads": "NH10",
                "trend_per_10min": None,
                "held_minutes": 0,
                "choke_points": [],
                "runs": [],
                "observed_at": None,
                "approximate_location": False,
                "speed_kmh": 20.0,
            }
        )
    return {"corridors": corridors, "incidents": []}


def approaches_to(junction_id: str, n: int) -> list[str]:
    return [c.corridor_id for c in NET.corridors.values() if c.to_junction == junction_id][:n]


class TestConvergence:
    def test_several_approaches_to_one_junction_becomes_one_posting(self):
        target = "J_SILIGURI_JUNCTION"
        cids = approaches_to(target, 3)
        recs = recommend(NET, board_with([(c, 1.5, 4.0) for c in cids]), NOW)
        posts = [r for r in recs if r.kind == "POST"]
        assert len(posts) == 1
        assert "Siliguri Junction" in posts[0].headline
        assert set(posts[0].corridors) == set(cids)

    def test_a_single_slow_approach_is_not_a_posting(self):
        cids = approaches_to("J_SILIGURI_JUNCTION", 1)
        recs = recommend(NET, board_with([(cids[0], 1.9, 9.0)]), NOW)
        assert not [r for r in recs if r.kind == "POST"]

    def test_convergence_threshold_is_respected(self):
        assert CONVERGENCE_MIN >= 2


class TestDeployability:
    """Advice that cannot be carried out is a list, and a list is what the
    officer already had."""

    def test_postings_never_exceed_available_units(self):
        degraded = []
        for jid in list(NET.junctions)[:8]:
            for cid in approaches_to(jid, 3):
                degraded.append((cid, 1.5, 5.0))
        recs = recommend(NET, board_with(degraded), NOW, deployable=3)
        assert len([r for r in recs if r.kind == "POST"]) <= 3

    def test_what_was_dropped_is_stated_not_hidden(self):
        degraded = []
        for jid in list(NET.junctions)[:8]:
            for cid in approaches_to(jid, 3):
                degraded.append((cid, 1.5, 5.0))
        recs = recommend(NET, board_with(degraded), NOW, deployable=2)
        watch = [r for r in recs if r.kind == "WATCH"]
        assert watch, "dropped junctions must be reported, not silently truncated"
        assert "more junction" in watch[0].headline

    def test_ranking_is_by_delay_not_by_road_count(self):
        """Two badly delayed approaches beat four barely delayed ones."""
        big = approaches_to("J_VENUS_MORE", 2)
        small = approaches_to("J_COURT_MORE", 4)
        board = board_with([(c, 2.0, 12.0) for c in big] + [(c, 1.3, 1.0) for c in small])
        recs = recommend(NET, board, NOW, deployable=1)
        posts = [r for r in recs if r.kind == "POST"]
        assert posts and "Venus More" in posts[0].headline


class TestHonesty:
    def test_every_recommendation_states_its_evidence_and_its_limits(self):
        cids = approaches_to("J_SILIGURI_JUNCTION", 3)
        for r in recommend(NET, board_with([(c, 1.5, 4.0) for c in cids]), NOW):
            assert r.because, f"{r.kind} must show its working"
            assert len(r.cannot_know) > 20, f"{r.kind} must state what it cannot know"

    def test_no_recommendation_asserts_a_cause(self):
        cids = approaches_to("J_SILIGURI_JUNCTION", 3)
        for r in recommend(NET, board_with([(c, 1.5, 4.0) for c in cids]), NOW):
            text = f"{r.headline} {r.detail}".lower()
            for word in ("because of", "caused by", "due to an", "the cause is"):
                assert word not in text, f"{r.kind} asserted a cause: {text[:90]}"

    def test_quiet_network_says_so_explicitly(self):
        recs = recommend(NET, board_with([]), NOW)
        assert len(recs) == 1
        assert recs[0].kind == "STAND_DOWN"


class TestCopy:
    """User-facing text in a police product. A grammar error undermines the
    care everything else shows."""

    def _watch(self, deployable: int):
        degraded = []
        for jid in list(NET.junctions)[:6]:
            for cid in approaches_to(jid, 3):
                degraded.append((cid, 1.5, 5.0))
        recs = recommend(NET, board_with(degraded), NOW, deployable=deployable)
        return next(r for r in recs if r.kind == "WATCH")

    def test_singular_agreement(self):
        # Pick a cap that leaves exactly one junction over.
        for cap in range(1, 6):
            try:
                w = self._watch(cap)
            except StopIteration:
                continue
            if w.headline.startswith("1 more junction"):
                assert "also shows" in w.headline, w.headline
                assert "junctions" not in w.headline
                return

    def test_plural_agreement(self):
        w = self._watch(1)
        if not w.headline.startswith("1 more junction "):
            assert "junctions" in w.headline and "also show " in w.headline, w.headline


class TestAdviceDoesNotFlood:
    """The posting cap stopped one kind of flooding. Escalations arrived
    through the other door: five unowned incidents produced five near-identical
    "has waited 30 minutes" cards, which is one message to a duty officer."""

    def board_with_stale(self, n: int, ages=None):
        b = board_with([])
        b["incidents"] = [
            {
                "incident_id": f"INC-{i}",
                "title": f"Stopped traffic on NH10 near junction {i}",
                "detail": "d",
                "priority": "P3",
                "needs_attention": True,
                "age_minutes": (ages[i] if ages else 30 + i),
                "detected_at": "2026-08-31T10:00:00",
                "junctions": [f"J_{i}"],
                "corridors": [f"C_{i}"],
            }
            for i in range(n)
        ]
        return b

    def test_many_stale_incidents_produce_one_recommendation(self):
        recs = recommend(NET, self.board_with_stale(5), NOW)
        escalations = [r for r in recs if r.kind == "ESCALATE"]
        assert len(escalations) == 1
        assert "5 incidents" in escalations[0].headline

    def test_it_names_the_oldest_and_counts_the_rest(self):
        recs = recommend(NET, self.board_with_stale(6), NOW)
        e = next(r for r in recs if r.kind == "ESCALATE")
        assert "2 more" in " ".join(e.because)

    def test_a_single_stale_incident_reads_naturally(self):
        recs = recommend(NET, self.board_with_stale(1), NOW)
        e = next(r for r in recs if r.kind == "ESCALATE")
        assert "1 incident has been waiting" in e.headline

    def test_fresh_incidents_do_not_escalate(self):
        recs = recommend(NET, self.board_with_stale(3, ages={0: 5, 1: 9, 2: 12}), NOW)
        assert not [r for r in recs if r.kind == "ESCALATE"]

    def test_a_p1_makes_the_escalation_urgent(self):
        b = self.board_with_stale(2)
        b["incidents"][0]["priority"] = "P1"
        e = next(r for r in recommend(NET, b, NOW) if r.kind == "ESCALATE")
        assert e.urgency == "NOW"


class TestUnlocatedJunctionsAreDeclared:
    """Recommending a posting somewhere we cannot locate must say so."""

    def test_an_unconfirmed_name_is_repeated_in_the_caveat(self):
        target = "J_WALL_FORD_SEVOKE_CROSSING"
        junction = NET.junction(target)
        assert junction is not None and junction.name_unconfirmed

        cids = approaches_to(target, 3)
        recs = recommend(NET, board_with([(c, 1.5, 4.0) for c in cids]), NOW)
        post = next(r for r in recs if r.kind == "POST")
        assert "2011 mobility plan" in post.cannot_know

    def test_a_confirmed_junction_carries_no_caveat(self):
        cids = approaches_to("J_VENUS_MORE", 3)
        recs = recommend(NET, board_with([(c, 1.5, 4.0) for c in cids]), NOW)
        post = next(r for r in recs if r.kind == "POST" and "Venus More" in r.headline)
        assert "mobility plan" not in post.cannot_know
        assert "approximate" not in post.cannot_know.lower()
