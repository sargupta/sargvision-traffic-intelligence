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

There are two front ends. **`apps/command-web`** (port 3050) is the duty
officer board — the deployed one, and the thing this repository is mainly
about. `apps/web` (port 3040) is the earlier narrative console kept for the
baseline write-up; it is not what the control room uses.

```bash
uv sync

# The baseline layer, from the 2019 extract. Optional: the board runs without
# it, and the tests that need it skip rather than fail.
PYTHONPATH=. .venv/bin/python scripts/build_analytics.py
PYTHONPATH=. .venv/bin/python scripts/discover.py

# The API. ROUTES_API_KEY is required — there is no data without it.
ROUTES_API_KEY=... \
CORS_ORIGINS=http://localhost:3050 \
AUTH_MODE=open \
  PYTHONPATH=. .venv/bin/uvicorn apps.api.main:app --port 8099

# The board. apps/command-web/.env.local should point at the API above;
# pointing it at the deployed API fails, because production CORS correctly
# allows only the deployed origin.
npm --prefix apps/command-web run dev
```

`scripts/replay_day.py [YYYYMMDD]` drives a whole day through the loop and
prints what it found — the fastest way to see the engine work.

### Environment

| variable | required | what it does |
|---|---|---|
| `ROUTES_API_KEY` | yes | Google Routes API key. Startup refuses without it. |
| `CORS_ORIGINS` | yes in production | Comma-separated allowed origins. Fails closed — an empty value permits nothing rather than everything. |
| `WRITE_TOKEN` | yes in production | The credential an officer needs to record an action. |
| `AUTH_MODE` | no | `token` (default) or `open`. See below. |
| `INCIDENT_STORE` | no | `memory` (default) or `firestore`. Only Firestore survives a restart. |
| `POLL_SECONDS` | no | Base cadence, 180 in production. Also drives the board's stale threshold, at 1.5 cycles. |
| `CONFIRM_MINUTES` | no | How long a condition must hold before it becomes an incident. 8 in production. |
| `LAPSE_MINUTES` | no | How long before an unattended incident is recorded as having cleared itself. |
| `TZ` | yes on Cloud Run | `Asia/Kolkata`. Without it the shift clock reads UTC, which is invisible on a machine already in IST. |

### Who may record an action

Reads are open: the board's figures are aggregates, and `/api/roster` returns
units without officer names or duty state. Recording is not, because every
action is a police record — and the endpoint was reachable unauthenticated
until the gate went in, on a public URL, with a durable store behind it.

Writes require `Authorization: Bearer $WRITE_TOKEN`. The gate **fails closed**:
with no token configured the API refuses every write with a 503 saying so,
rather than falling back to accepting anyone. `/health` reports the posture, so
an accidentally open deployment is visible from outside:

```
"writes": "gated" | "disabled — no WRITE_TOKEN configured" | "OPEN — anyone can record an action"
```

`AUTH_MODE=open` removes the gate and is for local development only. It is
never set on the deployed service, and the deploy smoke test fails if the live
API reports anything other than `gated` or accepts an anonymous write.

Set the token as the `WRITE_TOKEN` repository secret; the deploy passes it into
the service. The control room enters it once per console, from **Recording
locked** in the command bar. To rotate, change the secret and redeploy — every
console then needs the new value.

This is a shared room token, not per-officer identity. It proves the person at
the console belongs in the room; `by` still records which seat acted. Real
per-officer identity is the next step, and it is a directory problem rather
than a longer token.

## What this is not

`is_live` is `False` in replay and the mode is on every API response that could
be mistaken for current conditions. Zone pairs are not roads. The system can
establish that something changed and by how much; it cannot establish why, and
no detector or prompt is permitted to imply otherwise.

See [`docs/known-limitations.md`](docs/known-limitations.md).
