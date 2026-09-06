"""The Siliguri evidence base — the facts the console's suggestions must be
grounded in, held in one place so the copilot, the intervention playbook and the
junction reference all read them identically.

This replaces an earlier three-line accident dict that presented the accident
study as a ranking. It is not a ranking. Everything here carries the discipline
the underlying research (west-bengal-gov-ai/docs) established:

  * The accident study is n = 315 over 36 months. It is a PRIOR over where to
    instrument, never a ranking, and never the basis of an "X% of accidents at Y"
    claim.  (Roy, Mohammadi & Roy, Geographies 6(2):55, 2026; 01-diagnostic §2.3)
  * Congestion peaks by DAY; accidents peak at NIGHT (lean-hours density
    14.21/km², 67.67% concentration). The places Siliguri loses time and the
    places it loses lives are different places and different hours, and they need
    different interventions.
  * Venus More is the most DANGEROUS junction and one of the LEAST congested
    (V/C 0.39). A congestion remedy there is a category error.
  * The measurement instrument (Google Routes probe) under-samples two- and
    three-wheelers and totos — the modes that dominate Siliguri and cause most of
    the side friction — so a car-probe slowdown is not proof a road is failing.
"""

from __future__ import annotations

# The probe blind spot, stated wherever a congestion figure is used.
PROBE_CAVEAT = (
    "Our speed comes from Google's travel-time probe, which is drawn from the "
    "car/running-lane stream. Siliguri is dominated by two-wheelers, autos and "
    "totos, which filter and seep and lose far less time than cars — so a probe "
    "slowdown can over-state a problem the two-wheeler majority is not feeling. "
    "Confirm with an officer or camera before acting on the number alone."
)

# The evaluation discipline every proposed intervention must carry.
MEASUREMENT_PROTOCOL = (
    "Measure it: this corridor's before/after against a MATCHED control corridor "
    "(same weekday and hour), on a mode-appropriate metric (queue and discharge, "
    "not car-probe travel time alone); never act on a single-day spike "
    "(regression to the mean); and re-measure at ~2–4 weeks and ~3 months, "
    "because a day-one gain over-states the lasting one."
)

# Per-junction evidence, keyed by junction_id. `safety` is the human-readable
# note surfaced in the junction reference; the structured fields drive the
# intervention playbook. `trend` is the EHSA class from the 2026 accident study.
JUNCTION_EVIDENCE: dict[str, dict] = {
    "J_JALPAI_MORE": {
        "congestion_note": (
            "Worst volume-to-capacity in the city (V/C 1.14, CMP 2011) and it is "
            "NON-SIGNALISED — the most conventional, most fixable junction in the "
            "evidence, and outside Google Green Light's reach entirely."
        ),
        "structural": True,
    },
    "J_MAHANANDA_BRIDGE": {
        "congestion_note": "Second-worst V/C (1.13, signalised) on Hill Cart Road.",
    },
    "J_VENUS_MORE": {
        "safety": (
            "Highest accident density in the 2026 study (14.21/km², lean hours) and "
            "one of only two INTENSIFYING+PERSISTENT hotspots (zone A10) — yet one "
            "of the LEAST congested junctions (V/C 0.39). Danger, not delay: a "
            "night-time speed and geometry problem."
        ),
        "accident_zone": "A10",
        "trend": "intensifying+persistent",
        "period": "night/lean",
        "do_not": "congestion",  # never propose a congestion remedy here
    },
    "J_NAUKAGHAT": {
        "safety": (
            "Morning-peak accident leader (zone A3, AH2 × Noukaghat × Burdwan) and "
            "one of only two INTENSIFYING hotspots — accidents becoming more "
            "frequent and more severe."
        ),
        "accident_zone": "A3",
        "trend": "intensifying",
        "period": "morning_peak",
    },
    "J_ASHIGHAR_MORE": {
        "safety": (
            "Accident zone A5 (Eastern Bypass × Ghogomali Road) — high-speed "
            "through-traffic; a hotspot the earlier reporting missed."
        ),
        "accident_zone": "A5",
        "trend": "persistent",
        "period": "multi",
    },
    "J_DARJEELING_MORE": {
        "safety": (
            "Evening-peak accident leader (zone A13, Hill Cart & AH2, Darjeeling "
            "More → Junction, 16.13% of the evening period)."
        ),
        "accident_zone": "A13",
        "trend": "high",
        "period": "evening_peak",
        "congestion_note": "On Hill Cart Road (V/C 1.03) — matters on volume, not per-vehicle delay.",
    },
    "J_CHAMPASARI_MORE": {
        "safety": "Secondary accident hotspot, persistent (zones A7/A12). V/C 1.09.",
        "accident_zone": "A12",
        "trend": "persistent",
    },
    "J_AIR_VIEW_MORE": {
        "safety": "Accident zone A8 (Hill Cart × Burdwan near Airview/Sevoke More); midday leader.",
        "accident_zone": "A8",
        "trend": "high",
        "congestion_note": "Worst TTI approaches in the 2019 survey (up to 4.095).",
    },
    "J_JHANKAAR_MORE": {
        "safety": "Accident zone A15 (with Hill Cart/Burdwan/AH2 near Airview), lean hours.",
        "accident_zone": "A15",
        "trend": "lean",
    },
}

# The named high-volume arterials — Hill Cart Road matters on VOLUME, not
# per-vehicle delay (rank on volume-weighted person-delay). CMP 2011 ADT in PCU.
ARTERIAL_VOLUME = {
    "Hill Cart Road": "47,639–83,828 PCU/day (highest in the city)",
    "Sevoke Road": "42,937–54,150 PCU/day",
}

# Backward-compatible flat map: junction_id → safety sentence, for the junction
# reference widget. Derived from JUNCTION_EVIDENCE so there is one source.
SAFETY: dict[str, str] = {
    jid: ev["safety"] for jid, ev in JUNCTION_EVIDENCE.items() if ev.get("safety")
}
