"""Reliability engine — which movements you can plan around, and which you cannot.

Reliability is not slowness. A movement that is always slow is predictable and
can be planned for; a movement that is usually fine and occasionally terrible
cannot. On the Siliguri sample the two rank-correlate weakly, so this engine
produces information that median speed does not already carry.

The measure is the **buffer**: the extra time over a typical journey you must
allow to arrive on time nine trips in ten.

    buffer = (P90 travel time - P50 travel time) / P50 travel time

Computed on travel time per kilometre so movements of different length compare.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl

from packages.domain.canonical import Confidence


@dataclass(frozen=True)
class Bands:
    """Where the lines sit between the three reliability classes.

    Configuration calibrated against the Siliguri 2019 sample, not constants.
    A different city, or a different data source, must recalibrate: the bands
    describe what counts as dependable *here*.
    """

    reliable: float = 15.0        # under this much buffer, plan against the median
    moderate: float = 30.0        # under this, allow a margin
    # at or above `moderate`, the median is not a usable planning figure

    def classify(self, buffer_pct: float) -> str:
        if buffer_pct < self.reliable:
            return "HIGHLY_RELIABLE"
        if buffer_pct < self.moderate:
            return "MODERATELY_RELIABLE"
        return "UNPREDICTABLE"


SILIGURI = Bands()

MIN_SAMPLES = 200


def score(
    obs: pl.DataFrame, bands: Bands = SILIGURI, min_samples: int = MIN_SAMPLES
) -> pl.DataFrame:
    scored = (
        obs.with_columns(
            (pl.col("traffic_seconds") / (pl.col("distance_m") / 1000)).alias("_spk")
        )
        .group_by("movement_id")
        .agg(
            pl.col("movement_name").first(),
            pl.col("origin_zone").first(),
            pl.col("origin_zone_name").first(),
            pl.col("dest_zone").first(),
            pl.col("dest_zone_name").first(),
            pl.len().alias("sample_size"),
            pl.col("_spk").quantile(0.50).alias("p50_seconds_per_km"),
            pl.col("_spk").quantile(0.90).alias("p90_seconds_per_km"),
            pl.col("traffic_seconds").median().alias("median_seconds"),
            pl.col("traffic_seconds").quantile(0.90).alias("p90_seconds"),
            pl.col("speed_kmh").median().alias("median_speed_kmh"),
            pl.col("distance_m").median().alias("median_distance_m"),
        )
        .filter(pl.col("sample_size") >= min_samples)
        .with_columns(
            (
                (pl.col("p90_seconds_per_km") - pl.col("p50_seconds_per_km"))
                / pl.col("p50_seconds_per_km")
                * 100
            ).alias("buffer_pct")
        )
        .with_columns(
            pl.col("buffer_pct")
            .map_elements(bands.classify, return_dtype=pl.Utf8)
            .alias("reliability"),
            pl.col("sample_size")
            .map_elements(Confidence.from_sample, return_dtype=pl.Utf8)
            .alias("confidence"),
            (pl.col("median_seconds") / 60).round(1).alias("median_minutes"),
            (pl.col("p90_seconds") / 60).round(1).alias("p90_minutes"),
        )
        .sort("buffer_pct", descending=True)
    )
    return scored.with_columns(
        (pl.col("p90_minutes") - pl.col("median_minutes")).round(1).alias("extra_minutes")
    )


def worst_windows(baselines: pl.DataFrame, top: int = 10) -> pl.DataFrame:
    """The movement-hours with the widest spread between the normal-range ends.

    A wide P25-P75 band at a specific hour is where a movement stops being
    plannable, and it is more actionable than a movement-level average because
    it names the hour.
    """
    return (
        baselines.with_columns(
            (
                (pl.col("p75_seconds") - pl.col("p25_seconds")) / pl.col("median_seconds") * 100
            ).alias("spread_pct")
        )
        .sort("spread_pct", descending=True)
        .head(top)
    )
