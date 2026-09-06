"""Candidate traffic interventions — evidence-graded, Siliguri-specific, proposed
to be TESTED, never asserted.

This replaces a hand-reasoned playbook. Every candidate now carries the evidence
grade behind it (A = peer-reviewed independent … E = projection-as-result), a
measured effect range, its failure mode, and — the discipline that matters most —
what may NOT be claimed for it. The grounding is the west-bengal-gov-ai research
and three deep-research passes (see AI_Workspace/siliguri_intervention_research).

The corrections against the earlier version are deliberate and load-bearing:
  * Selection is not "worst live index". The index over-samples the car stream
    (see PROBE_CAVEAT); Venus More is never offered a congestion remedy; the
    structural junctions (Jalpai More, V/C 1.14, non-signalised) are named.
  * Signal work is not recommended — it is routed to Google Green Light (free,
    already in Kolkata), per the "measure, do not optimise" doctrine (ADR-0007).
  * Freight is not restricted by ban (contraindicated); through-freight is a
    diversion/holding question, and diversion usually moves the jam.
  * Paratransit friction is named as side friction, never as "totos cause X%".
  * Congestion (day) and accidents (night) are separated — different places,
    different hours, different interventions.
  * Every candidate names a matched-control before/after measurement.
"""

from __future__ import annotations

from datetime import datetime

from packages.copilot.grounding_safety import (
    JUNCTION_EVIDENCE,
    MEASUREMENT_PROTOCOL,
    PROBE_CAVEAT,
)

# Night window (the accident period; congestion remedies do not belong here).
NIGHT_HOURS = set(range(20, 24)) | set(range(0, 8))


def _is_slow(condition: str | None) -> bool:
    return condition in ("ACUTE", "CHRONIC")


def _profile(centre, junction, now: datetime) -> dict:
    """What we actually know about this junction — live, structural and safety."""
    ev = JUNCTION_EVIDENCE.get(junction.junction_id, {})
    corridors = centre.network.corridors_at(junction.junction_id)
    live: list[tuple[float, str, str, str, int]] = []
    for c in corridors:
        st = centre.status.get(c.corridor_id)
        if st and st.speed_kmh is not None:
            chokes = len(st.latest.choke_points) if st.latest else 0
            live.append((st.speed_kmh, st.band, st.condition, st.name, chokes))
    live.sort()  # slowest first
    worst = live[0] if live else None
    return {
        "junction": junction.name,
        "control": junction.control,
        "vc_ratio_2011": junction.vc_ratio,
        "live_worst_speed_kmh": round(worst[0], 1) if worst else None,
        "live_worst_band": worst[1] if worst else None,
        "live_worst_condition": worst[2] if worst else None,
        "loaded_corridor": worst[3] if worst else None,
        "has_choke_point": bool(worst and worst[4] > 0),
        "corridors_measured": len(live),
        "alternates": len(centre.network.neighbours(junction.junction_id)),
        # evidence
        "safety_note": ev.get("safety"),
        "accident_trend": ev.get("trend"),
        "accident_period": ev.get("period"),
        "congestion_note": ev.get("congestion_note"),
        "do_not": ev.get("do_not"),  # e.g. "congestion" at Venus More
        "structural": bool(ev.get("structural")),
        "is_night": now.hour in NIGHT_HOURS,
    }


def _candidate(action, grade, rationale, where_when, measure, expected, caveat, do_not_claim, fit):
    return {
        "action": action,
        "grade": grade,
        "rationale": rationale,
        "where_when": where_when,
        "measure": measure,
        "expected": expected,
        "caveat": caveat,
        "do_not_claim": do_not_claim,
        "fit": fit,
    }


def _watch(p: dict) -> dict:
    return _candidate(
        action="Keep on watch; no intervention warranted yet",
        grade="—",
        rationale="The junction is moving within its usual range and shows no located block. There is nothing to test right now.",
        where_when=p["junction"],
        measure="Its speed against its own baseline; act when it leaves the band on more than a single reading.",
        expected="—",
        caveat="Acting on a junction behaving normally spends an officer for no measurable gain — and a car-probe spike may be the two-wheeler-blind instrument, not a real jam.",
        do_not_claim="Do not trigger an intervention off a single-day probe spike.",
        fit=1,
    )


def _candidates(p: dict) -> list[dict]:
    """The evidence-graded playbook, matched to the profile. Ordered by fit; the
    caller trims. Grades: A peer-reviewed independent … E projection-as-result."""
    out: list[dict] = []
    slow = _is_slow(p["live_worst_condition"])
    loaded = p["loaded_corridor"] or "the loaded approach"
    signalised = p["control"] == "SIGNALISED"

    # ── Venus More and its kind: danger, not delay. Congestion is a category
    #    error here; offer only the safety intervention, at the accident period.
    if p["do_not"] == "congestion":
        out.append(
            _candidate(
                action="Night-time safety enforcement — speed and lane discipline (NOT a congestion remedy)",
                grade="A/B",
                rationale=(
                    f"{p['safety_note']} This is a speed/geometry problem at a free-flowing "
                    "junction, worst at night — not a queue. A congestion remedy would be a "
                    "category error."
                ),
                where_when=f"{p['junction']}, at the accident-prone period (lean/night hours).",
                measure=(
                    "This is a SAFETY intervention — the live travel-time system measures delay, "
                    "not collisions, so it cannot score this. The outcome needs the accident "
                    "record; track it there, over months, not the congestion index."
                ),
                expected="A safety benefit the travel-time data cannot confirm.",
                caveat=(
                    "Enforcement's deterrent effect decays within hours-to-days (Sherman 1990) — "
                    "rotate short, unpredictable pulses rather than one long drive."
                ),
                do_not_claim="Do not judge this by the congestion index. Do not claim it 'cleared' anything without re-measuring the accident record over months.",
                fit=5,
            )
        )
        out.append(_watch(p))
        out.sort(key=lambda x: -x["fit"])
        for c in out:
            c.pop("fit", None)
        return out[:4]

    # ── Clear a physical blockage — the strongest-evidenced lever.
    if p["has_choke_point"]:
        out.append(
            _candidate(
                action="Clear the located blockage fast (stalled vehicle / illegal parking / a stopped truck)",
                grade="A/B",
                rationale=(
                    "Incident management is the best-evidenced tactical lever: halving a lane "
                    "blockage's duration roughly halves its delay; one lane-blocking vehicle for "
                    "an hour is thousands of vehicle-hours. A localised stretch is stopped, not "
                    "the whole approach."
                ),
                where_when=f"On {loaded}, at the located choke, now.",
                measure="Roadway-clearance time and the corridor's speed in the hour after clearing vs the same hour before; queue length by approach.",
                expected="Speed recovers quickly if a block, not raw volume, was the cause.",
                caveat=(
                    "A light patrol cannot move a LOADED truck — the Chicken's-Neck corridor "
                    "needs pre-positioned HEAVY recovery. Confirm the cause on the ground first."
                ),
                do_not_claim="Do not claim a clearance fixed a corridor that was volume-bound, not blocked.",
                fit=5,
            )
        )

    # ── Point duty — only where genuinely oversaturated. Adds delay elsewhere.
    oversaturated = (p["vc_ratio_2011"] or 0) >= 1.0 or p["live_worst_band"] in ("SEVERE", "HIGH")
    if slow and oversaturated:
        out.append(
            _candidate(
                action="Post an officer for discretionary point-duty at the peak",
                grade="A (thin)",
                rationale=(
                    "At an OVERSATURATED junction running an outdated fixed cycle, an officer "
                    "reading live movements can beat the existing signal (Vajeeran et al. 2020, "
                    "heterogeneous traffic). Officers already exploit two-wheeler seepage the "
                    "signal cannot."
                ),
                where_when=f"{p['junction']}, through the peak window only.",
                measure="Discharge count per green-equivalent and queue length by approach, officer-present vs matched officer-absent periods at the same junction and hour — NOT car-probe travel time.",
                expected="Queue clears faster while worked, IF the junction is genuinely oversaturated.",
                caveat=(
                    "Posting at an UNDER-saturated or free-flowing junction actively adds delay "
                    "versus the signal. Only where V/C or live band shows real saturation."
                ),
                do_not_claim="Do not claim the officer beat a re-optimised signal — a fresh signal plan beats manual control. Do not measure the gain with the car probe (it misses the two-wheelers the officer is clearing).",
                fit=4,
            )
        )

    # ── Structural / non-signalised worst junction — name it, route correctly.
    if p["structural"] or (not signalised and (p["vc_ratio_2011"] or 0) >= 1.0):
        out.append(
            _candidate(
                action="Flag for a junction/signal feasibility review (structural — outside Green Light)",
                grade="B",
                rationale=(
                    f"{p.get('congestion_note') or 'Above capacity and non-signalised.'} A "
                    "junction operating over capacity with no signal control is the most "
                    "conventional fixable finding — but it is a works decision, not a shift "
                    "action, and Google Green Light cannot reach a non-signalised junction."
                ),
                where_when=f"{p['junction']} — refer to the road authority / CMP process.",
                measure="Baseline the junction's volume-weighted delay now, so any later works has a before to be measured against.",
                expected="A structural improvement over months, if the works happen.",
                caveat="Not something a duty officer resolves in a shift. Point-duty is the interim, not the fix.",
                do_not_claim="Do not imply this can be optimised remotely; it needs physical signalisation/geometry work.",
                fit=3,
            )
        )

    # ── Signalised + chronic delay → nominate to Green Light (doctrine).
    if signalised and slow:
        out.append(
            _candidate(
                action="Nominate this junction to Google Project Green Light for signal retiming",
                grade="A/B (≈6% travel time, larger reliability gain)",
                rationale=(
                    "The doctrine is measure, don't optimise: Green Light does AI signal retiming "
                    "free (already live in Kolkata), and independent evidence for adaptive signal "
                    "work is ~6% travel time — not the 25%+ vendors claim. We nominate and then "
                    "verify; we do not build the optimiser."
                ),
                where_when=f"{p['junction']} (signalised) — hand to the Green Light programme.",
                measure="Before/after on this junction's corridors against matched controls once retiming lands — the verification Green Light itself does not do for the city.",
                expected="A modest, mostly-reliability gain; signals are ~12% of Siliguri's speed gap, so do not over-expect.",
                caveat="Green Light's own metric is stops, not travel time, and its climate model does not fit a two-wheeler city. It also cannot reach non-signalised junctions.",
                do_not_claim="Do not claim a 25%+ signal gain (that figure is vendor-reported and uncontrolled). Do not present stops-saved as travel-time saved.",
                fit=3,
            )
        )

    # ── Paratransit / kerb side-friction — named honestly.
    if slow and p["corridors_measured"]:
        out.append(
            _candidate(
                action="Clear the kerb: enforce a boarding-alighting bay, keep the curb lane free",
                grade="A (capacity drop) / C-D (persistence)",
                rationale=(
                    "Side friction — kerb boarding, standing autos/totos, on-street parking — "
                    "destroys a large share of mid-block capacity; standing paratransit at the "
                    "kerb turns a stop into a moving bottleneck (Pandey & Vasudevan 2017)."
                ),
                where_when=f"{loaded}, at the worst kerb-friction node, through the peak.",
                measure="Lane occupancy and dwell overflow into the running lane, before/after, with photo/CCTV — the car probe barely sees this two/three-wheeler friction.",
                expected="Capacity recovers while the bay is enforced and the curb lane is kept clear.",
                caveat="Persistence is the whole problem: drivers revert, and relocating a stand just moves the friction. Pilot 3–5 nodes with sustained enforcement, not a city edict.",
                do_not_claim="NEVER claim 'totos cause X% of congestion' — no evidence isolates paratransit from the side-friction bundle. Do not claim a clearance persists without a 1–4 week re-measure.",
                fit=4 if not p["is_night"] else 2,
            )
        )

    # ── Timed diversion — kept, but with the induced-demand caution up front.
    if slow and p["alternates"] >= 2:
        out.append(
            _candidate(
                action="Timed diversion of THROUGH-traffic only (freight with no local origin/destination)",
                grade="A (for the caution)",
                rationale=(
                    "Diversion genuinely helps only for pure through-traffic (Chicken's-Neck "
                    "freight that can bypass) or an incident. For local trips it usually just "
                    "moves the jam — freed capacity refills (induced demand, Duranton & Turner)."
                ),
                where_when="Divert bypassable through-freight at the peak; keep local access.",
                measure="Cordon BOTH the relieved corridor AND the diversion route and its parallels — a win needs NETWORK delay down, not just the treated link.",
                expected="Net improvement only if the diverted traffic had no local destination.",
                caveat="Diverting NE-bound freight onto local roads imports the corridor's problem into the city. Freight BANS are contraindicated — use off-hour delivery incentives, not curfews.",
                do_not_claim="Do not claim a diversion cut congestion on the strength of the treated link alone — measure the displacement corridor; expect the jam to move, not vanish.",
                fit=2,
            )
        )

    if not out:
        out.append(_watch(p))

    out.sort(key=lambda x: -x["fit"])
    for c in out:
        c.pop("fit", None)
    return out[:4]


def suggest(centre, junction_query: str | None = None, now: datetime | None = None) -> dict:
    """Candidate interventions for a junction. If none is named, the worst live
    one that is a CONGESTION location (safety-only junctions like Venus More are
    not picked as 'worst congestion')."""
    now = now or datetime.now()
    junctions = list(centre.network.junctions.values())
    if junction_query:
        matches = [j for j in junctions if junction_query.lower() in j.name.lower()]
        if not matches:
            return {"error": f"no junction matching {junction_query!r}"}
        target = matches[0]
    else:

        def worst_speed(j):
            ev = JUNCTION_EVIDENCE.get(j.junction_id, {})
            if ev.get("do_not") == "congestion":
                return 999.0  # never pick a safety-only junction as worst congestion
            speeds = [
                centre.status[c.corridor_id].speed_kmh
                for c in centre.network.corridors_at(j.junction_id)
                if centre.status.get(c.corridor_id)
                and centre.status[c.corridor_id].speed_kmh is not None
            ]
            return min(speeds) if speeds else 999.0

        target = min(junctions, key=worst_speed)

    profile = _profile(centre, target, now)
    return {
        "junction": target.name,
        "profile": profile,
        "interventions": _candidates(profile),
        "probe_caveat": PROBE_CAVEAT,
        "measurement_protocol": MEASUREMENT_PROTOCOL,
        "basis": (
            "Evidence-graded candidates to TEST, not asserted fixes. Each carries its grade "
            "(A peer-reviewed … E projection), what to measure against a matched control, and "
            "what may NOT be claimed. Ranking is by absolute slowness and evidence fit, not the "
            "car-probe index alone, which under-samples the two/three-wheelers that dominate "
            "Siliguri. Signal work is routed to Google Green Light, not built here."
        ),
    }
