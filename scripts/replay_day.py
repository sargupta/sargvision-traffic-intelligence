"""Drive the intelligence loop over one historical day and report what it found.

Run:  PYTHONPATH=. .venv/bin/python scripts/replay_day.py [YYYYMMDD]

This is how the real-time system is exercised without a live feed: the replay
provider emits the day's observations as though they were arriving now, and the
engine cannot tell the difference. That is the point — it proves the loop, and
it keeps the demonstration reproducible.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import polars as pl

from packages.providers.live import ReplayProvider
from packages.realtime.engine import IntelligenceLoop, load_baselines
from packages.registry.movements import load_registry

DATE = int(sys.argv[1]) if len(sys.argv) > 1 else 20190722
TICK = timedelta(minutes=5)


def main() -> None:
    obs = pl.read_parquet("data/curated/observations.parquet")
    baselines = load_baselines(pl.read_parquet("data/curated/baselines.parquet"))
    registry = load_registry()

    provider = ReplayProvider(obs, replay_date=DATE)
    loop = IntelligenceLoop(registry=registry, provider=provider, baselines=baselines)

    day = datetime.strptime(str(DATE), "%Y%m%d")
    now = day.replace(hour=5)
    end = day.replace(hour=23)

    print(
        f"replaying {day:%A %d %B %Y} · {len(registry.active)} movements · {TICK.seconds // 60}-minute ticks\n"
    )

    while now <= end:
        result = loop.tick(now)
        if result["new"]:
            print(f"{now:%H:%M}  {result['headline']}")
            for fid in result["new"]:
                entry = loop.feed[fid]
                f = entry.finding
                print(f"        [{f.priority:.2f}] {f.severity:<8} {f.signal.value:<13} {f.title}")
                print(f"                 {f.claim}")
        now += TICK

    print("\n── end of day ─────────────────────────────────────────────")
    active = loop.feed_entries()
    resolved = [e for e in loop.feed.values() if e.state == "RESOLVED"]
    print(
        f"ticks {loop.ticks} · findings raised {len(loop.feed)} · still active {len(active)} · resolved {len(resolved)}"
    )
    print(f"\nfinal state: {loop.city.headline()}")
    print(f"counts: {loop.city.counts()}")


if __name__ == "__main__":
    main()
