"""Replay clock — historical data streamed as simulated time.

    HISTORICAL DATA -> REPLAY CLOCK -> INTELLIGENCE ENGINE -> EVENTS

The engine cannot distinguish this from a live feed. That is exactly what makes it a
valid architecture proof — and exactly why the mode must be labelled everywhere it
surfaces. Claiming live monitoring while replaying history would destroy the
credibility this product sells.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import polars as pl

from packages.analytics.events import CorridorTracker


@dataclass
class ReplaySession:
    date: int
    observations: pl.DataFrame
    trackers: dict[str, CorridorTracker] = field(default_factory=dict)
    events: list[dict] = field(default_factory=list)
    is_live: bool = False  # never true. checked by the API.
    mode: str = "HISTORICAL_REPLAY"

    def run(self) -> Iterator[dict]:
        """Yield one tick per hour, with any state transitions in that hour."""
        for (hour,), chunk in self.observations.sort("hour").group_by(
            ["hour"], maintain_order=True
        ):
            tick = {"hour": int(hour), "transitions": [], "mode": self.mode}
            for row in chunk.iter_rows(named=True):
                cid = row["corridor_id"]
                tracker = self.trackers.setdefault(cid, CorridorTracker(cid))
                label = tracker.observe(row["deviation_pct"], int(hour))
                if label:
                    entry = {
                        "corridor_id": cid,
                        "transition": label,
                        "deviation_pct": round(row["deviation_pct"], 1),
                        "peak_deviation_pct": round(tracker.peak_deviation, 1),
                    }
                    tick["transitions"].append(entry)
                    if label.endswith("->ACTIVE"):
                        self.events.append({**entry, "hour": int(hour)})
            yield tick
