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

MIN_PUBLISH = 30      # per BIN (unit x day_type x hour). Below this, nothing is published.

# NOTE: 30 is a per-bin floor, not the per-unit figure from the spike. A bin holds a
# fraction of its unit's observations, so applying a unit-level threshold to bins
# silently empties the preferred level -- which is exactly the bug this comment exists
# to prevent recurring.


def annotate(baselines: pl.DataFrame, source: str = BaselineSource.UNIT_1KM) -> pl.DataFrame:
    """Attach confidence and baseline source to every bin."""
    return baselines.with_columns(
        pl.col("sample_size")
        .map_elements(Confidence.from_sample, return_dtype=pl.Utf8)
        .alias("confidence"),
        pl.lit(source).alias("baseline_source"),
    ).filter(pl.col("sample_size") >= MIN_PUBLISH)


def resolve(preferred: pl.DataFrame, fallback: pl.DataFrame) -> pl.DataFrame:
    """Prefer the finer baseline wherever one survives the publish floor.

    `annotate` has already dropped bins below MIN_PUBLISH, so any surviving preferred bin
    is publishable and is used. The fallback fills only the gaps. The level actually used
    is retained in `baseline_source`, so a figure is never silently coarser than it looks.
    """
    if preferred.height == 0:
        return fallback
    return preferred
