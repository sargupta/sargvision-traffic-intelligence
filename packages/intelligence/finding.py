"""What the discovery engine emits, and what the rest of the system consumes.

A finding is not a sentence. It is a claim, the evidence that supports it, the
statistical test that survived, the confidence it earned, and the view that
shows it. The prose comes last and is generated from the structure — never the
other way round.

    Analytics discovers.  AI explains.  Humans decide.

The `view` field is what lets the interface reorganise itself around a finding
without any model inventing a query: the detector that found the pattern also
states how to show it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Kind(str, Enum):
    RELIABILITY = "RELIABILITY"          # this movement is hard to plan around
    DIVERGENCE = "DIVERGENCE"            # two things that should agree, do not
    ASYMMETRY = "ASYMMETRY"              # one direction differs from the other
    PERIOD = "PERIOD"                    # a time window behaves differently
    DAY_TYPE = "DAY_TYPE"                # weekday and weekend differ
    RECURRENCE = "RECURRENCE"            # the same departure keeps happening
    EVIDENCE_GAP = "EVIDENCE_GAP"        # we cannot see here


class Confidence(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"


@dataclass(frozen=True)
class Evidence:
    """The numbers a reviewer would demand before believing the claim."""

    observations: int
    test: str
    statistic: float | None
    p_value: float | None
    effect: float
    effect_unit: str
    comparison: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class View:
    """How the interface should reorganise itself to show this finding.

    Emitted by the detector, not by a language model, so the visualisation is
    always the one the evidence supports.
    """

    layout: str                     # map+detail | compare | timeline | coverage
    focus_movements: list[str] = field(default_factory=list)
    focus_zones: list[str] = field(default_factory=list)
    focus_hours: list[int] = field(default_factory=list)
    day_types: list[str] = field(default_factory=list)
    encode: str = "reliability"     # what the arcs should mean
    series: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Finding:
    id: str
    kind: Kind
    title: str
    claim: str
    interpretation: str
    limitation: str
    evidence: Evidence
    view: View
    confidence: Confidence
    impact: float          # 0-1, how much travel it touches
    novelty: float         # 0-1, how far from what the rest of the city does
    recurrence: float      # 0-1, how consistently it repeats
    movements: list[str] = field(default_factory=list)
    zones: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)

    @property
    def priority(self) -> float:
        """Impact × Confidence × Novelty × Recurrence.

        Multiplicative on purpose: a finding that scores zero on any one of
        these is not worth surfacing, and a sum would let a high impact carry
        an unrepeatable, low-confidence result to the top of the feed.
        """
        weight = {Confidence.HIGH: 1.0, Confidence.MODERATE: 0.65, Confidence.LOW: 0.3}
        return round(
            self.impact * weight[self.confidence] * self.novelty * self.recurrence, 4
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "title": self.title,
            "claim": self.claim,
            "interpretation": self.interpretation,
            "limitation": self.limitation,
            "evidence": self.evidence.as_dict(),
            "view": self.view.as_dict(),
            "confidence": self.confidence.value,
            "impact": round(self.impact, 4),
            "novelty": round(self.novelty, 4),
            "recurrence": round(self.recurrence, 4),
            "priority": self.priority,
            "movements": self.movements,
            "zones": self.zones,
            "related": self.related,
        }
