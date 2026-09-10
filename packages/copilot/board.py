"""The review board — the live, always-on expert layer, deterministic spine.

This reads the WHOLE network for the current situation and issues the immediate
move for every junction that warrants one right now, each attributed to the
discipline and the standard it rests on (packages.copilot.canon), with what to
measure and what it must not claim. It reuses the evidence-graded playbook in
packages.copilot.interventions rather than inventing a second one.

No language model participates here. This module is three things at once:

  1. the instant, offline-safe answer an officer always gets;
  2. the grounded situation brief the AI council (packages.copilot.council)
     reasons OVER — the council may re-prioritise and explain, never re-compute;
  3. the fallback the /api/board endpoint returns whenever the council is
     disabled, unreachable or over its credit budget.

Every figure here is one the centre already computed. The board's authority is
the canon it cites, not an assertion — an officer can check the source.
"""

from __future__ import annotations

from datetime import datetime

from packages.copilot.grounding_safety import MEASUREMENT_PROTOCOL, PROBE_CAVEAT
from packages.copilot.interventions import _candidates, _profile

MAX_ITEMS = 6

BOARD_NOTE = (
    "The review board reads the live network and issues the immediate move for each "
    "junction that warrants one now — grounded in the discipline and the published "
    "standard it rests on, with what to measure and what it must not claim."
)
DOCTRINE = (
    "Measure, don't optimise: every move is a hypothesis to TEST against a matched "
    "control, not an optimisation to assert. Signal retiming is routed to Google "
    "Green Light; the console's job is to verify what a posting actually did."
)


def _score(p: dict) -> int:
    """How much this junction warrants a move RIGHT NOW. Higher is more urgent.

    A located blockage is the strongest, best-evidenced lever, so it leads. Then
    acute (slow AND worse than its own usual) — the only congestion signal an
    officer cannot get by looking — weighted up when the junction is also over
    capacity. Chronic (always slow here) scores low: structural, and not news to
    an officer. A pure safety junction (Venus More) surfaces only in its own
    risk window, and never as a congestion item."""
    if p["do_not"] == "congestion":
        return 66 if p["is_night"] else 0
    cond = p["live_worst_condition"]
    band = p["live_worst_band"]
    oversaturated = (p["vc_ratio_2011"] or 0) >= 1.0 or band in ("SEVERE", "HIGH")
    if p["has_choke_point"]:
        return 100
    if cond == "ACUTE" and oversaturated:
        return 92
    if cond == "ACUTE":
        return 84
    if cond == "CHRONIC" and oversaturated:
        return 72
    if band in ("SEVERE", "HIGH"):
        return 62
    if cond == "CHRONIC":
        return 50
    return 0


def _urgency(score: int) -> str:
    if score >= 90:
        return "NOW"
    if score >= 60:
        return "THIS_SHIFT"
    return "ADVISORY"


def _item(profile: dict, top: dict, score: int) -> dict:
    return {
        "junction": profile["junction"],
        "urgency": _urgency(score),
        "score": score,
        "live": {
            "speed_kmh": profile["live_worst_speed_kmh"],
            "band": profile["live_worst_band"],
            "condition": profile["live_worst_condition"],
            "loaded_corridor": profile["loaded_corridor"],
            "has_choke_point": profile["has_choke_point"],
        },
        # the seat — the honest "expert chair": a real discipline + a checkable source
        "seat": top.get("discipline", ""),
        "source": top.get("source", ""),
        "grade": top["grade"],
        "move": top["action"],
        "rationale": top["rationale"],
        "where_when": top["where_when"],
        "measure": top["measure"],
        "expected": top["expected"],
        "caveat": top["caveat"],
        "do_not_claim": top["do_not_claim"],
    }


def live_board(centre, now: datetime | None = None, max_items: int = MAX_ITEMS) -> dict:
    """The immediate recommendations across the whole live network, ranked."""
    moment = now or centre.last_poll or datetime.now()
    items: list[dict] = []
    for junction in centre.network.junctions.values():
        profile = _profile(centre, junction, moment)
        score = _score(profile)
        if score <= 0:
            continue
        candidates = _candidates(profile)
        if not candidates:
            continue
        items.append(_item(profile, candidates[0], score))

    items.sort(key=lambda x: -x["score"])
    items = items[:max_items]
    seats = sorted({i["seat"] for i in items if i["seat"]})

    review = {
        "at": moment.isoformat(timespec="seconds"),
        "count": len(items),
        "items": items,
        "seats_consulted": seats,
        "board": BOARD_NOTE,
        "doctrine": DOCTRINE,
        "probe_caveat": PROBE_CAVEAT,
        "measurement_protocol": MEASUREMENT_PROTOCOL,
        "generated_by": "deterministic",
    }
    if not items:
        review["stand_down"] = (
            "The board sees nothing on the monitored network that warrants a move right now: "
            "no located blockage, no junction slow and worse than its own usual without cover, "
            "and no safety junction in its risk window. This is a result, not an empty screen."
        )
    return review
