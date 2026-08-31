"""Anomaly engine — deviation against a movement's OWN baseline.

Not against a city average, and not against free-flow. "Unusual" means unusual
for this movement, at this hour, on this kind of day. A journey that always
takes 40 minutes is not an anomaly at 40 minutes.

Thresholds are configuration, never constants. They were calibrated against the
Siliguri 2019 sample and must be recalibrated for any other city or source.

Deviation is measured in **pace** — seconds per kilometre — not in journey time.
Zone-to-zone movements pool trips of very different lengths, so a deviation
computed on raw seconds would flag every long journey as an anomaly and would be
measuring geography rather than congestion. See `packages.analytics.baselines`.

**These are historical anomalies.** Every row is an observation from 2019 that
departed from its own 2019 baseline. Nothing in this module detects a live
event, and the distinction must survive into every screen that shows the output.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from packages.analytics import baselines as base
from packages.domain.canonical import Confidence
from packages.domain.models import Severity


@dataclass(frozen=True)
class Thresholds:
    moderate: float = 30.0
    high: float = 45.0
    critical: float = 60.0
    resolve: float = 20.0  # hysteresis: exit below this, not at the entry threshold

    def classify(self, deviation_pct: float) -> Severity:
        if deviation_pct >= self.critical:
            return Severity.CRITICAL
        if deviation_pct >= self.high:
            return Severity.HIGH
        if deviation_pct >= self.moderate:
            return Severity.MODERATE
        return Severity.EXPECTED


SILIGURI = Thresholds()

KEYS = ["movement_id", "day_type", "hour"]


def score(
    obs: pl.DataFrame, baselines: pl.DataFrame, thresholds: Thresholds = SILIGURI
) -> pl.DataFrame:
    """Attach expected time, deviation and severity to every scorable observation.

    An inner join is deliberate: observations whose bin has no published
    baseline are dropped rather than scored against something coarser. We would
    rather say nothing about them than manufacture an expectation.
    """
    joined = base.with_pace(obs).join(
        baselines.select(
            *KEYS,
            "median_pace",
            "p25_pace",
            "p75_pace",
            "p90_pace",
            "sample_size",
            "confidence",
        ),
        on=KEYS,
        how="inner",
    )

    return (
        joined.with_columns(
            ((pl.col("pace") - pl.col("median_pace")) / pl.col("median_pace") * 100).alias(
                "deviation_pct"
            ),
            # Expected time for a journey of *this* length, so the two figures
            # an officer compares are like for like.
            (pl.col("median_pace") * pl.col("distance_m") / 1000 / 60)
            .round(1)
            .alias("expected_minutes"),
            (pl.col("traffic_seconds") / 60).round(1).alias("observed_minutes"),
        )
        .with_columns(
            pl.col("deviation_pct")
            .map_elements(lambda d: thresholds.classify(d).value, return_dtype=pl.Utf8)
            .alias("severity")
        )
        .with_columns(
            # An anomaly is only as trustworthy as the baseline it is measured
            # against, so the bin's confidence is carried through unchanged.
            pl.col("confidence").alias("baseline_confidence"),
            pl.lit(True).alias("is_historical"),
            pl.lit(False).alias("is_live"),
        )
    )


def anomalies_only(scored: pl.DataFrame) -> pl.DataFrame:
    return scored.filter(pl.col("severity") != "EXPECTED").sort("deviation_pct", descending=True)


def summary(scored: pl.DataFrame) -> pl.DataFrame:
    return (
        scored.group_by("severity")
        .agg(pl.len().alias("observations"))
        .sort("observations", descending=True)
    )


def by_movement(scored: pl.DataFrame, min_scored: int = 100) -> pl.DataFrame:
    """How often each movement departs from its own normal."""
    return (
        scored.group_by("movement_id")
        .agg(
            pl.col("movement_name").first(),
            pl.len().alias("scored"),
            (pl.col("severity") != "EXPECTED").sum().alias("anomalies"),
            pl.col("deviation_pct").quantile(0.95).alias("p95_deviation_pct"),
            pl.col("deviation_pct").max().alias("worst_deviation_pct"),
        )
        .filter(pl.col("scored") >= min_scored)
        .with_columns(
            (pl.col("anomalies") / pl.col("scored") * 100).round(2).alias("anomaly_rate_pct"),
            pl.col("scored")
            .map_elements(Confidence.from_sample, return_dtype=pl.Utf8)
            .alias("confidence"),
        )
        .sort("anomaly_rate_pct", descending=True)
    )
