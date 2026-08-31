"""Historical provider — the 2019 Siliguri open dataset.

This is the demonstrator's data source. It is NOT live monitoring, and
`is_live = False` is checked by the API so the UI can never mislabel it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import polars as pl

DEFAULT = Path("data/processed/siliguri_observations.parquet")


class HistoricalProvider:
    name = "siliguri-2019-open"
    is_live = False

    def __init__(self, path: Path = DEFAULT) -> None:
        self.path = path
        self._df: pl.DataFrame | None = None

    def _load(self) -> pl.DataFrame:
        if self._df is None:
            d = pl.read_parquet(self.path)
            self._df = d.with_columns(
                pl.col("traffic_s").cast(pl.Int64).alias("traffic_seconds"),
                pl.col("notraffic_s").cast(pl.Int64).alias("freeflow_seconds"),
                pl.col("dist_m").cast(pl.Int64).alias("distance_m"),
            ).filter(
                (pl.col("traffic_seconds") > 0)
                & (pl.col("freeflow_seconds") > 0)
                & (pl.col("distance_m") > 0)
            )
        return self._df

    def fetch_observations(self, start: datetime, end: datetime) -> pl.DataFrame:
        d = self._load()
        lo, hi = int(start.strftime("%Y%m%d")), int(end.strftime("%Y%m%d"))
        return d.filter((pl.col("date") >= lo) & (pl.col("date") <= hi))

    def available_dates(self) -> list[int]:
        return sorted(self._load()["date"].unique().to_list())

    def provenance(self) -> dict:
        return {
            "source": (
                "Akbar, Couture, Duranton & Storeygard, 'Mobility and Congestion in Urban "
                "India', American Economic Review 113(4), 2023. Zenodo 10.5281/zenodo.10499064."
            ),
            "licence": "CC BY 4.0",
            "window": "2019-06-13 to 2019-11-05",
            "count": "101,418 valid primary-route observations (115,347 raw joined)",
            "is_live": False,
            "limitation": (
                "Historical, not live. Modelled travel times for simulated trips, not observed "
                "probe traces. Corridor density is uneven."
            ),
        }
