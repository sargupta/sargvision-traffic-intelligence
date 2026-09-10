"""The canon the review board stands on.

Not a panel of invented professors. When a console tells a police control room
"a board of experts recommends X", the first thing a sceptical officer does is
ask who — and a made-up name ends the system's credibility on the spot. So the
board's authority is the real thing instead: the bodies of traffic-engineering
knowledge taught and published at the field's leading schools, and the Indian
codes that actually govern a junction in Siliguri. Every live recommendation
names its SEAT (the discipline) and its SOURCE (the standard or the
peer-reviewed result), so the officer — or the Commissioner — can check it.

These are the disciplines a graduate traffic-engineering programme (an MIT, an
Oxford, an IIT, an IISc) is built from; the console applies them to the live
situation, it does not claim their faculty endorse it.
"""

from __future__ import annotations

# seat_id -> {discipline, source}. Keep the sources checkable and specific.
SEATS: dict[str, dict[str, str]] = {
    "incident_management": {
        "discipline": "Traffic incident management",
        "source": (
            "Highway Capacity Manual, 6th ed. (Transportation Research Board); "
            "FHWA Traffic Incident Management; the queueing result that incident "
            "delay scales with clearance time, so clearance speed is the lever."
        ),
    },
    "junction_operations": {
        "discipline": "Signalised-junction operations under mixed traffic",
        "source": (
            "IRC:93 signal-design guidance; HCM signalised-intersection delay; "
            "Vajeeran et al. 2020 on manual point control in heterogeneous traffic."
        ),
    },
    "junction_geometry": {
        "discipline": "Junction geometry & capacity",
        "source": (
            "IRC:SP:41 urban-junction design; Siliguri CMP 2011 volume-to-capacity; "
            "HCM capacity analysis for an over-capacity, non-signalised junction."
        ),
    },
    "adaptive_signal": {
        "discipline": "Adaptive signal control",
        "source": (
            "Webster 1958 (TRRL) cycle-delay minimisation; SCOOT/SCATS adaptive "
            "control; Google Project Green Light — under the doctrine measure, "
            "don't optimise (ADR-0007)."
        ),
    },
    "access_management": {
        "discipline": "Access management & side friction",
        "source": (
            "HCM side-friction capacity adjustment; Pandey & Vasudevan 2017 on kerb "
            "friction on Indian arterials; IRC bus-bay / kerb-stop standards."
        ),
    },
    "network_assignment": {
        "discipline": "Network assignment & induced demand",
        "source": (
            "Duranton & Turner 2011, the fundamental law of road congestion; "
            "Braess's paradox; cordon before/after across the diversion network."
        ),
    },
    "road_safety": {
        "discipline": "Road-safety engineering & enforcement",
        "source": (
            "Roy, Mohammadi & Roy 2026 — Siliguri emerging-hotspot analysis "
            "(n=315, 36 months); Sherman 1990 on how enforcement deterrence "
            "decays within hours to days; iRAP / road-safety-audit doctrine."
        ),
    },
    "measurement": {
        "discipline": "Measurement discipline",
        "source": (
            "Regression to the mean; matched-control before/after; the car-probe "
            "blind spot to the two- and three-wheelers that dominate Siliguri."
        ),
    },
}


def seat(seat_id: str) -> dict[str, str]:
    """The discipline and source for a seat id, or an empty pair if unknown."""
    return SEATS.get(seat_id, {"discipline": "", "source": ""})
