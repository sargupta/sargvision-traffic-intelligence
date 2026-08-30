"""Anomaly engine — deviation against the corridor's OWN baseline.

Not against a city average, and not against free-flow. "Unusual" means unusual for
this road, at this hour, on this kind of day.

Thresholds are configuration, never constants. They were calibrated against 7,333
Siliguri observations and must be recalibrated for any other city or data source.
"""
from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from packages.domain.models import Severity


@dataclass(frozen=True)
class Thresholds:
    moderate: float = 30.0
    high: float = 45.0
    critical: float = 60.0
    resolve: float = 20.0   # hysteresis: exit below this, not at the entry threshold

    def classify(self, deviation_pct: float) -> Severity:
        if deviation_pct >= self.critical:
            return Severity.CRITICAL
        if deviation_pct >= self.high:
            return Severity.HIGH
        if deviation_pct >= self.moderate:
            return Severity.MODERATE
        return Severity.EXPECTED


SILIGURI = Thresholds()


def score(observations: pl.DataFrame, baselines: pl.DataFrame) -> pl.DataFrame:
    joined = observations.join(baselines, on=["unit_id", "day_type", "hour"], how="inner")
    iqr = pl.col("p75_seconds") - pl.col("p25_seconds")
    return joined.with_columns(
        (
            (pl.col("traffic_seconds") - pl.col("median_seconds"))
            / pl.col("median_seconds") * 100
        ).alias("deviation_pct"),
        pl.when(iqr > 0)
        .then((pl.col("traffic_seconds") - pl.col("median_seconds")) / iqr)
        .otherwise(None)
        .alias("robust_z"),
        (pl.col("traffic_seconds") > pl.col("p90_seconds")).alias("above_p90"),
    )
