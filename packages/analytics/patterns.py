"""Pattern engine — the recurring structure in how Siliguri moves.

Time-of-day, day-type and movement-level patterns. All deterministic: these are
group-bys and medians, and every figure can be recomputed by hand from the
observation table.
"""

from __future__ import annotations

import polars as pl

MIN_BIN = 30

# A congested hour is one whose median journey takes at least a tenth longer
# than free-flow. The cut is ours and is stated wherever it is used.
CONGESTED_TTI = 1.10


def by_hour(obs: pl.DataFrame, day_type: str | None = None) -> pl.DataFrame:
    frame = obs.filter(pl.col("day_type") == day_type) if day_type else obs
    return (
        frame.group_by("hour")
        .agg(
            pl.len().alias("sample_size"),
            pl.col("tti").median().alias("median_tti"),
            pl.col("speed_kmh").median().alias("median_speed_kmh"),
            pl.col("delay_pct").median().alias("median_delay_pct"),
            pl.col("traffic_seconds").median().alias("median_seconds"),
        )
        .filter(pl.col("sample_size") >= MIN_BIN)
        .sort("hour")
        .with_columns((pl.col("median_tti") >= CONGESTED_TTI).alias("congested"))
    )


def by_day_of_week(obs: pl.DataFrame) -> pl.DataFrame:
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    return (
        obs.group_by("day_of_week")
        .agg(
            pl.len().alias("sample_size"),
            pl.col("tti").median().alias("median_tti"),
            pl.col("speed_kmh").median().alias("median_speed_kmh"),
            pl.col("delay_pct").median().alias("median_delay_pct"),
        )
        .sort("day_of_week")
        .with_columns(
            pl.col("day_of_week")
            .map_elements(lambda i: names[int(i)], return_dtype=pl.Utf8)
            .alias("day_name")
        )
    )


def movement_by_hour(obs: pl.DataFrame, movement_id: str) -> pl.DataFrame:
    return by_hour(obs.filter(pl.col("movement_id") == movement_id))


def peak_windows(obs: pl.DataFrame) -> pl.DataFrame:
    """For every movement, the hour it is worst and the hour it is best."""
    binned = (
        obs.group_by("movement_id", "hour")
        .agg(
            pl.col("movement_name").first(),
            pl.len().alias("sample_size"),
            pl.col("tti").median().alias("median_tti"),
            pl.col("traffic_seconds").median().alias("median_seconds"),
        )
        .filter(pl.col("sample_size") >= MIN_BIN)
    )
    worst = (
        binned.sort("median_tti", descending=True)
        .group_by("movement_id")
        .first()
        .select(
            "movement_id",
            "movement_name",
            pl.col("hour").alias("peak_hour"),
            pl.col("median_tti").alias("peak_tti"),
            (pl.col("median_seconds") / 60).round(1).alias("peak_minutes"),
        )
    )
    best = (
        binned.sort("median_tti")
        .group_by("movement_id")
        .first()
        .select(
            "movement_id",
            pl.col("hour").alias("quietest_hour"),
            pl.col("median_tti").alias("quietest_tti"),
            (pl.col("median_seconds") / 60).round(1).alias("quietest_minutes"),
        )
    )
    return worst.join(best, on="movement_id", how="inner").sort("peak_tti", descending=True)


def rankings(movements: pl.DataFrame, reliability: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """The four lists the dashboard and the report both draw on."""
    return {
        "most_delayed": movements.sort("median_delay_pct", descending=True).head(10),
        "slowest": movements.sort("median_speed_kmh").head(10),
        "most_unreliable": reliability.sort("buffer_pct", descending=True).head(10),
        "most_stable": reliability.sort("buffer_pct").head(10),
    }


def weekday_weekend(obs: pl.DataFrame) -> pl.DataFrame:
    """The two day types side by side, hour for hour."""
    wd = by_hour(obs, "WEEKDAY").select(
        "hour",
        pl.col("median_tti").alias("weekday_tti"),
        pl.col("median_speed_kmh").alias("weekday_speed"),
        pl.col("sample_size").alias("weekday_n"),
    )
    we = by_hour(obs, "WEEKEND").select(
        "hour",
        pl.col("median_tti").alias("weekend_tti"),
        pl.col("median_speed_kmh").alias("weekend_speed"),
        pl.col("sample_size").alias("weekend_n"),
    )
    return wd.join(we, on="hour", how="full", coalesce=True).sort("hour")
