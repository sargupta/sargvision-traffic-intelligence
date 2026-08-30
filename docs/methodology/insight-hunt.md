# Insight Hunt — What the Data Actually Supports

`run: 30 August 2026` · **Purpose: find the strongest demonstrable insight before writing
another line of product theory.** Several candidates were tested. Most failed.

---

## What was tested, and what survived

| Candidate | Result | Verdict |
|---|---|---|
| **Directional asymmetry** (tidal flow, A→B ≠ B→A) | Median TTI gap **0.021**, p90 0.061, max 0.190 across 459 directional pairs | ❌ **No signal.** Nobody acts on a 0.02 difference |
| **Day-of-week structure** | Mon–Fri TTI **1.115–1.124** — statistically interchangeable. Sat 1.102, Sun 1.044 | ❌ **Only "Sunday is quieter."** An officer knows that |
| **Trend across 5 months** | TTI 1.089–1.117, no direction | ❌ **Flat** |
| **Journey reliability** (p90/p50 buffer) | Range **1.07 → 1.39**. Worst journey needs 39% extra time, best 7% | ⚠️ **Real but modest** |
| **No morning peak** | 07:00 *below* free-flow; plateau 09:00–22:00; worst hour **19:00** | ✅ **Holds. Contradicts the standard assumption** |
| **Weekend mirrors weekday** | Same 13-hour plateau, same 19:00 peak, lower amplitude | ✅ **Holds. Trade city, not commuter city** |
| **Free-flow is only 19.66 km/h** | Congestion is the minority of the speed gap | ✅ **Holds, and is the largest finding** |

---

## 🔴 The finding that challenges our own product hypothesis

The deciding question was: **is Siliguri's traffic predictable or volatile?** If variation
is mostly *within* a day, the product is **planning**. If it is mostly *across* days, the
product is **anomaly detection**.

```
total variance in weekday TTI          0.03100
explained by HOUR OF DAY               0.01224   (39.5%)
residual (day-to-day + unit + noise)   0.01876   (60.5%)
```

**Day-to-day movement is very small.** The same hour on different weekdays barely moves:

| Hour | Median TTI | SD across days | CV |
|---|---|---|---|
| 08:00 | 1.020 | 0.021 | **0.020** |
| 12:00 | 1.240 | 0.043 | 0.034 |
| 17:00 | 1.216 | 0.046 | 0.037 |
| 19:00 | 1.264 | 0.045 | 0.036 |

And genuinely unusual days are rare:

| Threshold | Days |
|---|---|
| beyond 1.5 SD | 9 of 103 (8.7%) |
| **beyond 2.0 SD** | **5 of 103 (4.9%)** |
| beyond 2.5 SD | 2 of 103 (1.9%) |

**Median weekday TTI 1.123, SD across days 0.026 — a coefficient of variation of 0.024.**

> ### In 2019, Siliguri's traffic was highly regular.
> **The same hour on different weekdays looks nearly identical, and about 95% of days are
> unremarkable.**

---

## What that means for the product

**It weakens the anomaly-detection hypothesis.** If an officer's Tuesday is nearly
identical to their Monday, *"what is unusual today?"* has little to find. Our own alert
calibration already hinted at this: we had to drop to **+30% deviation** to reach 5 alerts
a day, and gating at +60% produced roughly **one**.

**It strengthens a different hypothesis.** Traffic this regular is **plannable**. The
valuable question is not *"what is unusual today?"* but:

> **"Where does this city reliably lose time, how much, and what would change it?"**

That is a **planning and diagnosis** product, not an operations product. It answers *"what
should I change this quarter?"* rather than *"what do I do this morning?"*

### The uncomfortable implication

**The officer's question — *"what will I do differently tomorrow morning?"* — may be the
wrong test for this data**, because on 95% of mornings the honest answer is *"nothing, this
morning is like every other."*

**That is not a failure of the product. It is a finding about the city** — and it should
change what we build and what we claim, rather than being smoothed over.

---

## Three caveats that limit this conclusion

1. **City-median aggregation hides local events.** "Days look alike city-wide" does **not**
   mean nothing happened anywhere. A crash on one corridor barely moves a city median. The
   unit-level picture is a different question, partly answered by the alert calibration.
2. **The dataset samples trips; it does not monitor continuously.** A 30-minute incident
   affects few sampled trips and may be structurally under-represented. **Absence of
   detected anomalies is partly an artefact of the sampling design.**
3. **This is 2019.** Siliguri has grown. Volatility may be higher now, and this cannot
   establish that it is not.

**Caveat 2 is the strongest counter-argument to our own conclusion**, and it should be
stated whenever this finding is presented.

---

## What to demonstrate

On the evidence, the demo's strongest material is **structural, not operational**:

1. **Siliguri has no morning peak.** 07:00 runs below free-flow; the plateau is 09:00–22:00;
   the worst hour is **19:00**. Three independent local sources agree congestion begins at
   9–10am, not 8.
2. **The weekend looks like the weekday.** Same plateau, same peak hour, lower amplitude.
   **This is a trade city, not a commuter city** — and that is a genuinely different
   planning posture.
3. **Free-flow is 19.66 km/h.** Even with no traffic at all, Siliguri moves at under
   20 km/h. Congestion is the minority of the problem.
4. **Journey reliability varies 7% to 39%.** Some movements need a third more time budget
   than their median — usable for public communication and for scheduling.

**Then ask the Commissionerate whether any of it is useful.** Their reaction determines
whether there is a product. That is the test, and it has not been run.
