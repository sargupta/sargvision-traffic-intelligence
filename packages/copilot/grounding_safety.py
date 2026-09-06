"""The accident record, held here rather than measured.

The same study evidence the network reference shows, in one place so the copilot,
the intervention playbook and anything else read it identically. It is a study
finding (Roy, Mohammadi & Roy, Geographies 6(2):55, 2026 — 2021-23), not
something the live system observes, and it is what lets the tools answer "which
junctions are dangerous" — a different question from "which are congested".
"""

from __future__ import annotations

SAFETY: dict[str, str] = {
    "J_VENUS_MORE": (
        "Highest accident density in the city (14.21/km2), intensifying — and one of the "
        "LEAST congested (V/C 0.39). Danger, not delay."
    ),
    "J_DARJEELING_MORE": "Evening accident leader, 16.13% of the evening period's incidents.",
    "J_CHAMPASARI_MORE": "Secondary accident hotspot.",
}
