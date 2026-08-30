"""Baseline engine — what is normal for this corridor, this day type, this hour.

Rolling median plus percentile bands. Deliberately explainable: an officer and a
reviewer can both follow it. No LLM, no black box.
"""
from __future__ import annotations

import polars as pl

MIN_SAMPLES = 12


def prepare(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        pl.when(pl.col("dayofweek").cast(pl.Int64) >= 5)
        .then(pl.lit("WEEKEND"))
        .otherwise(pl.lit("WEEKDAY"))
        .alias("day_type"),
        (pl.col("querytime_min") // 60).cast(pl.Int64).alias("hour"),
        (pl.col("traffic_seconds") - pl.col("freeflow_seconds")).alias("delay_seconds"),
        (pl.col("traffic_seconds") / pl.col("freeflow_seconds")).alias("tti"),
        ((pl.col("distance_m") / 1000) / (pl.col("traffic_seconds") / 3600)).alias("speed_kmh"),
    )


def build(df: pl.DataFrame, min_samples: int = MIN_SAMPLES) -> pl.DataFrame:
    return (
        df.group_by(["corridor_id", "day_type", "hour"])
        .agg(
            pl.len().alias("sample_size"),
            pl.col("traffic_seconds").median().alias("median_seconds"),
            pl.col("traffic_seconds").quantile(0.25).alias("p25_seconds"),
            pl.col("traffic_seconds").quantile(0.75).alias("p75_seconds"),
            pl.col("traffic_seconds").quantile(0.90).alias("p90_seconds"),
        )
        .filter(pl.col("sample_size") >= min_samples)
    )
