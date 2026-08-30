"""Data preparation — join observations to trip geography and assign corridors.

Run once. The provider reads the output; it never touches the raw research files.

    raw .dta files  ->  [this script]  ->  data/processed/*.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

# Two resolutions. The spike (docs/methodology/spatial-feasibility-spike.md) found 1 km
# retains 45% of observations and 2 km retains 91%. We keep both and fall back per bin.
GRID_1KM = 0.009
GRID_2KM = 0.018
SILIGURI_CITYCODE = 21405
OUT = Path("data/processed/siliguri_observations.parquet")


def build(observations: Path, trips_dta: Path) -> pl.DataFrame:
    import pandas as pd

    trips = pd.read_stata(
        trips_dta,
        columns=["tripid", "citycode", "lat_orig", "lon_orig", "lat_dest", "lon_dest"],
    )
    trips = trips[trips.citycode == SILIGURI_CITYCODE]
    t = pl.from_pandas(trips)
    for label, deg in (("unit_id", GRID_1KM), ("unit_id_2km", GRID_2KM)):
        t = t.with_columns(
            pl.concat_str([
                pl.lit("SIL_"),
                (pl.col("lat_orig") / deg).round().cast(pl.Int64), pl.lit("_"),
                (pl.col("lon_orig") / deg).round().cast(pl.Int64), pl.lit("__"),
                (pl.col("lat_dest") / deg).round().cast(pl.Int64), pl.lit("_"),
                (pl.col("lon_dest") / deg).round().cast(pl.Int64),
            ]).alias(label)
        )
    t = t.with_columns(pl.col("unit_id").alias("corridor_id"))  # back-compat
    t = t.select(["tripid", "unit_id", "unit_id_2km", "corridor_id",
                  "lat_orig", "lon_orig", "lat_dest", "lon_dest"])

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
    print(f"wrote {OUT}: {df.height:,} rows, {df['unit_id'].n_unique()} units @1km, {df['unit_id_2km'].n_unique()} @2km")
