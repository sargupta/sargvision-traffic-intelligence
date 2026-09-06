"""A deployment and its measured effect.

An officer is posted to a road to fix a jam. The question the traffic police
cannot answer today — and the reason this system exists — is whether it worked,
and by how much. This module records the posting and measures it two ways:

  magnitude       the road's speed just before the posting vs while it was on —
                  in km/h, the number an officer and a Commissioner both read.
  counterfactual  the road's index during the posting vs its OWN typical for this
                  weekday and hour, so "it got better" is not just the jam easing
                  as it always does at this time. This is what the learned
                  baseline is for; without it we can only observe, not attribute.

The discipline is the copilot's: it never claims the officer caused the change.
It states what moved and how it compares to the usual, and names what that does
and does not establish.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime

# How much the index must move to count as a real change rather than noise. The
# same order as the band hysteresis; below this the honest verdict is "no
# measurable change", not a story told from a rounding error.
INDEX_NOISE = 0.05


@dataclass(frozen=True)
class DeploySample:
    """The worst condition across the deployment's corridors at one moment —
    lowest speed, and the index that went with it."""

    at: datetime
    speed_kmh: float | None
    index: float | None
    band: str

    def as_dict(self) -> dict:
        return {
            "at": self.at.isoformat(timespec="seconds"),
            "speed_kmh": round(self.speed_kmh, 1) if self.speed_kmh is not None else None,
            "index": round(self.index, 3) if self.index is not None else None,
            "band": self.band,
        }


def _median(xs: list[float]) -> float | None:
    return round(statistics.median(xs), 3) if xs else None


@dataclass
class Deployment:
    """One posting, its readings before and during, and what they measure."""

    deployment_id: str
    corridor_ids: list[str]
    primary_corridor_id: str
    location_name: str
    by: str  # the duty officer who logged the posting
    unit: str  # who was posted on the ground
    purpose: str
    started_at: datetime
    before: list[DeploySample] = field(default_factory=list)
    during: list[DeploySample] = field(default_factory=list)
    ended_at: datetime | None = None
    incident_id: str | None = None
    note: str | None = None

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    def record(self, sample: DeploySample) -> None:
        self.during.append(sample)

    # ── the measurement ──────────────────────────────────────────────────────
    def effect(self, history=None, now: datetime | None = None) -> dict:
        moment = now or self.ended_at or (self.during[-1].at if self.during else self.started_at)

        before_speed = _median([s.speed_kmh for s in self.before if s.speed_kmh is not None])
        during_speed = _median([s.speed_kmh for s in self.during if s.speed_kmh is not None])
        before_index = _median([s.index for s in self.before if s.index is not None])
        during_index = _median([s.index for s in self.during if s.index is not None])

        delta_speed = (
            round(during_speed - before_speed, 1)
            if before_speed is not None and during_speed is not None
            else None
        )
        # Negative index delta is an improvement (slower→faster).
        delta_index = (
            round(during_index - before_index, 3)
            if before_index is not None and during_index is not None
            else None
        )

        # The counterfactual: what does THIS corridor usually do at this weekday
        # and hour? If the road during the posting beat its own typical, the
        # improvement is more than the jam easing as it always does.
        typical_index = None
        vs_typical = None
        if history is not None:
            base = history.corridors.get(self.primary_corridor_id)
            if base is not None:
                b = base.baseline(self.started_at.weekday(), self.started_at.hour)
                if b and b["n"] >= 5:
                    typical_index = b["p50"]
                    if during_index is not None and typical_index is not None:
                        if during_index <= typical_index - INDEX_NOISE:
                            vs_typical = "better than this road's usual for the hour"
                        elif during_index >= typical_index + INDEX_NOISE:
                            vs_typical = "worse than this road's usual for the hour"
                        else:
                            vs_typical = "about this road's usual for the hour"

        verdict, confidence = self._verdict(delta_index, vs_typical, before_index, during_index)

        return {
            "deployment_id": self.deployment_id,
            "location": self.location_name,
            "unit": self.unit,
            "purpose": self.purpose,
            "active": self.is_active,
            "minutes_posted": round((moment - self.started_at).total_seconds() / 60, 1),
            "before_speed_kmh": before_speed,
            "during_speed_kmh": during_speed,
            "delta_speed_kmh": delta_speed,
            "before_index": before_index,
            "during_index": during_index,
            "delta_index": delta_index,
            "typical_index": typical_index,
            "vs_typical": vs_typical,
            "verdict": verdict,
            "confidence": confidence,
            "samples": {"before": len(self.before), "during": len(self.during)},
            "limitation": self._limitation(delta_index, typical_index),
        }

    @staticmethod
    def _verdict(delta_index, vs_typical, before_index, during_index) -> tuple[str, str]:
        if before_index is None or during_index is None:
            return ("not yet measurable", "low")
        if delta_index is None:
            return ("not yet measurable", "low")
        moved = delta_index <= -INDEX_NOISE
        worse = delta_index >= INDEX_NOISE
        if moved and vs_typical == "better than this road's usual for the hour":
            return ("improved while posted, and beat this road's usual", "good")
        if moved:
            # improved, but we cannot yet separate the posting from the usual easing
            return ("improved while posted", "fair")
        if worse:
            return ("worse while posted", "fair")
        return ("no measurable change while posted", "fair")

    @staticmethod
    def _limitation(delta_index, typical_index) -> str:
        base = (
            "This measures what the road did while the officer was posted, in the "
            "road's own before/after. "
        )
        if typical_index is None:
            return (
                base + "There is not yet enough history for this corridor at this weekday and "
                "hour to say whether the change beats its usual pattern — so this cannot "
                "yet separate the posting's effect from traffic easing on its own. The "
                "baseline sharpens as the system keeps observing."
            )
        return (
            base + "It is compared against this corridor's own typical for the weekday and "
            "hour, which controls for the usual pattern — but a single posting on a "
            "single day is evidence, not proof. Repeat postings build the case."
        )

    def as_dict(self, history=None, now: datetime | None = None) -> dict:
        return {
            "deployment_id": self.deployment_id,
            "corridor_ids": self.corridor_ids,
            "primary_corridor_id": self.primary_corridor_id,
            "location_name": self.location_name,
            "by": self.by,
            "unit": self.unit,
            "purpose": self.purpose,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "ended_at": self.ended_at.isoformat(timespec="seconds") if self.ended_at else None,
            "incident_id": self.incident_id,
            "note": self.note,
            "before": [s.as_dict() for s in self.before],
            "during": [s.as_dict() for s in self.during],
            "effect": self.effect(history, now),
        }


def deployment_id(corridor_id: str, at: datetime) -> str:
    return f"DEP-{at.strftime('%Y%m%d-%H%M')}-{corridor_id[:16]}"
