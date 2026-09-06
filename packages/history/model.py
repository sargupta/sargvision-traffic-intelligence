"""The corridor's own history — what "typical for this hour" finally means here.

Until now the system had two time layers: the live board, and a seven-year-old
city-wide study. Neither could answer "is THIS corridor unusual for a Tuesday
6pm?", because nothing remembered how this corridor itself behaves. This module
is that memory. It folds every live index reading into a small set of running
aggregates and forgets the reading itself.

WHAT IT STORES, AND WHY THAT IS COMPLIANT
-----------------------------------------
The Google Maps Platform terms let us cache coordinates, not traffic content,
and the incident store already refuses to write a single corridor reading for
exactly that reason. This store holds a strict superset of nothing-reconstructable:

  * per (corridor, weekday, hour) — a *histogram* of our own congestion index
    (a dimensionless ratio we computed), plus count/mean/min/max. A histogram of
    ratios is irreversible: no individual Google travel-time can be recovered
    from it. This is our derived statistic, not Google's content.
  * per (corridor, date) — a daily rollup (mean, peak, hours congested). A coarse
    aggregate, bounded to a recent window; again nothing raw survives.

No timestamped sequence of readings is ever kept. The baseline is unbounded
because it is pure aggregate; the daily rollup is capped so even the coarse
history honours a retention limit.

WHAT IT REFUSES TO PRETEND
--------------------------
The forecast is the corridor's own typical shape, nudged by its recent trend —
a transparent baseline, not a model that claims to know the future. It is
labelled as such everywhere it surfaces. "Analytics discovers, humans decide."
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Index histogram: fixed bins over the range the ratio actually occupies. Below
# 1.0 is "faster than typical", 1.0 is typical, and jams sit at 1.5–3.0. Bins of
# 0.1 give percentiles precise enough to act on while staying tiny to store.
BIN_WIDTH = 0.1
BIN_COUNT = 40  # 0.0 → 4.0; anything above lands in the top bin
DAILY_RETENTION_DAYS = 120  # the coarse rollup's cache limit
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _bin(index: float) -> int:
    # The 1e-9 nudge defeats float representation error: 1.4 / 0.1 is
    # 13.999999999999998, which would floor into the wrong bin and let a reported
    # percentile fall below the observed minimum.
    return max(0, min(BIN_COUNT - 1, int(index / BIN_WIDTH + 1e-9)))


@dataclass
class Bucket:
    """One (weekday, hour) cell for one corridor: the distribution of our index
    there, as counters that can only ever be added to."""

    n: int = 0
    total: float = 0.0
    total_sq: float = 0.0
    min_index: float | None = None
    max_index: float | None = None
    hist: list[int] = field(default_factory=lambda: [0] * BIN_COUNT)
    congested_n: int = 0
    last_seen: str | None = None  # ISO date only — no time, nothing reconstructable

    def fold(self, index: float, congested: bool, when: datetime) -> None:
        self.n += 1
        self.total += index
        self.total_sq += index * index
        self.min_index = index if self.min_index is None else min(self.min_index, index)
        self.max_index = index if self.max_index is None else max(self.max_index, index)
        self.hist[_bin(index)] += 1
        if congested:
            self.congested_n += 1
        self.last_seen = when.date().isoformat()

    @property
    def mean(self) -> float | None:
        return self.total / self.n if self.n else None

    @property
    def std(self) -> float | None:
        if self.n < 2:
            return None
        var = max(0.0, (self.total_sq - self.total * self.total / self.n) / (self.n - 1))
        return math.sqrt(var)

    def percentile(self, p: float) -> float | None:
        """Linear-interpolated percentile from the histogram. p in [0, 100]."""
        if self.n == 0:
            return None
        target = p / 100 * self.n
        cum = 0
        for b, count in enumerate(self.hist):
            if count == 0:
                continue
            if cum + count >= target:
                # interpolate within the bin
                frac = (target - cum) / count
                return round((b + frac) * BIN_WIDTH, 3)
            cum += count
        return round(BIN_COUNT * BIN_WIDTH, 3)

    def summary(self) -> dict:
        return {
            "n": self.n,
            "mean": round(self.mean, 3) if self.mean is not None else None,
            "p50": self.percentile(50),
            "p85": self.percentile(85),
            "p95": self.percentile(95),
            "min": round(self.min_index, 3) if self.min_index is not None else None,
            "max": round(self.max_index, 3) if self.max_index is not None else None,
            "congested_share": round(self.congested_n / self.n, 3) if self.n else None,
            "last_seen": self.last_seen,
        }


@dataclass
class DailyRollup:
    n: int = 0
    total: float = 0.0
    peak: float | None = None
    congested_n: int = 0

    def fold(self, index: float, congested: bool) -> None:
        self.n += 1
        self.total += index
        self.peak = index if self.peak is None else max(self.peak, index)
        if congested:
            self.congested_n += 1

    def summary(self) -> dict:
        return {
            "n": self.n,
            "mean": round(self.total / self.n, 3) if self.n else None,
            "peak": round(self.peak, 3) if self.peak is not None else None,
            "hours_congested": self.congested_n,
        }


@dataclass
class CorridorHistory:
    corridor_id: str
    name: str = ""
    # buckets keyed by (weekday 0-6, hour 0-23)
    buckets: dict[tuple[int, int], Bucket] = field(default_factory=dict)
    days: dict[str, DailyRollup] = field(default_factory=dict)  # ISO date → rollup

    def fold(self, when: datetime, index: float, congested: bool) -> None:
        key = (when.weekday(), when.hour)
        self.buckets.setdefault(key, Bucket()).fold(index, congested, when)
        self.days.setdefault(when.date().isoformat(), DailyRollup()).fold(index, congested)
        self._evict_old_days(when)

    def _evict_old_days(self, when: datetime) -> None:
        cutoff = (when.date() - timedelta(days=DAILY_RETENTION_DAYS)).isoformat()
        stale = [d for d in self.days if d < cutoff]
        for d in stale:
            del self.days[d]

    def baseline(self, weekday: int, hour: int) -> dict | None:
        b = self.buckets.get((weekday, hour))
        return b.summary() if b and b.n else None

    def day_profile(self, weekday: int) -> list[dict]:
        """This corridor's own typical shape across the 24 hours of a weekday —
        the per-corridor answer the 2019 city-wide curve could only approximate."""
        out = []
        for hour in range(24):
            b = self.buckets.get((weekday, hour))
            out.append(
                {
                    "hour": hour,
                    "p50": b.percentile(50) if b and b.n else None,
                    "p85": b.percentile(85) if b and b.n else None,
                    "n": b.n if b else 0,
                }
            )
        return out

    def observations(self) -> int:
        return sum(b.n for b in self.buckets.values())


def _std_from_summary(summary: dict) -> float | None:
    # p85 ≈ mean + 1.04·std for a normal; a rough spread when we only kept summary
    p85, p50 = summary.get("p85"), summary.get("p50")
    if p85 is None or p50 is None:
        return None
    return max(0.001, (p85 - p50) / 1.04)


@dataclass
class ObservationHistory:
    """The whole board's memory: one CorridorHistory per corridor, plus the read
    methods the copilot and the API ask their historical questions through."""

    corridors: dict[str, CorridorHistory] = field(default_factory=dict)

    # ── writing ──────────────────────────────────────────────────────────────
    def fold(self, corridor_id: str, name: str, when: datetime, index: float, congested: bool):
        ch = self.corridors.get(corridor_id)
        if ch is None:
            ch = self.corridors[corridor_id] = CorridorHistory(corridor_id, name)
        if name and not ch.name:
            ch.name = name
        ch.fold(when, index, congested)

    # ── reading ──────────────────────────────────────────────────────────────
    def now_vs_baseline(self, corridor_id: str, when: datetime, live_index: float) -> dict:
        """Is this corridor unusual for this hour, judged against ITSELF? The
        question the system could never answer before it had a memory."""
        ch = self.corridors.get(corridor_id)
        base = ch.baseline(when.weekday(), when.hour) if ch else None
        out: dict = {
            "corridor_id": corridor_id,
            "name": ch.name if ch else "",
            "when": {"weekday": DAY_NAMES[when.weekday()], "hour": when.hour},
            "live_index": round(live_index, 3),
            "baseline": base,
        }
        if not base or base["n"] < 5:
            out["verdict"] = "not enough history"
            out["confidence"] = "low"
            out["caveat"] = (
                f"Only {base['n'] if base else 0} readings for this corridor at this weekday "
                "and hour so far — the baseline is still forming. It sharpens as the system "
                "keeps observing."
            )
            return out
        std = _std_from_summary(base) or 0.001
        z = (live_index - (base["p50"] or 0)) / std
        if z >= 1.5:
            verdict = "worse than typical"
        elif z <= -1.5:
            verdict = "better than typical"
        else:
            verdict = "typical for the hour"
        out.update(
            {
                "verdict": verdict,
                "z_score": round(z, 2),
                "confidence": "good" if base["n"] >= 20 else "forming",
                "caveat": (
                    "Compared against this corridor's own readings for this weekday and hour "
                    f"({base['n']} of them). It says whether now is unusual, not why."
                ),
            }
        )
        return out

    def day_profile(self, corridor_id: str, weekday: int) -> dict | None:
        ch = self.corridors.get(corridor_id)
        if ch is None:
            return None
        hours = ch.day_profile(weekday)
        observed = [h for h in hours if h["n"]]
        peak = sorted(observed, key=lambda h: -(h["p85"] or 0))[:3] if observed else []
        return {
            "corridor_id": corridor_id,
            "name": ch.name,
            "weekday": DAY_NAMES[weekday],
            "hours": hours,
            "worst_hours": [{"hour": h["hour"], "p85": h["p85"]} for h in peak],
            "observations": ch.observations(),
            "caveat": (
                "This corridor's own typical shape, learned live — not the 2019 city study. "
                "Hours with no bar have not been observed yet."
            ),
        }

    def trend(self, corridor_id: str, days: int = 21) -> dict | None:
        """Is this corridor drifting worse or better? Recent daily means against
        the earlier half of the window. Descriptive, not predictive."""
        ch = self.corridors.get(corridor_id)
        if ch is None or not ch.days:
            return None
        dates = sorted(ch.days)[-days:]
        series = [{"date": d, **ch.days[d].summary()} for d in dates]
        means = [(d, ch.days[d].total / ch.days[d].n) for d in dates if ch.days[d].n]
        drift = None
        direction = "flat"
        if len(means) >= 6:
            half = len(means) // 2
            early = sum(m for _, m in means[:half]) / half
            late = sum(m for _, m in means[half:]) / (len(means) - half)
            drift = round(late - early, 3)
            if drift >= 0.05:
                direction = "worsening"
            elif drift <= -0.05:
                direction = "easing"
        return {
            "corridor_id": corridor_id,
            "name": ch.name,
            "days_observed": len(dates),
            "series": series,
            "drift": drift,
            "direction": direction,
            "caveat": (
                "A description of what the daily averages did over the window, not a claim "
                "about a cause. Days with heavier traffic naturally pull the average up."
            ),
        }

    def timeline(self, corridor_id: str, days: int = 30) -> dict | None:
        ch = self.corridors.get(corridor_id)
        if ch is None:
            return None
        dates = sorted(ch.days)[-days:]
        return {
            "corridor_id": corridor_id,
            "name": ch.name,
            "days": [{"date": d, **ch.days[d].summary()} for d in dates],
        }

    def forecast(self, corridor_id: str, when: datetime, hours: int = 3) -> dict | None:
        """The corridor's own typical index for the next few hours, nudged by its
        recent trend. A transparent baseline projection — explicitly NOT a model
        that claims to predict the future, and it says so."""
        ch = self.corridors.get(corridor_id)
        if ch is None:
            return None
        tr = self.trend(corridor_id)
        nudge = 0.0
        if tr and tr["drift"] is not None:
            nudge = max(-0.15, min(0.15, tr["drift"]))  # cap the drift's influence
        steps = []
        for h in range(1, hours + 1):
            t = when + timedelta(hours=h)
            base = ch.baseline(t.weekday(), t.hour)
            if not base or base["n"] < 5:
                steps.append(
                    {
                        "hour": t.hour,
                        "weekday": DAY_NAMES[t.weekday()],
                        "expected": None,
                        "n": base["n"] if base else 0,
                    }
                )
                continue
            expected = round((base["p50"] or 0) + nudge, 3)
            steps.append(
                {
                    "hour": t.hour,
                    "weekday": DAY_NAMES[t.weekday()],
                    "expected": expected,
                    "band": [base["p50"], base["p85"]],
                    "n": base["n"],
                }
            )
        return {
            "corridor_id": corridor_id,
            "name": ch.name,
            "from_hour": when.hour,
            "trend_nudge": round(nudge, 3),
            "steps": steps,
            "caveat": (
                "This is the corridor's own median for each upcoming hour, adjusted a little "
                "for its recent drift. It is a baseline expectation, not a prediction — an "
                "incident, weather or an event will override it entirely."
            ),
        }

    def coverage(self) -> dict:
        return {
            "corridors_with_history": sum(1 for c in self.corridors.values() if c.observations()),
            "total_observations": sum(c.observations() for c in self.corridors.values()),
            "note": (
                "Derived statistics only — a histogram of our own congestion index per "
                "weekday-hour, and coarse daily aggregates. No raw travel-time reading is "
                "stored; nothing here can reconstruct Google's data."
            ),
        }
