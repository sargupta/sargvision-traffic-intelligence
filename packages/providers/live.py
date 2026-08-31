"""Live observation providers.

Two implementations behind one interface, because the demonstrator and the
deployment have different constraints and the engine must not know which it is
talking to.

**Compliance boundary — read before adding a third.**

Google's Maps Service Specific Terms permit caching latitude and longitude
only; travel times obtained from the Routes API may not be retained to build a
persistent dataset, and the Terms of Service separately prohibit creating
derivative datasets from the content. A real-time system that keeps every
duration it has ever fetched in BigQuery is precisely the thing those clauses
describe.

So `GoogleRoutesProvider` holds observations in memory for a bounded window and
writes nothing durable. The persistent analytical history in this product comes
from the 2019 open dataset, which is CC BY 4.0 and may be retained. If live
history is needed later, the sanctioned route is a product licensed for it
(Roads Management Insights sits under the Analytics Service Specific Terms) or
first-party probe data — not a longer cache on this one.

`ReplayProvider` reads the open dataset and emits it as though it were arriving
now. It is the default for demonstration: deterministic, free, and outside the
terms question entirely.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

import polars as pl

from packages.registry.movements import MonitoredMovement


@dataclass(frozen=True)
class Sample:
    """One live reading for one movement."""

    movement_id: str
    observed_at: datetime
    traffic_seconds: float
    distance_m: float
    source: str
    is_live: bool


class ObservationProvider(Protocol):
    name: str
    is_live: bool
    retains_durations: bool

    def sample(self, movements: list[MonitoredMovement], at: datetime) -> list[Sample]: ...
    def provenance(self) -> dict: ...


class ReplayProvider:
    """Streams the 2019 dataset as if it were happening now.

    A given wall-clock instant maps to the same instant on a chosen historical
    date, so the same demonstration runs identically every time — which is what
    makes it a demonstration rather than a hope.
    """

    name = "siliguri-2019-replay"
    is_live = False
    retains_durations = True  # CC BY 4.0 data; retention is permitted

    def __init__(self, observations: pl.DataFrame, replay_date: int, speed: float = 60.0):
        self.speed = speed
        self.replay_date = replay_date
        self._day = (
            observations.filter(pl.col("date") == replay_date)
            if "date" in observations.columns
            else observations
        )
        # Pre-bucket to five minutes so a sample is a median rather than one trip.
        self._buckets = (
            self._day.with_columns(
                (pl.col("hour").cast(pl.Int64) * 60 + (pl.col("minute_of_day") % 60)).alias("_mod")
            )
            .with_columns((pl.col("_mod") // 5 * 5).alias("bucket"))
            .group_by("movement_id", "bucket")
            .agg(
                pl.col("traffic_seconds").median().alias("traffic_seconds"),
                pl.col("distance_m").median().alias("distance_m"),
                pl.len().alias("n"),
            )
        )
        self._index: dict[tuple[str, int], tuple[float, float]] = {
            (r["movement_id"], int(r["bucket"])): (r["traffic_seconds"], r["distance_m"])
            for r in self._buckets.iter_rows(named=True)
        }

    def sample(self, movements: list[MonitoredMovement], at: datetime) -> list[Sample]:
        bucket = (at.hour * 60 + at.minute) // 5 * 5
        out: list[Sample] = []
        for m in movements:
            # Walk back to the most recent bucket this movement was observed in,
            # rather than inventing a reading it never had.
            for back in range(0, 60, 5):
                hit = self._index.get((m.movement_id, (bucket - back) % 1440))
                if hit:
                    out.append(
                        Sample(
                            movement_id=m.movement_id,
                            observed_at=at,
                            traffic_seconds=float(hit[0]),
                            distance_m=float(hit[1]),
                            source=self.name,
                            is_live=False,
                        )
                    )
                    break
        return out

    def provenance(self) -> dict:
        return {
            "source": self.name,
            "licence": "CC BY 4.0",
            "is_live": False,
            "mode": "HISTORICAL_REPLAY",
            "replay_date": self.replay_date,
            "retains_durations": True,
            "note": (
                "Observations are replayed from the 2019 open dataset at "
                f"{self.speed:.0f}x. Nothing here reflects current conditions."
            ),
        }


class GoogleRoutesProvider:
    """Live durations from the Routes API, held in memory only.

    `retains_durations` is False and is checked by the collector: this provider
    must never be wired to a durable store. See the module docstring.
    """

    name = "google-routes"
    is_live = True
    retains_durations = False

    ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"
    RETENTION = timedelta(hours=6)

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ROUTES_API_KEY", "")
        self._recent: list[Sample] = []

    def sample(self, movements: list[MonitoredMovement], at: datetime) -> list[Sample]:
        if not self.api_key:
            raise RuntimeError(
                "ROUTES_API_KEY is not set. The live provider will not start without "
                "one; use ReplayProvider for demonstration."
            )
        import httpx

        out: list[Sample] = []
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        }
        with httpx.Client(timeout=10.0) as client:
            for m in movements:
                body = {
                    "origin": {
                        "location": {
                            "latLng": {"latitude": m.origin_lat, "longitude": m.origin_lon}
                        }
                    },
                    "destination": {
                        "location": {"latLng": {"latitude": m.dest_lat, "longitude": m.dest_lon}}
                    },
                    "travelMode": "DRIVE",
                    "routingPreference": "TRAFFIC_AWARE",
                }
                r = client.post(self.ENDPOINT, headers=headers, json=body)
                r.raise_for_status()
                routes = r.json().get("routes", [])
                if not routes:
                    continue
                out.append(
                    Sample(
                        movement_id=m.movement_id,
                        observed_at=at,
                        traffic_seconds=float(str(routes[0]["duration"]).rstrip("s")),
                        distance_m=float(routes[0]["distanceMeters"]),
                        source=self.name,
                        is_live=True,
                    )
                )

        # Bounded in-memory window. Nothing is written to disk.
        cutoff = at - self.RETENTION
        self._recent = [s for s in self._recent + out if s.observed_at >= cutoff]
        return out

    def provenance(self) -> dict:
        return {
            "source": self.name,
            "licence": "Google Maps Platform Terms of Service",
            "is_live": True,
            "mode": "LIVE",
            "retains_durations": False,
            "note": (
                "Durations are held in memory for at most 6 hours and are never "
                "persisted. Maps Service Specific Terms permit caching lat/lng only."
            ),
        }
