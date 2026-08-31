"""Export the four surviving findings, plus map geometry, as a single JSON payload.

Every number the artefact renders is produced here. Nothing is typed into the
frontend by hand — if a figure appears on screen, it was computed in this file.

Run:  .venv/bin/python scripts/export_findings.py
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

SOURCE = Path("data/processed/siliguri_observations.parquet")
OUT = Path("apps/web/public/data/findings.json")

GRID_1KM = 0.009
GRID_2KM = 0.018
WEEKEND = (5, 6)  # dayofweek follows datetime.date.weekday(): Monday = 0

# A speed a mid-sized Indian city might reasonably aim at. Used only as a
# reference line, never presented as a target anyone has adopted.
REFERENCE_SPEED_KMH = 30.0

MIN_BIN = 30  # matches packages/analytics/confidence.MIN_PUBLISH


def cell_centroid(cell: str, grid: float) -> tuple[float, float]:
    """`2968_9825` -> the centre of that grid cell, in degrees."""
    lat_idx, lon_idx = (int(part) for part in cell.split("_"))
    return (lat_idx * grid + grid / 2, lon_idx * grid + grid / 2)


def band(n: int) -> str:
    if n >= 300:
        return "HIGH"
    if n >= 100:
        return "MODERATE"
    if n >= MIN_BIN:
        return "LOW"
    return "INSUFFICIENT"


def main() -> None:
    df = pl.read_parquet(SOURCE)
    total = df.height

    # ---------------------------------------------------------------- F1
    # Three estimators, because the answer depends on how you aggregate and
    # the honest presentation is the range they span.
    observed_median = df["speed"].median()
    freeflow_median = df["ff_speed"].median()
    observed_agg = (df["dist_m"].sum() / 1000) / (df["traffic_s"].sum() / 3600)
    freeflow_agg = (df["dist_m"].sum() / 1000) / (df["notraffic_s"].sum() / 3600)
    observed_mean = df["speed"].mean()
    freeflow_mean = df["ff_speed"].mean()

    shares = []
    for obs, ff in (
        (observed_median, freeflow_median),
        (observed_agg, freeflow_agg),
        (observed_mean, freeflow_mean),
    ):
        shares.append((ff - obs) / (REFERENCE_SPEED_KMH - obs) * 100)

    f1 = {
        "observed_speed_kmh": round(observed_median, 2),
        "freeflow_speed_kmh": round(freeflow_median, 2),
        "reference_speed_kmh": REFERENCE_SPEED_KMH,
        "congestion_gap_kmh": round(freeflow_median - observed_median, 2),
        "structural_gap_kmh": round(REFERENCE_SPEED_KMH - freeflow_median, 2),
        "congestion_share_pct_low": int(min(shares)),
        "congestion_share_pct_high": int(-(-max(shares) // 1)),
        "estimators": [
            {
                "method": "median of per-observation speeds",
                "observed": round(observed_median, 2),
                "freeflow": round(freeflow_median, 2),
                "share_pct": round(shares[0], 1),
            },
            {
                "method": "distance-weighted aggregate",
                "observed": round(observed_agg, 2),
                "freeflow": round(freeflow_agg, 2),
                "share_pct": round(shares[1], 1),
            },
            {
                "method": "mean of per-observation speeds",
                "observed": round(observed_mean, 2),
                "freeflow": round(freeflow_mean, 2),
                "share_pct": round(shares[2], 1),
            },
        ],
        "n": total,
    }

    # ------------------------------------------------------------- F2 / F3
    def by_hour(frame: pl.DataFrame) -> list[dict]:
        agg = (
            frame.group_by("hour")
            .agg(
                pl.col("tti").median().alias("tti"),
                pl.col("speed").median().alias("speed"),
                pl.len().alias("n"),
            )
            .sort("hour")
            .filter(pl.col("n") >= MIN_BIN)
        )
        return [
            {
                "hour": int(r["hour"]),
                "tti": round(r["tti"], 3),
                "speed": round(r["speed"], 2),
                "n": int(r["n"]),
            }
            for r in agg.iter_rows(named=True)
        ]

    weekday = df.filter(~pl.col("dayofweek").is_in(WEEKEND))
    weekend = df.filter(pl.col("dayofweek").is_in(WEEKEND))
    weekday_hours, weekend_hours = by_hour(weekday), by_hour(weekend)

    def summarise(hours: list[dict]) -> dict:
        peak = max(hours, key=lambda h: h["tti"])
        # A "congested hour" is one at or above 10% over free-flow.
        plateau = [h["hour"] for h in hours if h["tti"] >= 1.10]
        return {
            "peak_hour": peak["hour"],
            "peak_tti": peak["tti"],
            "peak_speed": peak["speed"],
            "plateau_hours": len(plateau),
            "plateau_start": min(plateau) if plateau else None,
            "plateau_end": max(plateau) if plateau else None,
            "n": sum(h["n"] for h in hours),
        }

    f2 = {"hours": weekday_hours, "summary": summarise(weekday_hours), "threshold_tti": 1.10}
    morning = next((h for h in weekday_hours if h["hour"] == 9), None)
    evening = next((h for h in weekday_hours if h["hour"] == 19), None)
    f2["morning_0900"] = morning
    f2["evening_1900"] = evening

    f3 = {
        "weekday": weekday_hours,
        "weekend": weekend_hours,
        "weekday_summary": summarise(weekday_hours),
        "weekend_summary": summarise(weekend_hours),
        "weekend_share_of_weekday_peak": round(
            summarise(weekend_hours)["peak_tti"] / summarise(weekday_hours)["peak_tti"] * 100, 1
        ),
    }

    # ---------------------------------------------------------------- F4
    # Buffer index on travel time per kilometre, so corridors of different
    # length are comparable: how much extra time to budget to arrive on
    # time nine journeys in ten.
    rel = (
        df.with_columns((pl.col("traffic_s") / (pl.col("dist_m") / 1000)).alias("spk"))
        .group_by("unit_id_2km")
        .agg(
            pl.col("spk").quantile(0.5).alias("p50"),
            pl.col("spk").quantile(0.9).alias("p90"),
            pl.col("speed").median().alias("speed"),
            pl.col("tti").median().alias("tti"),
            pl.col("lat_orig").mean().alias("lat_o"),
            pl.col("lon_orig").mean().alias("lon_o"),
            pl.col("lat_dest").mean().alias("lat_d"),
            pl.col("lon_dest").mean().alias("lon_d"),
            pl.len().alias("n"),
        )
        .filter(pl.col("n") >= 200)
        .with_columns(((pl.col("p90") - pl.col("p50")) / pl.col("p50") * 100).alias("buffer_pct"))
        .sort("buffer_pct", descending=True)
    )

    corridors = [
        {
            "id": r["unit_id_2km"],
            "buffer_pct": round(r["buffer_pct"], 1),
            "speed": round(r["speed"], 2),
            "tti": round(r["tti"], 3),
            "n": int(r["n"]),
            "confidence": band(int(r["n"])),
            "origin": [round(r["lat_o"], 5), round(r["lon_o"], 5)],
            "dest": [round(r["lat_d"], 5), round(r["lon_d"], 5)],
        }
        for r in rel.iter_rows(named=True)
    ]

    buffers = [c["buffer_pct"] for c in corridors]

    # Is "unreliable" just another word for "slow"? Rank-correlate the two, and
    # count how many corridors appear on both worst-lists. If the answer is
    # "hardly any", then reliability is information speed does not already carry.
    def spearman(xs: list[float], ys: list[float]) -> float:
        def ranks(v: list[float]) -> list[float]:
            order = sorted(range(len(v)), key=lambda i: v[i])
            out = [0.0] * len(v)
            for pos, i in enumerate(order):
                out[i] = float(pos)
            return out

        rx, ry = ranks(xs), ranks(ys)
        mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry, strict=True))
        den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
        return num / den

    TOP = 15
    worst_buffer = {c["id"] for c in sorted(corridors, key=lambda c: -c["buffer_pct"])[:TOP]}
    slowest = {c["id"] for c in sorted(corridors, key=lambda c: c["speed"])[:TOP]}

    f4 = {
        "rho_buffer_speed": round(spearman(buffers, [c["speed"] for c in corridors]), 3),
        "top_n": TOP,
        "overlap": len(worst_buffer & slowest),
        "corridors": corridors,
        "unit_count": len(corridors),
        "min_sample": 200,
        "worst": round(max(buffers), 1),
        "best": round(min(buffers), 1),
        "median": round(sorted(buffers)[len(buffers) // 2], 1),
        "spread_multiple": round(max(buffers) / min(buffers), 1),
    }

    # ------------------------------------------------------- Coverage layer
    # How well each 1 km cell is observed, counting every journey that starts
    # or ends inside it. This is what makes "we cannot see here" visible.
    cells: dict[str, int] = {}
    for pair, cnt in df.group_by("unit_id").len().iter_rows():
        origin_cell, dest_cell = pair.removeprefix("SIL_").split("__")
        cells[origin_cell] = cells.get(origin_cell, 0) + cnt
        cells[dest_cell] = cells.get(dest_cell, 0) + cnt

    coverage = [
        {"c": [round(lat, 5), round(lon, 5)], "n": n, "b": band(n)}
        for cell, n in sorted(cells.items(), key=lambda kv: -kv[1])
        for lat, lon in [cell_centroid(cell, GRID_1KM)]
    ]
    coverage_summary = {
        b: sum(1 for c in coverage if c["b"] == b)
        for b in ("HIGH", "MODERATE", "LOW", "INSUFFICIENT")
    }

    payload = {
        "meta": {
            "canonical_sample": "101,418 valid primary-route observations",
            "n": total,
            "window_start": "2019-06-13",
            "window_end": "2019-11-05",
            "days": int(df["date"].n_unique()),
            "trips": int(df["tripid"].n_unique()),
            "mode": "historical replay",
            "is_live": False,
            "source": "Akbar, Couture, Duranton & Storeygard, Mobility and Congestion in Urban India, American Economic Review 113(4), 2023. Zenodo 10.5281/zenodo.10499064, CC BY 4.0.",
            "bbox": [26.633, 88.362, 26.792, 88.481],
            "centre": [26.7145, 88.4215],
            "min_bin": MIN_BIN,
        },
        "f1_ceiling": f1,
        "f2_shape": f2,
        "f3_weekend": f3,
        "f4_reliability": f4,
        "coverage": {"cells": coverage, "summary": coverage_summary, "cell_count": len(coverage)},
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1))
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")
    print(json.dumps({k: v for k, v in f1.items() if k != "estimators"}, indent=2))
    print("F2", json.dumps(f2["summary"]))
    print(
        "F3 weekend",
        json.dumps(f3["weekend_summary"]),
        "ratio",
        f3["weekend_share_of_weekday_peak"],
    )
    print("F4", json.dumps({k: v for k, v in f4.items() if k != "corridors"}))
    print("coverage", coverage_summary, "cells", len(coverage))


if __name__ == "__main__":
    main()
