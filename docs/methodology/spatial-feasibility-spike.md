# Spatial Feasibility Spike — Phase 0 Deliverable

`run: 30 August 2026` · Blueprint v2 §35 Phase 0 · **Result: the spatial model must change.**

The blueprint named this the correct first engineering task and the project's next major
uncertainty. It has been run. **Three of its five questions returned answers that
invalidate the proposed segment model.**

---

## Q1 — What geometry exists in the observations?

**Origin and destination points. Nothing else.**

```
lat_orig, lon_orig, lat_dest, lon_dest
```

No route polyline. No waypoint sequence. No path geometry — not in the observation
table, not in the trip index.

> **A travel time in this dataset describes an unknown path between two known points.**

---

## Q2 — Can observations be assigned to segments?

# ❌ No.

Assigning a whole-trip travel time to a road segment requires knowing which segments the
trip used. Without route geometry that path must be **assumed**, and the travel time then
**smears across roughly four assumed 500 m segments** (median trip 2.13 km straight-line).

**The blueprint's 250–750 m direction-aware segment model cannot be built from this data.**
Not with better engineering, not with map-matching — the information is not present.

> **This is the single most important finding of the spike, and it is exactly what a
> feasibility spike is for.** Had we built the spatial layer first as planned, we would
> have produced segment-level numbers that looked rigorous and were assumptions.

**Consequence:** `SEGMENT` is removed from the spatial hierarchy for V1. The atomic
analytical unit is the **origin–destination zone pair**, which is what the observations
actually measure.

```
Blueprint v2                      Corrected for this data
CITY                              CITY
 └─ ZONE                           └─ ZONE
     └─ CORRIDOR                       └─ OD ZONE PAIR   ← atomic unit
         └─ SEGMENT   ❌ not supported
             └─ OBSERVATION                └─ OBSERVATION
```

---

## Q3 — What spatial unit size is appropriate?

Swept empirically. Baseline bins require ≥12 samples; units require ≥100 observations.

| Bin | ~km | Units | ≥300 obs | ≥100 obs | Baseline bins | **% observations retained** |
|---|---|---|---|---|---|---|
| 0.0045° | 0.5 | 8,663 | 0 | 4 | 1 | **0.4%** |
| 0.0090° | **1.0** | 2,621 | 32 | 250 | 767 | **45.1%** |
| 0.0180° | **2.0** | 507 | 92 | 173 | **2,204** | **91.0%** |
| 0.0270° | 3.0 | 180 | 58 | 74 | 1,611 | 97.2% |
| 0.0450° | 5.0 | 56 | 23 | 31 | 735 | 99.3% |

**0.5 km is unusable** — 4 units and a single baseline bin. This alone rules out anything
near the blueprint's 250–750 m proposal.

**2 km is the inflection.** It yields **2,204 baseline bins from 91% of observations**,
against 767 bins from 45% at 1 km.

> ### 🔴 The current pipeline uses 12% of the data
> Configured at 1 km with a ≥300-observation floor, it scores **12,220 of 101,418**
> observations across 32 units. **Moving to 2 km with a ≥100 floor retains 91%.**
> That is not a tuning change; it is most of the dataset.

**Recommendation — hierarchical, per blueprint §12:**

```
1 km unit baseline        ← preferred, spatially actionable
      ↓ insufficient sample
2 km unit baseline        ← fallback, retains 91% coverage
      ↓ insufficient sample
NO BASELINE / LOW CONFIDENCE
```

**Fallback level must be visible in metadata and in the UI.** A user must be able to see
that a figure came from a 2 km fallback rather than a 1 km unit.

---

## Q4 / Q5 — What coverage exists, and how much meets threshold?

Evidence coverage at the 1 km unit — the layer blueprint §25 correctly calls essential:

| Band | Units | % units | Observations | % obs |
|---|---|---|---|---|
| **HIGH** (≥300) | 32 | **1.2%** | 12,220 | 12.0% |
| **MODERATE** (100–299) | 218 | 8.3% | 33,501 | 33.0% |
| **LOW** (30–99) | 639 | 24.4% | 34,491 | 34.0% |
| **INSUFFICIENT** (<30) | **1,732** | **66.1%** | 21,206 | 20.9% |

> **250 of 2,621 spatial units — 9.5% — carry usable evidence. Two thirds have almost
> none.**

**This makes the evidence-coverage overlay non-optional.** A uniformly styled map would
imply city-wide intelligence across a city where 90% of spatial units cannot support a
claim. Blueprint §25 was right to call this the most important new visualisation; the
spike shows it is a correctness requirement, not a nicety.

---

## What changes

| Blueprint v2 said | Spike found | Action |
|---|---|---|
| Segments of 250–750 m, direction-aware | No path geometry exists | **Remove the segment layer from V1** |
| Map-matching approach TBD after inspection | Nothing to map-match | **Delete the map-matching task.** Saves the 1–2 week Phase 2 |
| "Most uncertain technical phase" | Resolved in hours, negatively | **Phase 2 shrinks to zone definition** |
| Corridors named after spatial validation | Named corridors need a path assumption | **Zone pairs are honest; named corridors are a labelling exercise on top** |
| Evidence coverage as a recommended visual | 90% of units lack evidence | **Promote to a correctness requirement** |

### Timeline effect

Blueprint estimated **7–10 weeks**, with Phase 2 (spatial model) at 1–2 weeks and flagged
as the most uncertain. **That phase is now days, not weeks** — there is no map-matching to
build. The uncertainty it was hedging has been resolved, in the direction of less work and
a smaller claim.

---

## The honest position this produces

The product can say:

> *"Travel between these two areas of Siliguri is taking 43% longer than it normally does
> at this hour, based on 340 comparable observations."*

It **cannot** say:

> *"Congestion on the Sevoke Road segment between Air View More and Venus More."*

The first is defensible from the data. The second requires knowing which roads the trips
used, and this dataset does not record that.

**That is a narrower product than the blueprint imagined, and a truthful one.**
