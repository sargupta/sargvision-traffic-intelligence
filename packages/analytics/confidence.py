"""Baseline confidence and hierarchical fallback — Blueprint §12.

    unit (1 km) baseline
          ↓ insufficient sample
    unit (2 km) fallback
          ↓ insufficient sample
    city / no baseline

The spike made this mandatory rather than optional: at the 1 km unit only 9.5% of
spatial units carry usable evidence, so a system that published a baseline everywhere
would be fabricating precision across two thirds of the city.
"""
from __future__ import annotations

import polars as pl

from packages.domain.canonical import BaselineSource, Confidence

MIN_PUBLISH = 30      # below this, no baseline is published at all
PREFERRED = 100       # at or above this, the preferred unit is used


def annotate(baselines: pl.DataFrame, source: str = BaselineSource.UNIT_1KM) -> pl.DataFrame:
    """Attach confidence and baseline source to every bin."""
    return baselines.with_columns(
        pl.col("sample_size")
        .map_elements(Confidence.from_sample, return_dtype=pl.Utf8)
        .alias("confidence"),
        pl.lit(source).alias("baseline_source"),
    ).filter(pl.col("sample_size") >= MIN_PUBLISH)


def resolve(preferred: pl.DataFrame, fallback: pl.DataFrame) -> pl.DataFrame:
    """Use the preferred baseline where it is strong enough; otherwise the fallback.

    The chosen level is retained in `baseline_source` so the UI can show it.
    """
    strong = preferred.filter(pl.col("sample_size") >= PREFERRED)
    weak_keys = preferred.filter(pl.col("sample_size") < PREFERRED).select(
        ["unit_id", "day_type", "hour"]
    )
    substituted = fallback.join(weak_keys, on=["unit_id", "day_type", "hour"], how="inner")
    return pl.concat([strong, substituted], how="diagonal_relaxed")
