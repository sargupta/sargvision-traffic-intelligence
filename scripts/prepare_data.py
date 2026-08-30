"""Data preparation — join observations to trip geography and assign corridors.

Run once. The provider reads the output; it never touches the raw research files.

    raw .dta files  ->  [this script]  ->  data/processed/*.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

GRID_DEG = 0.009   # ~1 km cells. Grid pairs, NOT named roads -- see docs/known-limitations.md
SILIGURI_CITYCODE = 21405
OUT = Path("data/processed/siliguri_observations.parquet")


def build(observations: Path, trips_dta: Path) -> pl.DataFrame:
    import pandas as pd

    trips = pd.read_stata(
        trips_dta,
        columns=["tripid", "citycode", "lat_orig", "lon_orig", "lat_dest", "lon_dest"],
    )
    trips = trips[trips.citycode == SILIGURI_CITYCODE]
    t = pl.from_pandas(trips).with_columns(
        (pl.col("lat_orig") / GRID_DEG).round().cast(pl.Int64).alias("o_lat"),
        (pl.col("lon_orig") / GRID_DEG).round().cast(pl.Int64).alias("o_lon"),
        (pl.col("lat_dest") / GRID_DEG).round().cast(pl.Int64).alias("d_lat"),
        (pl.col("lon_dest") / GRID_DEG).round().cast(pl.Int64).alias("d_lon"),
    ).with_columns(
        pl.concat_str([
            pl.lit("SIL_"), pl.col("o_lat"), pl.lit("_"), pl.col("o_lon"),
            pl.lit("__"), pl.col("d_lat"), pl.lit("_"), pl.col("d_lon"),
        ]).alias("corridor_id")
    ).select(["tripid", "corridor_id", "lat_orig", "lon_orig", "lat_dest", "lon_dest"])

    obs = pl.read_parquet(observations)
    return obs.join(t, on="tripid", how="inner")


if __name__ == "__main__":
    obs = Path(sys.argv[1] if len(sys.argv) > 1 else "data/processed/siliguri_2019_observations.parquet")
    dta = Path(sys.argv[2] if len(sys.argv) > 2 else "data/raw/alltrips_India.dta")
    if not dta.exists():
        sys.exit(f"missing {dta} - see docs/data-provenance.md")
    df = build(obs, dta)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    print(f"wrote {OUT}: {df.height:,} rows, {df['corridor_id'].n_unique()} corridors")
