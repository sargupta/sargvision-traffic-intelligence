"""Baseline engine — what is normal for this movement, this day type, this hour.

Medians and percentile bands, nothing cleverer. An officer and a reviewer can
both follow the arithmetic, which matters more here than sophistication: a
baseline nobody can check is a baseline nobody should act on.

A baseline is published only where the evidence supports one. Bins below the
publishing floor are dropped rather than smoothed, so silence in the output
means "we do not know", never "nothing to report".

**Baselines are built on pace, not on journey time.** A zone-to-zone movement
pools journeys of very different lengths — inside one movement-hour bin the
longest trip is commonly five to ten times the shortest, and distance correlates
about 0.8 with travel time. A baseline on raw seconds would therefore measure
how far someone went far more than how delayed they were, and every long trip
would score as an anomaly. Pace (seconds per kilometre) removes trip length from
the comparison, which is the only way "this journey took longer than it should"
can mean congestion rather than geography.

Journey times are still reported, but they are derived: an expected time is the
movement's expected pace multiplied by *this* journey's distance.
"""

from __future__ import annotations

import polars as pl

from packages.domain.canonical import Confidence

# Per BIN (movement x day_type x hour), not per movement. A bin holds a fraction
# of its movement's observations; applying a movement-level threshold to bins
# silently empties the table.
MIN_SAMPLES = 30

KEYS = ("movement_id", "day_type", "hour")


def with_pace(obs: pl.DataFrame) -> pl.DataFrame:
    """Seconds per kilometre — the length-independent measure of how a trip went."""
    return obs.with_columns(
        (pl.col("traffic_seconds") / (pl.col("distance_m") / 1000)).alias("pace"),
        (pl.col("freeflow_seconds") / (pl.col("distance_m") / 1000)).alias("freeflow_pace"),
    )


def build(obs: pl.DataFrame, min_samples: int = MIN_SAMPLES) -> pl.DataFrame:
    """Pace baselines per movement, day type and hour."""
    return (
        with_pace(obs)
        .group_by(list(KEYS))
        .agg(
            pl.len().alias("sample_size"),
            pl.col("pace").median().alias("median_pace"),
            pl.col("pace").quantile(0.10).alias("p10_pace"),
            pl.col("pace").quantile(0.25).alias("p25_pace"),
            pl.col("pace").quantile(0.75).alias("p75_pace"),
            pl.col("pace").quantile(0.90).alias("p90_pace"),
            pl.col("freeflow_pace").median().alias("median_freeflow_pace"),
            pl.col("traffic_seconds").median().alias("median_seconds"),
            pl.col("traffic_seconds").quantile(0.25).alias("p25_seconds"),
            pl.col("traffic_seconds").quantile(0.75).alias("p75_seconds"),
            pl.col("traffic_seconds").quantile(0.90).alias("p90_seconds"),
            pl.col("delay_seconds").median().alias("median_delay_seconds"),
            pl.col("delay_pct").median().alias("median_delay_pct"),
            pl.col("tti").median().alias("median_tti"),
            pl.col("speed_kmh").median().alias("median_speed_kmh"),
            pl.col("distance_m").median().alias("median_distance_m"),
            pl.col("movement_name").first(),
            pl.col("origin_zone").first(),
            pl.col("dest_zone").first(),
        )
        .filter(pl.col("sample_size") >= min_samples)
        .with_columns(
            pl.col("sample_size")
            .map_elements(Confidence.from_sample, return_dtype=pl.Utf8)
            .alias("confidence"),
            # The band to plan against, for a journey of this bin's typical
            # length. Stated in minutes because that is the unit an officer
            # thinks in; derived from pace so it is comparable across bins.
            (pl.col("p25_pace") * pl.col("median_distance_m") / 1000 / 60)
            .round(1)
            .alias("normal_low_minutes"),
            (pl.col("p75_pace") * pl.col("median_distance_m") / 1000 / 60)
            .round(1)
            .alias("normal_high_minutes"),
            (pl.col("median_pace") * pl.col("median_distance_m") / 1000 / 60)
            .round(1)
            .alias("expected_minutes"),
        )
        .sort(["movement_id", "day_type", "hour"])
    )


def movement_totals(obs: pl.DataFrame, min_samples: int = 100) -> pl.DataFrame:
    """One row per movement, pooled across hours and day types."""
    return (
        obs.group_by("movement_id")
        .agg(
            pl.col("movement_name").first(),
            pl.col("origin_zone").first(),
            pl.col("origin_zone_name").first(),
            pl.col("dest_zone").first(),
            pl.col("dest_zone_name").first(),
            pl.len().alias("sample_size"),
            pl.col("traffic_seconds").median().alias("median_seconds"),
            pl.col("traffic_seconds").quantile(0.90).alias("p90_seconds"),
            pl.col("delay_seconds").median().alias("median_delay_seconds"),
            pl.col("delay_pct").median().alias("median_delay_pct"),
            pl.col("tti").median().alias("median_tti"),
            pl.col("speed_kmh").median().alias("median_speed_kmh"),
            pl.col("distance_m").median().alias("median_distance_m"),
            pl.col("origin_lat").mean().alias("origin_lat"),
            pl.col("origin_lon").mean().alias("origin_lon"),
            pl.col("dest_lat").mean().alias("dest_lat"),
            pl.col("dest_lon").mean().alias("dest_lon"),
        )
        .filter(pl.col("sample_size") >= min_samples)
        .with_columns(
            pl.col("sample_size")
            .map_elements(Confidence.from_sample, return_dtype=pl.Utf8)
            .alias("confidence"),
            (pl.col("median_seconds") / 60).round(1).alias("expected_minutes"),
        )
        .sort("sample_size", descending=True)
    )
