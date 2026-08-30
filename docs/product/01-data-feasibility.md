# Data Feasibility — what we can and cannot know

`status: verified live` · 30 August 2026 · Every number here was produced by
running the code, not by reading documentation.

---

## 1. The 2019 dataset cannot give junction-level baselines

We tested whether the 101,418 historical observations map onto the 34 named
corridors. They do not.

| Junction catchment radius | Observations on a named corridor | Share |
|---|---|---|
| 300 m | 676 | 0.7% |
| 500 m | 2,081 | 2.1% |
| 750 m | 5,999 | 5.9% |
| **1,000 m** | **11,972** | **11.8%** |
| 1,500 m | 23,594 | 23.3% |

Junctions in Siliguri sit roughly 2 km apart, so a 1,000 m catchment already
means neighbouring junctions share territory, and 1,500 m is not a junction at
all. At the most generous defensible radius, **88% of the historical data does
not describe any named corridor.**

This is not a flaw in the dataset. It was sampled as random origin-destination
pairs across the city; it was never sampled on the junction network.

> **Conclusion.** The 2019 data is good evidence for **city-level structure** —
> the shape of the day, weekday against weekend, the free-flow ceiling. It is
> not evidence for **what happens at Venus More**. We must stop trying to make
> it be, and the product must work without it.

## 2. What the Routes API gives us instead — verified live

A single `computeRoutes` call returns both figures we need:

```
Venus More → Darjeeling More, along Hill Cart Road
  distance          3,359 m
  duration            886 s   traffic aware
  staticDuration      745 s   typical conditions
  congestion index  1.189     duration / staticDuration
```

**This solves the cold-start problem.** Congestion relative to a corridor's own
typical time is computable on the first request, with no accumulated history at
all — and therefore with nothing to retain.

### 2.1 Choke points inside a corridor

With `extraComputations: ["TRAFFIC_ON_POLYLINE"]` the response carries
`speedReadingIntervals`: segments of the route polyline classified `NORMAL`,
`SLOW` or `TRAFFIC_JAM`.

```
Venus More → Darjeeling More
  points   0– 57  NORMAL
  points  57– 60  SLOW      ← the choke point, located on the road
  points  60– 77  NORMAL
  points  77–104  SLOW
  points 104–141  NORMAL
```

This answers *"what are the choke points"* at **road-segment resolution inside a
named corridor** — not at the corridor level, and not at the zone level. It is
the single most valuable thing available to this product.

### 2.2 Live across the network

16 corridors probed at once, Sunday afternoon:

| Corridor | Index | Road |
|---|---|---|
| Air View More → Siliguri Junction | **1.500** | NH10 |
| Siliguri Junction → Darjeeling More | **1.413** | NH10 |
| Court More → Venus More | 1.252 | Court More Main Rd, Hill Cart Rd |
| Siliguri Junction → Mahananda Bridge | 1.239 | NH10 |
| Sevoke More → Air View More | 1.168 | Hill Cart Rd |
| Naukaghat → Jalpai More | 0.704 | NH10 |

Real road names come back with every route.

## 3. The limitation that remains

`staticDuration` is Google's typical-conditions estimate, not a measured
empty-road time. Six of sixteen corridors returned an index **below 1.0** —
currently faster than "typical". So the index is a comparison against a
modelled expectation, and it must be presented that way. It is reliable for
comparing corridors against each other and for tracking one corridor over the
day; it is not a physical claim about free-flow speed.

## 4. What still needs history, and what that costs

| Question | Needs history? | Available today |
|---|---|---|
| Is this corridor congested now? | No | **Yes** — index from one call |
| Where is the choke point on it? | No | **Yes** — speed intervals |
| Is it getting worse this hour? | No | **Yes** — successive calls in memory |
| Does this recur every Tuesday evening? | **Yes** | **No** — see below |
| Is the city improving year on year? | **Yes** | Only at city level, from 2019 |

Recurring-window analysis is the one requirement that needs retained travel
times, which the Maps Terms do not permit us to keep. The honest options are
Roads Management Insights under the Analytics Service Specific Terms, an
authorised data agreement, or first-party probe data. **Until one of those
exists, the product must not claim to know that a pattern recurs.** It can say
what it has seen since it started, in memory, and label it as exactly that.
