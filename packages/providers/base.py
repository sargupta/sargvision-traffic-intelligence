"""Data provider boundary.

The platform must not be architected around one vendor. Everything upstream of this
protocol is swappable: historical open data today, an authorised live product later,
first-party probe data eventually.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import polars as pl


class TrafficDataProvider(Protocol):
    """Anything that can supply traffic observations."""

    name: str
    is_live: bool

    def fetch_observations(self, start: datetime, end: datetime) -> pl.DataFrame:
        """Columns: corridor_id, observed_at, traffic_seconds, freeflow_seconds, distance_m."""
        ...

    def provenance(self) -> dict:
        """Source, licence and limitations — surfaced with every metric derived from it."""
        ...
