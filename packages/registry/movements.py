"""The movement registry — what the system watches, and how often.

A monitored movement is an origin zone, a destination zone, a priority and a
sampling interval. The registry is the only thing that decides what gets
collected, so the API budget and the compliance surface are both bounded by one
readable file rather than scattered through the collector.

Priorities exist because sampling is not free and not all movements matter
equally. A HIGH movement is polled every five minutes; a LOW one every twenty.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

DEFAULT_PATH = Path("data/curated/registry.json")


@dataclass(frozen=True)
class MonitoredMovement:
    movement_id: str
    name: str
    origin_zone: str
    origin_name: str
    origin_lat: float
    origin_lon: float
    dest_zone: str
    dest_name: str
    dest_lat: float
    dest_lon: float
    priority: str  # HIGH | MEDIUM | LOW
    sampling_seconds: int
    active: bool
    baseline_observations: int
    median_distance_m: float

    def as_dict(self) -> dict:
        return asdict(self)


PRIORITY_SAMPLING = {"HIGH": 300, "MEDIUM": 600, "LOW": 1200}


@dataclass
class Registry:
    movements: list[MonitoredMovement]

    @property
    def active(self) -> list[MonitoredMovement]:
        return [m for m in self.movements if m.active]

    def by_id(self, movement_id: str) -> MonitoredMovement | None:
        return next((m for m in self.movements if m.movement_id == movement_id), None)

    def calls_per_hour(self) -> int:
        """What the registry costs in requests. Kept visible on purpose."""
        return sum(round(3600 / m.sampling_seconds) for m in self.active)

    def save(self, path: Path = DEFAULT_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([m.as_dict() for m in self.movements], indent=1))


def build_from_analytics(movements: pl.DataFrame, reliability: pl.DataFrame) -> Registry:
    """Derive the registry from what the baseline layer can actually support.

    A movement is only worth monitoring live if there is a historical baseline
    to compare it against — otherwise the system can report that traffic is
    slow but not whether that is unusual, which is the whole product. Priority
    follows evidence and volatility: the movements we know most about and that
    move around most are the ones worth the sampling budget.
    """
    buffers = dict(zip(reliability["movement_id"], reliability["buffer_pct"], strict=True))
    volatile = sorted(buffers.values(), reverse=True)
    top_third = volatile[max(0, len(volatile) // 3 - 1)] if volatile else 0.0

    out: list[MonitoredMovement] = []
    for row in movements.sort("sample_size", descending=True).iter_rows(named=True):
        buffer = buffers.get(row["movement_id"], 0.0)
        if row["confidence"] == "HIGH" and buffer >= top_third:
            priority = "HIGH"
        elif row["confidence"] in ("HIGH", "MODERATE"):
            priority = "MEDIUM"
        else:
            priority = "LOW"

        out.append(
            MonitoredMovement(
                movement_id=row["movement_id"],
                name=row["movement_name"],
                origin_zone=row["origin_zone"],
                origin_name=row["origin_zone_name"],
                origin_lat=round(row["origin_lat"], 6),
                origin_lon=round(row["origin_lon"], 6),
                dest_zone=row["dest_zone"],
                dest_name=row["dest_zone_name"],
                dest_lat=round(row["dest_lat"], 6),
                dest_lon=round(row["dest_lon"], 6),
                priority=priority,
                sampling_seconds=PRIORITY_SAMPLING[priority],
                active=True,
                baseline_observations=int(row["sample_size"]),
                median_distance_m=round(row["median_distance_m"], 1),
            )
        )
    return Registry(movements=out)


def load_registry(path: Path = DEFAULT_PATH) -> Registry:
    raw = json.loads(path.read_text())
    return Registry(movements=[MonitoredMovement(**r) for r in raw])
