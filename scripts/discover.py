"""Run the Intelligence Discovery Engine and publish the insight store.

Run:  PYTHONPATH=. .venv/bin/python scripts/discover.py

This is the job that makes the application's front page change. It is
deterministic: the same tables produce the same findings in the same order, so
a finding appearing or disappearing means the data or the thresholds moved, not
that the engine felt differently today.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from packages.intelligence.engine import discover, feed_summary

CURATED = Path("data/curated")
OUT_STORE = CURATED / "insights.json"
OUT_WEB = Path("apps/web/public/data/insights.json")


def main() -> None:
    tables = {
        name: pl.read_parquet(CURATED / f"{name}.parquet")
        for name in (
            "observations", "movements", "reliability", "baselines", "anomalies", "zones"
        )
    }
    manifest = json.loads((CURATED / "manifest.json").read_text())
    scored_total = manifest["row_counts"]["observations"]

    run = discover(
        obs=tables["observations"],
        movements=tables["movements"],
        reliability=tables["reliability"],
        baselines=tables["baselines"],
        anomalies=tables["anomalies"],
        zones=tables["zones"],
        scored_total=scored_total,
    )

    payload = {
        "run": {
            "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "summary": feed_summary(run),
            "proposed": run.proposed,
            "surfaced": run.surfaced,
            "rejected_fdr": run.rejected_fdr,
            "fdr_q": run.fdr_q,
            "data_window": manifest["window"],
            "mode": "historical replay",
            "is_live": False,
        },
        "findings": [f.as_dict() for f in run.findings],
        "edges": run.edges,
    }

    OUT_STORE.write_text(json.dumps(payload, indent=1))
    OUT_WEB.parent.mkdir(parents=True, exist_ok=True)
    OUT_WEB.write_text(json.dumps(payload, separators=(",", ":")))

    print(feed_summary(run))
    print(
        f"proposed {run.proposed} · surfaced {run.surfaced} · "
        f"rejected by FDR {run.rejected_fdr} (q = {run.fdr_q})\n"
    )
    for f in run.findings:
        print(
            f"  [{f.priority:.3f}] {f.confidence.value:<8} {f.kind.value:<13} {f.title}"
        )
    print(f"\n{len(run.edges)} graph edges")


if __name__ == "__main__":
    main()
