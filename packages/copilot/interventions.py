"""Candidate traffic interventions — proposed to be TESTED, never asserted.

An officer knows a junction is slow. What they asked for is the next step: a
workable action they can try on the ground, and a way to know whether it worked.
This module answers that without pretending to certainty a measurement cannot
give. It proposes 2-4 candidate interventions matched to what the data actually
shows about a junction, and — the part that makes it honest — states for each
one exactly what the system will measure to decide if it moved the road.

The discipline is the same as the copilot's: it never claims a fix will work. It
proposes a hypothesis; the verification engine proves or disproves it from the
corridor's own before/after travel time. "We verify" is the whole point.
"""

from __future__ import annotations

from datetime import datetime

# The accident record — the same evidence the network reference and copilot use.
from packages.copilot.grounding_safety import SAFETY


def _profile(centre, junction) -> dict:
    """What we actually know about this junction, live and structural."""
    corridors = centre.network.corridors_at(junction.junction_id)
    live: list[tuple[float, str, str, int]] = []
    for c in corridors:
        st = centre.status.get(c.corridor_id)
        if st and st.index is not None:
            chokes = len(st.latest.choke_points) if st.latest else 0
            live.append((st.index, st.band, st.name, chokes))
    live.sort(reverse=True)
    worst = live[0] if live else None
    return {
        "junction": junction.name,
        "control": junction.control,
        "vc_ratio_2011": junction.vc_ratio,
        "congestion_pressure": junction.congestion_pressure,
        "safety": SAFETY.get(junction.junction_id),
        "live_worst_index": round(worst[0], 3) if worst else None,
        "live_worst_band": worst[1] if worst else None,
        "loaded_corridor": worst[2] if worst else None,
        "has_choke_point": bool(worst and worst[3] > 0),
        "corridors_measured": len(live),
        "alternates": len(centre.network.neighbours(junction.junction_id)),
    }


def _candidates(p: dict) -> list[dict]:
    """The playbook, matched to the profile. Each is a testable hypothesis with
    its own measurement. Ordered by fit; the caller trims."""
    out: list[dict] = []
    chronic = p["congestion_pressure"] in ("OVER_CAPACITY", "NEAR_CAPACITY") or (
        p["vc_ratio_2011"] is not None and p["vc_ratio_2011"] >= 0.8
    )
    elevated = p["live_worst_band"] in ("SEVERE", "HIGH", "ELEVATED")
    signalised = p["control"] == "SIGNALISED"
    dangerous = bool(p["safety"])
    loaded = p["loaded_corridor"]

    if p["has_choke_point"]:
        out.append(
            {
                "action": "Clear the choke point (encroachment / illegal parking / a stalled vehicle)",
                "rationale": "A localised stretch is stopped, not the whole approach — the classic cause is something physically blocking a lane rather than raw volume.",
                "where_when": f"On {loaded or 'the loaded approach'}, at the located choke, now.",
                "measure": "The corridor's index in the hour after the lane is cleared, against the same hour before.",
                "expected": "Index drops toward 1.0 quickly if the block was the cause.",
                "caveat": "Have the field officer confirm the cause first — if it is volume, not a block, clearing nothing changes.",
                "fit": 5,
            }
        )
    if signalised and (chronic or elevated) and loaded:
        out.append(
            {
                "action": "Request a longer green / retimed cycle on the loaded arm from the signal authority",
                "rationale": f"The junction is signalised and {loaded} is carrying the load; the split may be starving that approach at peak.",
                "where_when": f"The {loaded} approach, at the peak window.",
                "measure": "Before/after on the loaded corridor's journey time once the retiming is applied, over several matched days.",
                "expected": "The loaded approach improves; watch the cross-street does not worsen by more.",
                "caveat": "We do not control signals — this is a recommendation to the authority. Measure the cross-street too so the fix does not just move the delay.",
                "fit": 4,
            }
        )
    if chronic or elevated:
        out.append(
            {
                "action": "Post a traffic officer to manually manage the loaded movement at peak",
                "rationale": "The approach is above its typical travel time; discretionary manual control often clears a recurring peak a fixed signal cannot.",
                "where_when": f"{p['junction']}, through the peak window.",
                "measure": "The junction's corridor index during posted windows against comparable unposted windows.",
                "expected": "Index falls while the officer is working it; the verification engine attributes the change.",
                "caveat": "Helps only if the cause is manageable flow, not physical under-capacity — if V/C is the wall, a posting will not move it far.",
                "fit": 4,
            }
        )
    if (chronic or elevated) and p["alternates"] >= 2:
        out.append(
            {
                "action": "Run a timed diversion of through-traffic to an alternate route",
                "rationale": "The junction is over its typical time and has alternate corridors that could take a share at peak.",
                "where_when": "Divert a portion of through-traffic during the peak window; keep local access.",
                "measure": "Index on BOTH the relieved corridor and the alternate — the test is whether total delay fell, not whether the jam simply moved.",
                "expected": "The relieved corridor improves without the alternate degrading by as much.",
                "caveat": "The main risk of a diversion is shifting the jam. This measurement is designed to catch exactly that.",
                "fit": 3,
            }
        )
    if dangerous:
        out.append(
            {
                "action": "Enforcement focused on lane discipline and the risky movements (a safety posting)",
                "rationale": f"{p['safety']}",
                "where_when": f"{p['junction']}, at the accident-prone period.",
                "measure": "This is a SAFETY intervention — the live system measures travel time, not collisions, so its effect on danger cannot be read here. Track the index as a secondary signal only; the real outcome needs the accident record.",
                "expected": "A safety benefit the live data cannot confirm — this one is about danger, not delay.",
                "caveat": "Do not judge a safety posting by the congestion index. Venus More is the case in point: dangerous and NOT congested.",
                "fit": 3 if not (chronic or elevated) else 2,
            }
        )
    if not out:
        out.append(
            {
                "action": "Keep on watch; no intervention warranted yet",
                "rationale": "The junction is within its typical travel time and shows no located block. There is nothing to test right now.",
                "where_when": p["junction"],
                "measure": "Its index against its own baseline; act when it leaves the band.",
                "expected": "—",
                "caveat": "Acting on a junction that is behaving normally spends an officer for no measurable gain.",
                "fit": 1,
            }
        )
    out.sort(key=lambda x: -x["fit"])
    for c in out:
        c.pop("fit", None)
    return out[:4]


def suggest(centre, junction_query: str | None = None, now: datetime | None = None) -> dict:
    """Candidate interventions for a junction. If none is named, the worst live one."""
    junctions = list(centre.network.junctions.values())
    if junction_query:
        matches = [j for j in junctions if junction_query.lower() in j.name.lower()]
        if not matches:
            return {"error": f"no junction matching {junction_query!r}"}
        target = matches[0]
    else:

        def worst_index(j):
            idx = [
                centre.status[c.corridor_id].index
                for c in centre.network.corridors_at(j.junction_id)
                if centre.status.get(c.corridor_id)
                and centre.status[c.corridor_id].index is not None
            ]
            return max(idx) if idx else 0.0

        target = max(junctions, key=worst_index)

    profile = _profile(centre, target)
    return {
        "junction": target.name,
        "profile": profile,
        "interventions": _candidates(profile),
        "basis": (
            "Candidate interventions to TEST on the ground, not asserted fixes. Each names "
            "what the system will measure to decide if it worked. The measurement is the "
            "corridor's own before/after travel time; a safety posting is the exception, whose "
            "benefit the live data cannot confirm."
        ),
    }
