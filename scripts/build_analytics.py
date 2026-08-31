"""Phase 1 — build every analytics table from the prepared observations.

    prepared parquet
          ↓  zone model (data-driven clustering, gazetteer naming)
          ↓  mobility observations (published schema, quality-gated)
          ↓  baselines · reliability · patterns · anomalies
    data/curated/*.parquet  +  siliguri.duckdb  +  manifest.json

Run:  .venv/bin/python scripts/build_analytics.py

Nothing here is stochastic at run time — the clustering seed is fixed — so two
runs on the same input produce byte-identical tables.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import polars as pl

from packages.analytics import anomalies as anom
from packages.analytics import baselines as base
from packages.analytics import patterns as pat
from packages.analytics import reliability as rel
from packages.mobility.observations import build_observations, validate
from packages.zones.model import (
    MAX_NAME_DISTANCE_M,
    MIN_ZONE_ENDPOINTS,
    assign,
    build_zones,
)

SOURCE = Path("data/processed/siliguri_observations.parquet")
CURATED = Path("data/curated")
DB = CURATED / "siliguri.duckdb"


def main() -> None:
    CURATED.mkdir(parents=True, exist_ok=True)
    raw = pl.read_parquet(SOURCE)
    print(f"source                 {raw.height:>9,} rows")

    # ── Zones ────────────────────────────────────────────────────────────────
    model = build_zones(raw)
    zoned = assign(raw, model)
    print(f"zones                  {model.k:>9} (chosen from {len(model.search)} candidates)")
    for z in model.zones.iter_rows(named=True):
        print(
            f"  {z['zone_id']}  {z['zone_name']:<18} "
            f"named at {z['name_distance_m']:>5,} m  ·  {z['endpoint_observations']:>7,} endpoints"
        )

    # ── Mobility Data Layer ──────────────────────────────────────────────────
    obs = build_observations(zoned)
    gate = validate(obs)
    print(f"observations           {obs.height:>9,} rows")
    failures = {k: v for k, v in gate.items() if k not in ("rows", "trips") and v}
    if failures:
        raise SystemExit(f"quality gate failed: {failures}")
    print(f"quality gate           {'PASS':>9}  ({gate['trips']:,} distinct trips)")

    # ── Analytics ────────────────────────────────────────────────────────────
    baselines = base.build(obs)
    movements = base.movement_totals(obs)
    reliability = rel.score(obs)
    hourly_all = pat.by_hour(obs).with_columns(pl.lit("ALL").alias("day_type"))
    hourly_wd = pat.by_hour(obs, "WEEKDAY").with_columns(pl.lit("WEEKDAY").alias("day_type"))
    hourly_we = pat.by_hour(obs, "WEEKEND").with_columns(pl.lit("WEEKEND").alias("day_type"))
    hourly = pl.concat([hourly_all, hourly_wd, hourly_we])
    daily = pat.by_day_of_week(obs)
    peaks = pat.peak_windows(obs)
    week = pat.weekday_weekend(obs)
    scored = anom.score(obs, baselines)
    found = anom.anomalies_only(scored)
    per_movement = anom.by_movement(scored)

    print(f"baselines              {baselines.height:>9,} bins")
    print(f"movements              {movements.height:>9,} of {model.k * model.k} possible")
    print(f"reliability            {reliability.height:>9,} movements scored")
    print(f"scored observations    {scored.height:>9,} ({scored.height / obs.height:.1%} of total)")
    print(
        f"historical anomalies   {found.height:>9,} ({found.height / max(scored.height, 1):.1%} of scored)"
    )

    tables: dict[str, pl.DataFrame] = {
        "zones": model.zones,
        "observations": obs,
        "baselines": baselines,
        "movements": movements,
        "reliability": reliability,
        "patterns_hourly": hourly,
        "patterns_daily": daily,
        "patterns_weekly": week,
        "peak_windows": peaks,
        "anomalies": found,
        "anomaly_rates": per_movement,
    }

    for name, frame in tables.items():
        frame.write_parquet(CURATED / f"{name}.parquet")

    # A single queryable database, so the API and the copilot's tools read the
    # same tables through the same engine rather than re-deriving anything.
    DB.unlink(missing_ok=True)
    con = duckdb.connect(str(DB))
    for name, frame in tables.items():
        con.register(f"_{name}", frame.to_arrow())
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM _{name}")
    con.close()

    manifest = {
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": str(SOURCE),
        "mode": "historical replay",
        "is_live": False,
        "window": {"start": "2019-06-13", "end": "2019-11-05", "days": int(raw["date"].n_unique())},
        "canonical_sample": "101,418 valid primary-route observations",
        "config": {
            "zone_min_endpoints": MIN_ZONE_ENDPOINTS,
            "zone_max_name_distance_m": MAX_NAME_DISTANCE_M,
            "baseline_min_samples": base.MIN_SAMPLES,
            "reliability_min_samples": rel.MIN_SAMPLES,
            "reliability_bands": {
                "reliable": rel.SILIGURI.reliable,
                "moderate": rel.SILIGURI.moderate,
            },
            "anomaly_thresholds": {
                "moderate": anom.SILIGURI.moderate,
                "high": anom.SILIGURI.high,
                "critical": anom.SILIGURI.critical,
            },
            "congested_tti": pat.CONGESTED_TTI,
        },
        "zone_search": model.search,
        "quality_gate": gate,
        "row_counts": {name: frame.height for name, frame in tables.items()},
    }
    (CURATED / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\nwrote {len(tables)} tables + manifest to {CURATED}/  and {DB}")


if __name__ == "__main__":
    main()
