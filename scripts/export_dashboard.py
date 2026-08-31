"""Phase 2 — pack the analytics tables into one bundle the dashboard can hold.

The tables are small enough (25 movements, ~790 baseline bins, 24 hours) that
shipping them to the browser beats querying them over a network for every
interaction. The dashboard is therefore instant and works with the API down;
the API exists for the copilot, which needs to run tools server-side.

Raw observations are NOT exported. 101,418 rows have no business in a browser,
and every screen is answerable from the aggregates.

Run:  PYTHONPATH=. .venv/bin/python scripts/export_dashboard.py
"""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl

CURATED = Path("data/curated")
OUT = Path("apps/web/public/data/analytics.json")

# Anomalies are the one table that could grow without bound. The dashboard shows
# the most extreme; the count of everything else is reported so the truncation
# is visible rather than silent.
ANOMALY_LIMIT = 400


def rows(name: str, columns: list[str] | None = None) -> list[dict]:
    frame = pl.read_parquet(CURATED / f"{name}.parquet")
    if columns:
        frame = frame.select(columns)
    return frame.to_dicts()


def main() -> None:
    manifest = json.loads((CURATED / "manifest.json").read_text())

    anomalies = pl.read_parquet(CURATED / "anomalies.parquet")
    top = (
        anomalies.sort("deviation_pct", descending=True)
        .head(ANOMALY_LIMIT)
        .select(
            "observation_id",
            "movement_id",
            "movement_name",
            "observed_at",
            "hour",
            "day_type",
            "expected_minutes",
            "observed_minutes",
            "deviation_pct",
            "severity",
            "baseline_confidence",
            "distance_m",
        )
        .with_columns(
            pl.col("observed_at").dt.strftime("%Y-%m-%d %H:%M").alias("observed_at"),
            pl.col("deviation_pct").round(1),
            pl.col("distance_m").round(0),
        )
    )

    bundle = {
        "meta": {
            **{
                k: manifest[k]
                for k in ("built_at", "mode", "is_live", "window", "canonical_sample")
            },
            "config": manifest["config"],
            "quality_gate": manifest["quality_gate"],
            "row_counts": manifest["row_counts"],
            "zone_search": manifest["zone_search"],
            "source": (
                "Akbar, Couture, Duranton & Storeygard, Mobility and Congestion in Urban "
                "India, American Economic Review 113(4), 2023. "
                "Zenodo 10.5281/zenodo.10499064, CC BY 4.0."
            ),
            "anomaly_limit": ANOMALY_LIMIT,
            "anomalies_total": anomalies.height,
        },
        "zones": rows("zones"),
        "movements": rows("movements"),
        "reliability": rows("reliability"),
        "baselines": rows(
            "baselines",
            [
                "movement_id",
                "movement_name",
                "day_type",
                "hour",
                "sample_size",
                "confidence",
                "expected_minutes",
                "normal_low_minutes",
                "normal_high_minutes",
                "median_pace",
                "median_tti",
                "median_speed_kmh",
                "median_delay_pct",
                "median_distance_m",
            ],
        ),
        "patterns_hourly": rows("patterns_hourly"),
        "patterns_daily": rows("patterns_daily"),
        "patterns_weekly": rows("patterns_weekly"),
        "peak_windows": rows("peak_windows"),
        "anomaly_rates": rows("anomaly_rates"),
        "anomalies": top.to_dicts(),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, separators=(",", ":"), default=str))
    size = OUT.stat().st_size / 1024
    print(f"wrote {OUT}  ({size:.0f} KB)")
    for key, value in bundle.items():
        if isinstance(value, list):
            print(f"  {key:<18} {len(value):>6,} rows")
    print(f"  anomalies shown {ANOMALY_LIMIT} of {anomalies.height:,}")


if __name__ == "__main__":
    main()
