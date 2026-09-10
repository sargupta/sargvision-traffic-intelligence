"""The coverage boundary and the real-time "no officer on it" signal.

Two honest answers to "what are we NOT covering":

  1. SIGNIFICANT_GAPS — a static register of roads the evidence says matter but
     the console does not instrument, each with why it matters and why it is not
     watched yet. Watching every road collides with the Maps terms and the
     Routes API cost (the binding constraint), so coverage is a deliberate,
     evidence-targeted decision, not a blanket sweep. This register is what makes
     that decision visible instead of silent.

  2. unwatched_slow() — the corridors that are slow RIGHT NOW (acute or chronic)
     with no active deployment on them. This is the Ghogomali pattern the officer
     confirmed — the system pointing at a real problem on a road nobody is
     standing on — generalised to the whole network.

The gap register is grounded in the west-bengal-gov-ai evidence base
(see reference_siliguri_evidence / AI_Workspace/siliguri_intervention_research).
Graded A (peer-reviewed) … D (press). Coordinates are approximate where noted;
adding any of these to the LIVE network is a costed decision, not done here.
"""

from __future__ import annotations

# Roads the evidence flags as significant but the console does not instrument.
# `kind`: junction | corridor | area. `grade`: evidence grade of the significance.
SIGNIFICANT_GAPS: list[dict] = [
    {
        "name": "Matigara",
        "kind": "area",
        "significance": (
            "Heavy daily traffic on the NH31/Bidhan Nagar approach toward Bagdogra; "
            "named by the Commissionerate as uncovered. Not in the instrumented network."
        ),
        "evidence": "Operational report (founder/officer)",
        "grade": "D",
        "why_not_watched": "Outside the 20-junction OD set; would need geometry and added Routes cost.",
    },
    {
        "name": "Surya Sen Avenue (approach)",
        "kind": "corridor",
        "significance": "Worst Travel-Time-Index approach in the 2019 city survey (TTI 4.095).",
        "evidence": "Chanda & Roy Chowdhury, IJRAR 6(1), 2019",
        "grade": "B",
        "why_not_watched": "Approach not in the current corridor set.",
    },
    {
        "name": "Burdwan Road",
        "kind": "corridor",
        "significance": "Second-worst TTI approach (3.716); a CDP-named arterial where traffic converges.",
        "evidence": "IJRAR 2019; Siliguri CDP 2041",
        "grade": "B",
        "why_not_watched": "Instrumented only where it meets Hill Cart Road, not along its length.",
    },
    {
        "name": "Khalpara (freight parking)",
        "kind": "area",
        "significance": (
            "The CDP names it specifically: trucks parked on the road for long durations "
            "cause congestion and speed loss — a locatable freight-parking problem."
        ),
        "evidence": "Siliguri CDP 2041",
        "grade": "B",
        "why_not_watched": "A parking/enforcement problem, not a through-corridor; not in the OD set.",
    },
    {
        "name": "S.F. Road",
        "kind": "corridor",
        "significance": "New accident hotspot (zone A16) — a recent spike in the 2026 study's EHSA.",
        "evidence": "Roy et al., Geographies 6(2):55, 2026 (n=315, a prior)",
        "grade": "A",
        "why_not_watched": "A safety location, distinct from the congestion OD set; not instrumented.",
    },
    {
        "name": "Tinbatti More (AH2)",
        "kind": "junction",
        "significance": "Accident zone A4 (complex geometry on AH2); absent from the originating report.",
        "evidence": "Roy et al. 2026 (prior)",
        "grade": "A",
        "why_not_watched": "Not in the instrumented junction set.",
    },
    {
        "name": "IOC Road near NJP Station",
        "kind": "corridor",
        "significance": "Accident zone A6; a corridor the originating report never mentioned.",
        "evidence": "Roy et al. 2026 (prior)",
        "grade": "A",
        "why_not_watched": "NJP Station is a node in the network but this segment is not a live corridor.",
    },
    {
        "name": "Salugara More (Sevoke Road)",
        "kind": "junction",
        "significance": "Accident zone A2 — a persistent hotspot in the EHSA on the Sevoke Road arterial.",
        "evidence": "Roy et al. 2026 (prior)",
        "grade": "A",
        "why_not_watched": "Beyond the current network's Sevoke-Road extent.",
    },
]


def coverage_summary(centre) -> dict:
    """What is watched, what is not, and the honest boundary."""
    return {
        "corridors_instrumented": len(centre.network.corridors),
        "junctions_instrumented": len(centre.network.junctions),
        "known_gaps": len(SIGNIFICANT_GAPS),
        "note": (
            "Coverage is deliberately targeted, not exhaustive: every live corridor is a "
            "recurring Routes API cost, and the Maps terms bar storing raw readings, so we "
            "instrument the evidence-significant network and name what we leave out rather "
            "than sweep every road. The gaps below are watched by nobody — including us."
        ),
    }


def unwatched_slow(centre, now=None) -> dict:
    """Corridors slow RIGHT NOW (acute or chronic) with no active deployment on
    them — the roads a problem is on and nobody is standing on. The generalised
    Ghogomali signal."""
    moment = now or centre.last_poll
    # corridor_ids currently covered by an active deployment
    covered: set[str] = set()
    for dep in centre.deployments.values():
        if dep.is_active:
            covered.update(dep.corridor_ids)

    rows = []
    for cid, st in centre.status.items():
        if st.condition not in ("ACUTE", "CHRONIC"):
            continue
        if cid in covered:
            continue
        r = st.latest
        # How slow against the road's OWN usual — the deviation an officer needs,
        # not just "slow". typical_speed is Google's modelled typical for the same
        # route; excess is minutes over that. For a CHRONIC road the two speeds sit
        # close (it is always this slow); for an ACUTE one the gap is the story.
        typical_speed = None
        if r is not None and r.static_duration_s:
            typical_speed = round((r.distance_m / 1000) / (r.static_duration_s / 3600), 1)
        rows.append(
            {
                "corridor_id": cid,
                "name": st.name,
                "condition": st.condition,
                "speed_kmh": round(st.speed_kmh, 1) if st.speed_kmh is not None else None,
                "typical_speed_kmh": typical_speed,
                "excess_minutes": round(r.excess_minutes, 1) if r is not None else None,
                "index": round(st.index, 2) if st.index is not None else None,
                "duration_minutes": round(r.duration_s / 60, 1) if r is not None else None,
                "typical_minutes": round(r.static_duration_s / 60, 1) if r is not None else None,
                "band": st.band,
                "held_minutes": round(st.held_for(moment).total_seconds() / 60, 1)
                if moment
                else None,
            }
        )
    # acute first (deploy now), then slowest
    rows.sort(
        key=lambda r: (
            r["condition"] != "ACUTE",
            r["speed_kmh"] if r["speed_kmh"] is not None else 999,
        )
    )
    acute = sum(1 for r in rows if r["condition"] == "ACUTE")
    return {
        "count": len(rows),
        "acute": acute,
        "chronic": len(rows) - acute,
        "corridors": rows,
        "note": (
            "Slow now, and no officer posted on them. Acute (slow AND worse than usual) is the "
            "dispatch list; chronic (always slow here) is structural. A car-probe slowdown "
            "under-samples the two/three-wheelers, so confirm before deploying."
        ),
    }
