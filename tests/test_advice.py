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
        corridors.append({
            "corridor_id": cid, "name": corridor.name,
            "band": "HIGH" if hit else "NORMAL",
            "index": hit[1] if hit else 1.0,
            "excess_minutes": hit[2] if hit else 0.0,
            "duration_minutes": 10.0, "typical_minutes": 8.0,
            "roads": "NH10", "trend_per_10min": None, "held_minutes": 0,
            "choke_points": [], "runs": [], "observed_at": None,
            "approximate_location": False, "speed_kmh": 20.0,
        })
    return {"corridors": corridors, "incidents": []}


def approaches_to(junction_id: str, n: int) -> list[str]:
    return [
        c.corridor_id for c in NET.corridors.values() if c.to_junction == junction_id
    ][:n]


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
        board = board_with(
            [(c, 2.0, 12.0) for c in big] + [(c, 1.3, 1.0) for c in small]
        )
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
