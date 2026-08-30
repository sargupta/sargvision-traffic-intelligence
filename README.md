# SARGVISION Traffic Intelligence — Siliguri

Real-time urban mobility intelligence. The system observes live conditions,
compares them against what each movement normally does at that hour on that
kind of day, detects meaningful change, and surfaces it for investigation.

```
OBSERVE → UNDERSTAND → COMPARE → DETECT → CONNECT → EXPLAIN → INVESTIGATE
```

**Analytics discovers. AI explains. Humans decide.** No language model computes
a traffic figure anywhere in this system, and the copilot has no path to the
observations. Every number in an answer came out of a deterministic tool, and
the tool trace is returned with the answer.

---

## Architecture

```
                    OBSERVATION PROVIDER
              ReplayProvider  |  GoogleRoutesProvider
                          │
                          ▼
                  INTELLIGENCE LOOP  (5-minute ticks)
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
   CITY STATE        BASELINE LAYER     DETECTORS
   deviation         2019 pace          deterioration
   status            percentiles        persistence
   persistence       confidence         variability
   velocity                             spatial cluster
        └─────────────────┼──────────────────┘
                          ▼
                    CONSOLIDATION
              clusters absorb their members
           same-signal same-zone collapse to one
                          │
              ┌───────────┴────────────┐
              ▼                        ▼
      INTELLIGENCE FEED          COPILOT (tools only)
              └───────────┬────────────┘
                          ▼
                  DYNAMIC CONSOLE
        map canvas · feed · adaptive view directives
```

## The compliance boundary

Google's Maps Service Specific Terms permit caching **latitude and longitude
only**. Travel times from the Routes API may not be retained to build a
persistent dataset. A real-time product that stores every duration it fetches
is exactly what that prohibits.

So the collector is an interface with two implementations:

| Provider | Live | Retains durations | Role |
|---|---|---|---|
| `ReplayProvider` | no | yes — CC BY 4.0 data | demonstration, and the default |
| `GoogleRoutesProvider` | yes | **no** — 6-hour memory window | deployment |

The engine cannot tell them apart. The persistent analytical history comes from
the 2019 open dataset, which may be retained. If live history is needed, the
sanctioned route is a product licensed for it (Roads Management Insights, under
the Analytics Service Specific Terms) or first-party probe data — not a longer
cache on this one.

## The baseline layer

The 2019 dataset — **101,418 valid primary-route observations**, 143 days — is
not the product. It is the calibration layer that makes live comparison mean
anything.

- **Zones** are derived, not drawn. Endpoints are clustered by weighted k-means;
  the zone count is the largest at which every zone still holds enough evidence
  *and* has a landmark within 1.5 km to be honestly named after. That gives
  five: Siliguri Central, Siliguri Junction, Salugara, NJP Station, Champasari.
- **Baselines are built on pace** (seconds per kilometre), not journey time.
  Inside one movement-hour bin, trip distances span 5–10× and distance
  correlates 0.80 with travel time, so a baseline on seconds measures how far
  someone went. On seconds, 22.1% of observations scored as anomalies; on pace,
  2.9%.
- **Nothing is published below 30 observations** per movement-hour-daytype bin.
  Where the system is silent it is uninformed, and it says so rather than
  estimating into the gap.

## Running it

```bash
uv sync
PYTHONPATH=. .venv/bin/python scripts/build_analytics.py   # baseline layer
PYTHONPATH=. .venv/bin/python scripts/discover.py          # structural findings
PYTHONPATH=. .venv/bin/uvicorn apps.api.main:app --port 8099
npm --prefix apps/web run dev                              # console on :3040
```

`scripts/replay_day.py [YYYYMMDD]` drives a whole day through the loop and
prints what it found — the fastest way to see the engine work.

## What this is not

`is_live` is `False` in replay and the mode is on every API response that could
be mistaken for current conditions. Zone pairs are not roads. The system can
establish that something changed and by how much; it cannot establish why, and
no detector or prompt is permitted to imply otherwise.

See [`docs/known-limitations.md`](docs/known-limitations.md).
