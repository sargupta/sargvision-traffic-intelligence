"""The Mobility Data Layer.

One row per analytical observation: a single origin-to-destination journey
measured at a moment in time, with the travel it actually took and the travel an
empty road would have allowed.

    Raw historical dataset
            ↓  filter to Siliguri (citycode 21405)
            ↓  primary route only (minimum route_rank)
            ↓  quality validation (positive times and distances)
    Mobility observations
            ↓  zone assignment
    Analytics tables

Everything downstream reads this table and nothing reads the raw archive. The
upstream extraction lives in `scripts/prepare_data.py`; this module is the
contract between extraction and analysis.
"""

from __future__ import annotations

import datetime as dt

import polars as pl

# The published fields. Anything not on this list is an implementation detail
# and must not be relied on outside this package.
SCHEMA: tuple[str, ...] = (
    "observation_id",
    "trip_id",
    "observed_at",
    "date",
    "hour",
    "minute_of_day",
    "day_of_week",
    "day_type",
    "origin_lat",
    "origin_lon",
    "dest_lat",
    "dest_lon",
    "origin_zone",
    "origin_zone_name",
    "dest_zone",
    "dest_zone_name",
    "movement_id",
    "movement_name",
    "distance_m",
    "traffic_seconds",
    "freeflow_seconds",
    "delay_seconds",
    "delay_pct",
    "tti",
    "speed_kmh",
    "freeflow_speed_kmh",
    "route_rank",
)

WEEKEND = (5, 6)  # day_of_week follows datetime.date.weekday(): Monday = 0


def _timestamp() -> pl.Expr:
    """Rebuild a real instant from the stored date and minute-of-day.

    Times in the source are local Siliguri wall-clock. They are kept naive
    rather than stamped with a timezone we cannot verify: the source documents
    a local query time, not a UTC offset, and inventing one would put a
    precision on the data that is not there.
    """
    date_str = pl.col("date").cast(pl.Utf8)
    return (
        date_str.str.to_date("%Y%m%d")
        .cast(pl.Datetime("us"))
        .dt.offset_by(pl.format("{}m", pl.col("querytime_min")))
    )


def build_observations(df: pl.DataFrame) -> pl.DataFrame:
    """Project the prepared parquet into the published mobility schema.

    Expects the frame to already carry zone assignments from
    `packages.zones.assign`.
    """
    out = (
        df.with_columns(
            _timestamp().alias("observed_at"),
            pl.when(pl.col("dayofweek").is_in(WEEKEND))
            .then(pl.lit("WEEKEND"))
            .otherwise(pl.lit("WEEKDAY"))
            .alias("day_type"),
        )
        .with_columns(
            pl.int_range(pl.len()).cast(pl.Utf8).str.zfill(6).alias("_seq"),
        )
        .with_columns(
            (pl.lit("OBS_") + pl.col("_seq")).alias("observation_id"),
            pl.col("tripid").cast(pl.Int64).alias("trip_id"),
            pl.col("querytime_min").cast(pl.Int32).alias("minute_of_day"),
            pl.col("dayofweek").cast(pl.Int8).alias("day_of_week"),
            pl.col("lat_orig").cast(pl.Float64).alias("origin_lat"),
            pl.col("lon_orig").cast(pl.Float64).alias("origin_lon"),
            pl.col("lat_dest").cast(pl.Float64).alias("dest_lat"),
            pl.col("lon_dest").cast(pl.Float64).alias("dest_lon"),
            pl.col("dist_m").cast(pl.Float64).alias("distance_m"),
            pl.col("traffic_s").cast(pl.Float64).alias("traffic_seconds"),
            pl.col("notraffic_s").cast(pl.Float64).alias("freeflow_seconds"),
            (pl.col("traffic_s") - pl.col("notraffic_s")).alias("delay_seconds"),
            (
                (pl.col("traffic_s") - pl.col("notraffic_s")) / pl.col("notraffic_s") * 100
            ).alias("delay_pct"),
            (pl.col("traffic_s") / pl.col("notraffic_s")).alias("tti"),
            pl.col("speed").cast(pl.Float64).alias("speed_kmh"),
            pl.col("ff_speed").cast(pl.Float64).alias("freeflow_speed_kmh"),
            pl.col("route_rank").cast(pl.Int8),
            pl.col("hour").cast(pl.Int8),
        )
    )
    return out.select(SCHEMA)


def validate(obs: pl.DataFrame) -> dict[str, int | bool]:
    """Quality gate. Every count here should be zero except the row total."""
    return {
        "rows": obs.height,
        "trips": obs["trip_id"].n_unique(),
        "null_zone": obs.filter(pl.col("origin_zone").is_null()).height,
        "nonpositive_traffic": obs.filter(pl.col("traffic_seconds") <= 0).height,
        "nonpositive_freeflow": obs.filter(pl.col("freeflow_seconds") <= 0).height,
        "nonpositive_distance": obs.filter(pl.col("distance_m") <= 0).height,
        "non_primary_route": obs.filter(pl.col("route_rank") != obs["route_rank"].min()).height,
        "hour_out_of_range": obs.filter(
            (pl.col("hour") < 0) | (pl.col("hour") > 23)
        ).height,
        "duplicate_ids": obs.height - obs["observation_id"].n_unique(),
    }
