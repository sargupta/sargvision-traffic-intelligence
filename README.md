# SARGVISION Traffic Intelligence Copilot

**AI-powered traffic intelligence and investigation copilot.** Pilot city: **Siliguri, West Bengal.**

> Google Maps helps people see traffic.
> **This helps city authorities understand what the traffic means.**

---

## What it does

Answers the five questions a traffic officer actually has:

```
What needs attention?  →  Why?  →  Has this happened before?
        →  What else is affected?  →  What should I investigate?
```

Those five questions define the product APIs. Everything else serves them.

## What it does not do

No signal control. No CCTV. No ANPR. No live-monitoring claim. No physical-cause
diagnosis without evidence. It does not replace Google Maps, traffic engineers, or
the officer's judgement.

---

## Architecture

```
API  →  Application Service  →  Domain Service  →  Repository  →  Data Store
```

Never `API → LLM → Database`. The AI receives evidence from validated tools; it has
no database access of its own.

```
packages/
  contracts/     Metric contract — provenance enforced at construction
  domain/        Corridor · Observation · Event · Severity · Priority
  analytics/     baselines · anomalies · events · patterns        (deterministic)
  intelligence/  priority scoring · city insights                 (deterministic)
  replay/        replay clock — historical data as simulated time
  providers/     TrafficDataProvider protocol + implementations
apps/
  api/           FastAPI — the five product endpoints
  web/           Next.js dashboard
```

## Non-negotiable principles

1. The LLM does not calculate traffic metrics.
2. The LLM does not invent observations.
3. The system distinguishes **observation** from **interpretation** from **hypothesis**.
4. Every important insight is traceable to evidence.
5. Every important claim states its limitation.
6. The AI explains intelligence; it does not manufacture it.
7. Human authorities remain the decision-makers.

## Data

**Demonstrator mode runs on historical open data** — 101,418 valid primary-route
observations for Siliguri, June–November 2019, CC BY 4.0
(Zenodo `10.5281/zenodo.10499064`). See [`docs/data-provenance.md`](docs/data-provenance.md).

> ⚠️ **This is historical replay, not live monitoring**, and any demonstration must
> say so. The analytics engine is production architecture; the data source in this
> mode is 2019 history.

## Quickstart

```bash
uv sync
uv run scripts/fetch_data.py     # CC BY 4.0, no login
uv run uvicorn apps.api.main:app --reload
```
