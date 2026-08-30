"""The Intelligence Discovery Engine.

    observations
         ↓  detectors — each asks one question of the data
    candidate findings
         ↓  evidence validation — is this statistically meaningful?
    surviving findings
         ↓  prioritiser — impact x confidence x novelty x recurrence
    intelligence findings

Every detector here is deterministic. No language model participates in
discovering anything, deciding whether it is real, or scoring how much it
matters. The model's job begins afterwards, and is only ever to put a validated
finding into readable English.

**Multiple comparisons are controlled.** A run tests dozens of hypotheses across
25 movements. At p < 0.05 uncorrected, a couple of false findings per run is
the expected outcome, not bad luck — and a feed that surfaces noise as
discovery is worse than no feed. Benjamini-Hochberg is applied across every
test in the run before anything is published.
"""

from __future__ import annotations

import polars as pl
from scipy import stats

from packages.intelligence.finding import Confidence, Evidence, Finding, Kind, View

FDR_Q = 0.05          # false discovery rate the run is held to
MIN_GROUP = 60        # smallest sample either side of a comparison
EVENING = (17, 18, 19, 20, 21)


# ── evidence validation ──────────────────────────────────────────────────────

def benjamini_hochberg(p_values: list[float], q: float = FDR_Q) -> list[bool]:
    """Which p-values survive at false discovery rate q. Order is preserved."""
    if not p_values:
        return []
    m = len(p_values)
    order = sorted(range(m), key=lambda i: p_values[i])
    survive = [False] * m
    cutoff_rank = -1
    for rank, idx in enumerate(order, start=1):
        if p_values[idx] <= q * rank / m:
            cutoff_rank = rank
    for rank, idx in enumerate(order, start=1):
        if rank <= cutoff_rank:
            survive[idx] = True
    return survive


def _confidence(n: int, p: float | None) -> Confidence:
    """Confidence is sample size and strength of evidence together.

    A tiny p-value on 80 observations is not the same claim as a tiny p-value
    on 8,000, and the feed must not present them as if it were.
    """
    if p is None:
        return Confidence.MODERATE if n >= 300 else Confidence.LOW
    if n >= 1000 and p < 0.001:
        return Confidence.HIGH
    if n >= 300 and p < 0.01:
        return Confidence.MODERATE
    return Confidence.LOW


def _rank_biserial(u: float, n1: int, n2: int) -> float:
    """Effect size for Mann-Whitney U: 0 means the distributions coincide."""
    return abs(2 * u / (n1 * n2) - 1)


def _pace(obs: pl.DataFrame) -> pl.DataFrame:
    return obs.with_columns(
        (pl.col("traffic_seconds") / (pl.col("distance_m") / 1000)).alias("pace")
    )


# ── detectors ────────────────────────────────────────────────────────────────

def detect_unreliable(reliability: pl.DataFrame, obs: pl.DataFrame) -> list[dict]:
    """Movements you cannot plan around, relative to the rest of the city."""
    city_median = float(reliability["buffer_pct"].median())
    total = obs.height
    out: list[dict] = []

    for row in reliability.sort("buffer_pct", descending=True).head(6).iter_rows(named=True):
        if row["buffer_pct"] <= city_median:
            continue
        excess = row["buffer_pct"] - city_median
        share = row["sample_size"] / total
        out.append(
            {
                "p": None,
                "n": row["sample_size"],
                "build": lambda r=row, e=excess, s=share: Finding(
                    id=f"REL_{r['movement_id']}",
                    kind=Kind.RELIABILITY,
                    title=f"{r['movement_name']} is hard to plan around",
                    claim=(
                        f"A journey on {r['movement_name']} needs {r['buffer_pct']:.0f}% "
                        f"more time than typical to arrive on time nine trips in ten — "
                        f"{e:.0f} points above the city median of {city_median:.0f}%."
                    ),
                    interpretation=(
                        f"Budgeting the median {r['median_minutes']:.0f} minutes fails one "
                        f"trip in ten by {r['extra_minutes']:.0f} minutes or more. A movement "
                        "that is usually fine and occasionally bad is an operations problem, "
                        "not a capacity one: something intermittent is happening on it."
                    ),
                    limitation=(
                        "Buffer is computed across all hours and both day types pooled. It "
                        "says the movement is unpredictable, not when. The zone pair is not "
                        "a road, and this is 2019 data."
                    ),
                    evidence=Evidence(
                        observations=r["sample_size"],
                        test="percentile spread of pace (P90 vs P50), seconds per km",
                        statistic=round(r["buffer_pct"], 2),
                        p_value=None,
                        effect=round(e, 2),
                        effect_unit="points above city median buffer",
                        comparison=f"city median buffer {city_median:.1f}%",
                    ),
                    view=View(
                        layout="map+detail",
                        focus_movements=[r["movement_id"]],
                        encode="reliability",
                    ),
                    confidence=_confidence(r["sample_size"], None),
                    impact=min(1.0, s * 8),
                    novelty=min(1.0, e / 15),
                    recurrence=1.0,
                    movements=[r["movement_id"]],
                ),
            }
        )
    return out


def detect_divergence(reliability: pl.DataFrame) -> list[dict]:
    """Movements whose reliability rank is nothing like their speed rank.

    This is the finding a live traffic map structurally cannot produce, because
    it needs the distribution of many days rather than the state of one.
    """
    ranked = reliability.with_columns(
        pl.col("buffer_pct").rank(descending=True).alias("rank_unreliable"),
        pl.col("median_speed_kmh").rank().alias("rank_slow"),
    ).with_columns((pl.col("rank_slow") - pl.col("rank_unreliable")).abs().alias("gap"))

    out: list[dict] = []
    for row in ranked.sort("gap", descending=True).head(3).iter_rows(named=True):
        if row["gap"] < ranked.height / 3:
            continue
        fast_but_unreliable = row["rank_slow"] > row["rank_unreliable"]
        out.append(
            {
                "p": None,
                "n": row["sample_size"],
                "build": lambda r=row, fbu=fast_but_unreliable: Finding(
                    id=f"DIV_{r['movement_id']}",
                    kind=Kind.DIVERGENCE,
                    title=(
                        f"{r['movement_name']} is "
                        + ("quick but undependable" if fbu else "slow but dependable")
                    ),
                    claim=(
                        f"{r['movement_name']} ranks {int(r['rank_unreliable'])} of "
                        f"{ranked.height} for unreliability but {int(r['rank_slow'])} of "
                        f"{ranked.height} for slowness — a gap of {int(r['gap'])} places."
                    ),
                    interpretation=(
                        "Average speed would put this movement in the wrong queue. "
                        + (
                            "It moves well most of the time, which is exactly why the bad "
                            "days are not planned for."
                            if fbu
                            else "It is consistently slow, which at least makes it plannable: "
                            "the fix here is capacity, not operations."
                        )
                    ),
                    limitation=(
                        "Ranks are within these 25 movements only, and both measures pool "
                        "all hours. A gap in rank is not a statistical test."
                    ),
                    evidence=Evidence(
                        observations=r["sample_size"],
                        test="rank comparison, buffer against median speed",
                        statistic=float(r["gap"]),
                        p_value=None,
                        effect=float(r["gap"]),
                        effect_unit="places between the two ranks",
                        comparison=f"{ranked.height} movements ranked on both measures",
                    ),
                    view=View(
                        layout="compare",
                        focus_movements=[r["movement_id"]],
                        encode="divergence",
                        series=["buffer_pct", "median_speed_kmh"],
                    ),
                    confidence=_confidence(r["sample_size"], None),
                    impact=0.6,
                    novelty=min(1.0, float(r["gap"]) / ranked.height),
                    recurrence=1.0,
                    movements=[r["movement_id"]],
                ),
            }
        )
    return out


def detect_asymmetry(obs: pl.DataFrame, movements: pl.DataFrame) -> list[dict]:
    """One direction of a movement behaving unlike the other.

    Operationally this is among the most useful things the data can say: it
    localises a problem to a direction, which narrows what could cause it.
    """
    paced = _pace(obs)
    seen: set[frozenset[str]] = set()
    out: list[dict] = []

    for row in movements.iter_rows(named=True):
        o, d = row["origin_zone"], row["dest_zone"]
        if o == d:
            continue
        pair = frozenset({o, d})
        if pair in seen:
            continue
        seen.add(pair)

        fwd = paced.filter((pl.col("origin_zone") == o) & (pl.col("dest_zone") == d))["pace"]
        rev = paced.filter((pl.col("origin_zone") == d) & (pl.col("dest_zone") == o))["pace"]
        if fwd.len() < MIN_GROUP or rev.len() < MIN_GROUP:
            continue

        a, b = fwd.to_numpy(), rev.to_numpy()
        u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
        med_a, med_b = float(fwd.median()), float(rev.median())
        slower_first = med_a > med_b
        pct = abs(med_a - med_b) / min(med_a, med_b) * 100
        if pct < 8:
            continue

        names = {row["origin_zone_name"]: o, row["dest_zone_name"]: d}
        o_name, d_name = row["origin_zone_name"], row["dest_zone_name"]
        slow_name = o_name if slower_first else d_name
        fast_name = d_name if slower_first else o_name
        n_total = int(fwd.len() + rev.len())

        out.append(
            {
                "p": float(p),
                "n": n_total,
                "build": lambda r=row, p=float(p), u=float(u), pct=pct, sn=slow_name,
                fn=fast_name, na=int(fwd.len()), nb=int(rev.len()), nt=n_total,
                ma=med_a, mb=med_b, nm=names: Finding(
                    id=f"ASY_{'_'.join(sorted(nm.values()))}",
                    kind=Kind.ASYMMETRY,
                    title=f"{sn} → {fn} is the slower direction",
                    claim=(
                        f"Travelling {sn} to {fn} is {pct:.0f}% slower per kilometre than "
                        f"the return leg, across {nt:,} observations."
                    ),
                    interpretation=(
                        "A difference this size between two directions of the same pair is "
                        "not geometry — the distance is the same both ways. It points at "
                        "something directional: a junction that only binds one way, "
                        "kerbside activity on one side, or a turn that has to cross traffic."
                    ),
                    limitation=(
                        "Zone pairs are not roads, and the two directions may not use the "
                        "same route at all. The test shows the distributions differ; it "
                        "cannot say why, and this data carries no vehicle types or turns."
                    ),
                    evidence=Evidence(
                        observations=nt,
                        test="Mann-Whitney U on pace, two-sided",
                        statistic=round(u, 1),
                        p_value=p,
                        effect=round(pct, 2),
                        effect_unit="% difference in median pace",
                        comparison=f"{na:,} observations one way against {nb:,} the other",
                    ),
                    view=View(
                        layout="compare",
                        focus_movements=[f"{v}__{w}" for v in nm.values() for w in nm.values() if v != w],
                        focus_zones=list(nm.values()),
                        encode="asymmetry",
                        series=["pace"],
                    ),
                    confidence=_confidence(nt, p),
                    impact=min(1.0, nt / 8000),
                    novelty=min(1.0, pct / 25),
                    recurrence=1.0,
                    movements=[f"{v}__{w}" for v in nm.values() for w in nm.values() if v != w],
                    zones=list(nm.values()),
                ),
            }
        )
    return out


def detect_period(obs: pl.DataFrame, movements: pl.DataFrame) -> list[dict]:
    """Movements whose evening behaves unlike the rest of their own day."""
    paced = _pace(obs)
    out: list[dict] = []

    for row in movements.iter_rows(named=True):
        mid = row["movement_id"]
        sub = paced.filter(pl.col("movement_id") == mid)
        evening = sub.filter(pl.col("hour").is_in(EVENING))["pace"]
        rest = sub.filter(~pl.col("hour").is_in(EVENING))["pace"]
        if evening.len() < MIN_GROUP or rest.len() < MIN_GROUP:
            continue

        a, b = evening.to_numpy(), rest.to_numpy()
        u, p = stats.mannwhitneyu(a, b, alternative="greater")
        med_e, med_r = float(evening.median()), float(rest.median())
        pct = (med_e - med_r) / med_r * 100
        if pct < 8:
            continue

        n_total = int(evening.len() + rest.len())
        out.append(
            {
                "p": float(p),
                "n": n_total,
                "build": lambda r=row, p=float(p), u=float(u), pct=pct,
                ne=int(evening.len()), nt=n_total: Finding(
                    id=f"EVE_{r['movement_id']}",
                    kind=Kind.PERIOD,
                    title=f"{r['movement_name']} loses its evening",
                    claim=(
                        f"Between 17:00 and 21:00, {r['movement_name']} runs {pct:.0f}% "
                        f"slower per kilometre than it does across the rest of the day."
                    ),
                    interpretation=(
                        "The evening is when this movement stops resembling itself. If staff "
                        "or signal timing are allocated on a whole-day average, this is the "
                        "window that average is hiding."
                    ),
                    limitation=(
                        "The evening window is defined as 17:00-21:00 by us, not derived. "
                        "The comparison is against the same movement's other hours, so it "
                        "says nothing about how this movement compares to the city."
                    ),
                    evidence=Evidence(
                        observations=nt,
                        test="Mann-Whitney U on pace, evening greater than rest of day",
                        statistic=round(u, 1),
                        p_value=p,
                        effect=round(pct, 2),
                        effect_unit="% slower per km in the evening",
                        comparison=f"{ne:,} evening observations against {nt - ne:,} others",
                    ),
                    view=View(
                        layout="timeline",
                        focus_movements=[r["movement_id"]],
                        focus_hours=list(EVENING),
                        encode="delay",
                        series=["median_tti"],
                    ),
                    confidence=_confidence(nt, p),
                    impact=min(1.0, nt / 8000),
                    novelty=min(1.0, pct / 25),
                    recurrence=0.9,
                    movements=[r["movement_id"]],
                ),
            }
        )
    return out


def detect_day_type(obs: pl.DataFrame, movements: pl.DataFrame) -> list[dict]:
    """Movements where the weekend genuinely is a different city — or is not."""
    paced = _pace(obs)
    out: list[dict] = []

    for row in movements.iter_rows(named=True):
        mid = row["movement_id"]
        sub = paced.filter(pl.col("movement_id") == mid)
        wd = sub.filter(pl.col("day_type") == "WEEKDAY")["pace"]
        we = sub.filter(pl.col("day_type") == "WEEKEND")["pace"]
        if wd.len() < MIN_GROUP or we.len() < MIN_GROUP:
            continue

        u, p = stats.mannwhitneyu(wd.to_numpy(), we.to_numpy(), alternative="two-sided")
        med_wd, med_we = float(wd.median()), float(we.median())
        pct = (med_wd - med_we) / med_we * 100
        if abs(pct) < 6:
            continue

        n_total = int(wd.len() + we.len())
        out.append(
            {
                "p": float(p),
                "n": n_total,
                "build": lambda r=row, p=float(p), u=float(u), pct=pct,
                nw=int(wd.len()), ne=int(we.len()), nt=n_total: Finding(
                    id=f"DAY_{r['movement_id']}",
                    kind=Kind.DAY_TYPE,
                    title=(
                        f"{r['movement_name']} "
                        + ("empties at the weekend" if pct > 0 else "is worse at the weekend")
                    ),
                    claim=(
                        f"{r['movement_name']} runs {abs(pct):.0f}% "
                        f"{'slower' if pct > 0 else 'faster'} per kilometre on weekdays "
                        f"than at weekends."
                    ),
                    interpretation=(
                        "A movement that clears at the weekend is carrying commuting or "
                        "business travel, and demand-side measures can reach it. One that "
                        "does not is carrying something that does not observe a weekend."
                        if pct > 0
                        else "This movement is busier at the weekend than on weekdays, which "
                        "points at retail, market or leisure travel rather than commuting."
                    ),
                    limitation=(
                        "One 2019 window covering monsoon into early winter. Festival weeks "
                        "are inside it and are not separated out, and a public holiday is "
                        "counted as whatever weekday it fell on."
                    ),
                    evidence=Evidence(
                        observations=nt,
                        test="Mann-Whitney U on pace, weekday against weekend",
                        statistic=round(u, 1),
                        p_value=p,
                        effect=round(abs(pct), 2),
                        effect_unit="% difference in median pace",
                        comparison=f"{nw:,} weekday observations against {ne:,} weekend",
                    ),
                    view=View(
                        layout="compare",
                        focus_movements=[r["movement_id"]],
                        day_types=["WEEKDAY", "WEEKEND"],
                        encode="delay",
                        series=["weekday_tti", "weekend_tti"],
                    ),
                    confidence=_confidence(nt, p),
                    impact=min(1.0, nt / 8000),
                    novelty=min(1.0, abs(pct) / 20),
                    recurrence=0.95,
                    movements=[r["movement_id"]],
                ),
            }
        )
    return out


def detect_recurrence(anomalies: pl.DataFrame, scored_total: int, obs: pl.DataFrame) -> list[dict]:
    """Movement-hours where departures from normal keep recurring.

    A single bad evening is weather. The same hour on the same movement
    departing from its own baseline again and again is a pattern.
    """
    if anomalies.height == 0:
        return []

    base_rate = anomalies.height / max(scored_total, 1)
    per_bin = (
        obs.group_by("movement_id", "hour").len().rename({"len": "scored"})
    )
    hits = (
        anomalies.group_by("movement_id", "hour")
        .agg(pl.len().alias("hits"), pl.col("movement_name").first())
        .join(per_bin, on=["movement_id", "hour"], how="inner")
        .filter((pl.col("scored") >= 150) & (pl.col("hits") >= 12))
    )

    out: list[dict] = []
    for row in hits.iter_rows(named=True):
        test = stats.binomtest(row["hits"], row["scored"], base_rate, alternative="greater")
        rate = row["hits"] / row["scored"]
        if rate < base_rate * 2:
            continue
        out.append(
            {
                "p": float(test.pvalue),
                "n": int(row["scored"]),
                "build": lambda r=row, p=float(test.pvalue), rate=rate, br=base_rate: Finding(
                    id=f"REC_{r['movement_id']}_{r['hour']:02d}",
                    kind=Kind.RECURRENCE,
                    title=f"{r['movement_name']} keeps breaking at {r['hour']:02d}:00",
                    claim=(
                        f"At {r['hour']:02d}:00, {r['movement_name']} departs from its own "
                        f"baseline on {rate * 100:.0f}% of observations — against "
                        f"{br * 100:.1f}% across the city."
                    ),
                    interpretation=(
                        "This is not one bad day. The same movement at the same hour keeps "
                        "leaving its own normal range, which is the signature of a recurring "
                        "cause rather than an incident — and recurring causes can be found."
                    ),
                    limitation=(
                        "An anomaly here means a departure from this movement's own 2019 "
                        "baseline at this hour. It is not an incident record, and no cause "
                        "is attached because none is in the data."
                    ),
                    evidence=Evidence(
                        observations=int(r["scored"]),
                        test="binomial test against the city-wide anomaly rate",
                        statistic=int(r["hits"]),
                        p_value=p,
                        effect=round(rate / br, 2),
                        effect_unit="x the city anomaly rate",
                        comparison=f"{r['hits']} departures in {r['scored']:,} observations",
                    ),
                    view=View(
                        layout="timeline",
                        focus_movements=[r["movement_id"]],
                        focus_hours=[int(r["hour"])],
                        encode="anomaly",
                        series=["median_tti"],
                    ),
                    confidence=_confidence(int(r["scored"]), float(test.pvalue)),
                    impact=min(1.0, int(r["scored"]) / 3000),
                    novelty=min(1.0, (rate / br - 1) / 3),
                    recurrence=min(1.0, rate * 6),
                    movements=[r["movement_id"]],
                ),
            }
        )
    return out


def detect_evidence_gaps(
    baselines: pl.DataFrame, movements: pl.DataFrame, zones: pl.DataFrame
) -> list[dict]:
    """Where the system cannot see. Absence of evidence, stated as a finding.

    This is deliberately in the same feed as everything else. A gap in coverage
    is a fact about the city's instrumentation and it competes for attention on
    the same terms as a pattern.
    """
    possible = zones.height * zones.height * 24 * 2
    covered = baselines.height
    thin = movements.filter(pl.col("confidence").is_in(["LOW", "INSUFFICIENT"]))

    out: list[dict] = [
        {
            "p": None,
            "n": covered,
            "build": lambda: Finding(
                id="GAP_COVERAGE",
                kind=Kind.EVIDENCE_GAP,
                title="Most hours of most movements have no publishable baseline",
                claim=(
                    f"{covered:,} of {possible:,} possible movement-hour-daytype bins carry "
                    f"the 30 observations we publish at — {covered / possible * 100:.0f}%."
                ),
                interpretation=(
                    "Everywhere else, the honest output is silence. The engine does not "
                    "estimate into the gaps, because a baseline computed on a dozen "
                    "journeys is not something anyone should deploy staff against."
                ),
                limitation=(
                    "Raising coverage means lowering the floor, and a lower floor means "
                    "less defensible figures. 30 is a judgement, and it is the reason this "
                    "number is low."
                ),
                evidence=Evidence(
                    observations=covered,
                    test="count of bins clearing the publishing floor",
                    statistic=covered,
                    p_value=None,
                    effect=round(covered / possible * 100, 2),
                    effect_unit="% of possible bins covered",
                    comparison=f"{possible:,} possible bins across {zones.height} zones",
                ),
                view=View(layout="coverage", encode="coverage"),
                confidence=Confidence.HIGH,
                impact=1.0,
                novelty=0.5,
                recurrence=1.0,
            ),
        }
    ]

    if thin.height:
        out.append(
            {
                "p": None,
                "n": int(thin["sample_size"].sum()),
                "build": lambda t=thin: Finding(
                    id="GAP_THIN_MOVEMENTS",
                    kind=Kind.EVIDENCE_GAP,
                    title=f"{t.height} movements rest on thin evidence",
                    claim=(
                        f"{t.height} of the city's movements carry fewer than 300 "
                        "observations, so anything said about them is provisional."
                    ),
                    interpretation=(
                        "These movements appear in the interface with their confidence "
                        "shown, and they should not carry a decision on their own."
                    ),
                    limitation="Low confidence is not evidence of absence of a problem.",
                    evidence=Evidence(
                        observations=int(t["sample_size"].sum()),
                        test="sample size against the confidence bands",
                        statistic=t.height,
                        p_value=None,
                        effect=float(t.height),
                        effect_unit="movements below MODERATE confidence",
                        comparison="300 observations for MODERATE, 1,000 for HIGH",
                    ),
                    view=View(
                        layout="coverage",
                        focus_movements=t["movement_id"].to_list(),
                        encode="coverage",
                    ),
                    confidence=Confidence.HIGH,
                    impact=0.4,
                    novelty=0.4,
                    recurrence=1.0,
                    movements=t["movement_id"].to_list(),
                ),
            }
        )
    return out
