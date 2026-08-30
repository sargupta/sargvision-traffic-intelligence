# SARGVISION Traffic Intelligence
## Technical Feasibility, Architecture and MVP Build Blueprint
### Siliguri Pilot — Critical Review and Recreated Technical Document

**Version:** 2.0  
**Status:** Proposed Technical Blueprint  
**Scope:** Independent MVP and demonstrator  
**Target geography:** Siliguri, West Bengal  
**Primary objective:** Prove a reusable traffic intelligence and investigation layer before obtaining live government traffic-system access.

---

# 1. Executive Summary

This document defines the technically credible path for building **SARGVISION Traffic Intelligence**, an AI-assisted system that converts traffic observations into operational intelligence for city authorities.

The previous architecture direction was broadly correct but required several corrections:

1. It over-emphasised the AI Copilot before establishing a sufficiently rigorous traffic intelligence model.
2. It treated map visualisation as a presentation layer rather than a core product design problem.
3. It implied that historical point/route observations could immediately become an operational corridor model without a formal spatial aggregation method.
4. It proposed "network intelligence" too early without defining the graph, topology, or evidence required.
5. It used terms such as "current traffic", "event", and "priority" without sufficiently separating historical replay from live operations.
6. It included a generic six-week timeline that understated the spatial data-engineering work.
7. It did not adequately distinguish what can be independently demonstrated today from what requires future data partnerships.
8. It risked producing a visually impressive demo that appears more operationally mature than the evidence supports.

The recreated architecture therefore follows a stricter principle:

> **Build the traffic intelligence substrate first. Build the visual investigation workspace second. Add the AI Copilot as a controlled interface to deterministic intelligence services.**

The MVP is feasible, but its strongest and most honest form is:

> **A historical traffic intelligence and investigation system for Siliguri, demonstrated through time-based replay and an evidence-grounded AI Copilot.**

It is not yet:

- a live city traffic command platform;
- a traffic signal optimisation system;
- a replacement for Google Maps;
- a CCTV analytics platform;
- a digital twin;
- an autonomous traffic-management system.

---

# 2. Critical Feasibility Conclusion

## Overall assessment

| Dimension | Assessment | Score |
|---|---|---:|
| Historical analytics | Highly feasible | 9.5/10 |
| Traffic baseline modelling | Highly feasible | 9/10 |
| Historical anomaly detection | Highly feasible | 9/10 |
| Event construction | Feasible | 8/10 |
| Historical replay | Highly feasible | 9.5/10 |
| Visualization workspace | Highly feasible | 9/10 |
| AI investigation Copilot | Highly feasible | 8.5/10 |
| Corridor model | Feasible but technically important | 7/10 |
| Network intelligence | Limited for MVP | 5.5/10 |
| Structural mobility inference | Exploratory | 5/10 |
| Live operational intelligence | Data-dependent | 4/10 today |
| Traffic intervention measurement | Future data-dependent | 5/10 |
| Signal optimisation | Out of MVP scope | 3/10 independently |

## Strategic conclusion

The MVP should be built.

However, the first version should prove only three things:

1. **Siliguri traffic observations can be transformed into a repeatable intelligence model.**
2. **An officer can investigate unusual traffic conditions faster than by manually inspecting maps and charts.**
3. **The architecture can later accept a live licensed data source without rebuilding the intelligence layer.**

That is a sufficiently strong startup MVP.

---

# 3. Product Definition

## Product

**SARGVISION Traffic Intelligence**

## MVP proposition

> An evidence-grounded traffic intelligence workspace that helps city authorities understand abnormal traffic conditions, historical patterns and investigation context.

## Core user question

The product must answer:

> **What deserves my attention, why does it deserve attention, and what evidence supports that conclusion?**

This is more precise than the earlier broad statement:

> "What is happening?"

The system must prioritise information, not merely display it.

---

# 4. What the Product Is and Is Not

## The product is

- a traffic observation analysis system;
- a historical baseline engine;
- an anomaly and event engine;
- an investigation workspace;
- a map-based intelligence interface;
- a controlled AI query interface;
- an evidence and traceability system.

## The product is not in V1

- a live traffic feed provider;
- a signal timing controller;
- a CCTV platform;
- an ANPR system;
- an automatic incident detector with ground-truth confirmation;
- a causal inference engine;
- a traffic simulation or digital twin;
- an autonomous recommendation engine.

This scope discipline is essential.

---

# 5. The Core Technical Thesis

The architecture should be designed around a stable canonical data contract.

```text
DATA SOURCE
     │
     ▼
INGESTION ADAPTER
     │
     ▼
CANONICAL TRAFFIC OBSERVATION
     │
     ▼
SPATIAL AGGREGATION
     │
     ▼
CORRIDOR / SEGMENT TIME SERIES
     │
     ▼
BASELINE ENGINE
     │
     ▼
ANOMALY ENGINE
     │
     ▼
EVENT ENGINE
     │
     ▼
INVESTIGATION MODEL
     │
     ├──────────────► VISUAL WORKSPACE
     │
     └──────────────► AI COPILOT TOOLS
```

The most important architectural asset is therefore not the dashboard.

It is:

> **The canonical traffic observation model and deterministic intelligence pipeline.**

If this is designed correctly, historical data, future Google-authorised sources, city systems and sensor-derived observations can all enter through adapters.

---

# 6. Primary User and Decision Context

## Primary user

Traffic operations officer or supervisory traffic officer.

## Secondary users

- senior police leadership;
- traffic planning personnel;
- municipal mobility stakeholders;
- technical analysts.

## MVP decision context

The system is not expected to command field operations.

It supports:

- prioritisation;
- investigation;
- historical context;
- briefing;
- post-event understanding.

## User workflow

```text
OPEN SYSTEM
     ↓
SEE PRIORITISED CONDITIONS
     ↓
SELECT ONE
     ↓
UNDERSTAND EVIDENCE
     ↓
COMPARE WITH EXPECTED BEHAVIOUR
     ↓
INSPECT TIME EVOLUTION
     ↓
CHECK RELATED SPATIAL CONTEXT
     ↓
ASK FOLLOW-UP QUESTIONS
     ↓
DECIDE WHETHER HUMAN INVESTIGATION IS WARRANTED
```

This workflow should drive the entire UI.

---

# 7. Data Reality and Constraints

## Existing historical evidence

The current Siliguri historical analysis includes:

- 14,612 trip records in the Siliguri frame;
- 115,347 raw joined observations;
- 115,330 valid observations after invalid-value removal;
- 101,418 valid primary-route observations;
- 14,558 represented trips;
- observation period from 2019-06-13 to 2019-11-05.

The canonical wording is:

> **101,418 valid primary-route observations**

The system must retain this distinction in documentation and UI provenance.

## Critical limitation

The historical data is:

- historical;
- unevenly sampled;
- not a continuous sensor feed;
- not necessarily dense enough for all corridor/time-bin combinations.

Therefore the MVP must implement:

> **minimum sample requirements and confidence labels**

rather than forcing intelligence everywhere.

---

# 8. The Most Important Missing Layer: Spatial Aggregation

The earlier design jumped too quickly from route observations to named corridors.

That is not technically rigorous.

A formal spatial model is required.

## Recommended spatial hierarchy

```text
CITY
 │
 ├── ZONE
 │
 │    ├── CORRIDOR
 │    │
 │    │    ├── SEGMENT
 │    │    │
 │    │    │    └── OBSERVATION
```

### City

Siliguri.

### Zone

Broad operational geography, for example:

- central commercial zone;
- northbound gateway zone;
- station/transport zone.

These should not be over-defined in V1.

### Corridor

A meaningful road movement axis.

Examples should only be named after spatial validation.

### Segment

The atomic spatial unit used for analytics.

Recommended MVP segment model:

- approximately 250–750 metres;
- direction-aware;
- stable identifier;
- geometry stored separately from analytical measures.

## Why segments matter

A road called "Sevoke Road" may have very different behaviour across its length.

Therefore:

> **The analytics engine should operate on segments first and aggregate to corridors second.**

---

# 9. Recommended Spatial Data Strategy

## Base road geometry

Use OpenStreetMap as the open geospatial reference layer.

Possible components:

```text
OpenStreetMap
      +
GeoPandas
      +
Shapely
      +
OSMnx
      +
PostGIS later if required
```

Google Maps should be used for product visualisation and user context, not as the permanent analytical road-network datastore.

## MVP process

```text
RAW OBSERVATION GEOMETRY
        ↓
CLEAN AND NORMALISE
        ↓
MAP MATCH / SPATIAL ASSIGNMENT
        ↓
ROAD SEGMENT ID
        ↓
DIRECTION
        ↓
TIME BIN
        ↓
SEGMENT METRICS
```

The exact map-matching approach should be selected after inspecting the raw observation geometry.

Do not prematurely assume that sophisticated map matching is necessary.

The first engineering spike should answer:

> Can the existing coordinates be reliably assigned to useful spatial units using simple spatial joins?

If yes, avoid unnecessary complexity.

---

# 10. Canonical Data Model

The MVP should define stable domain entities.

## TrafficObservation

```text
TrafficObservation
------------------
observation_id
source_id
source_type
observed_at
trip_id
route_rank

latitude
longitude

segment_id
corridor_id
direction

distance_m
traffic_duration_s
free_flow_duration_s

travel_time_ratio
delay_s
speed_proxy

quality_flags
```

Derived metrics should be calculated by deterministic services.

## SegmentMetric

```text
SegmentMetric
-------------
segment_id
time_bucket
observation_count

median_travel_ratio
median_delay_s

p25
p50
p75

baseline_ratio
deviation_percent

confidence
```

## TrafficAnomaly

```text
TrafficAnomaly
--------------
anomaly_id
segment_id
observed_at

metric_name
observed_value
expected_value

deviation_percent
severity

confidence
```

## TrafficEvent

```text
TrafficEvent
------------
event_id
status

started_at
ended_at

segment_ids
corridor_ids

peak_severity
peak_deviation

persistence_minutes

confidence
```

## Investigation

```text
Investigation
-------------
investigation_id
event_id

evidence_items
historical_matches
related_segments

limitations

generated_summary
```

---

# 11. Traffic Metrics

The system should use simple, explainable metrics in V1.

## Traffic Ratio

```text
traffic_ratio
=
traffic_duration
/
free_flow_duration
```

Interpretation:

```text
1.0 = approximately free-flow

1.3 = approximately 30% slower

1.6 = approximately 60% slower
```

## Delay

```text
delay_seconds
=
traffic_duration
-
free_flow_duration
```

## Deviation from Expected

```text
deviation_percent
=
(observed - expected)
/
expected
× 100
```

The exact metric must be documented in the API response.

Do not allow the UI to display ambiguous labels such as simply:

> +52%

without context.

The UI should say:

> **52% above expected travel-time ratio**

or equivalent.

---

# 12. Baseline Engine

The baseline is the foundation of the entire intelligence system.

## Initial baseline dimensions

For each sufficiently sampled segment:

```text
Segment
+
Hour of Day
+
Day Type
```

Potential day types:

- weekday;
- weekend.

Do not initially overfit with too many dimensions.

## Baseline output

```text
segment_id
hour
day_type

median
p25
p75
sample_count
confidence
```

## Minimum sample rule

If the historical sample is insufficient:

```text
NO BASELINE
```

or:

```text
LOW CONFIDENCE BASELINE
```

The system should not fabricate precision.

## Hierarchical fallback

Where appropriate:

```text
Segment baseline
      ↓ insufficient
Corridor baseline
      ↓ insufficient
City / road-class baseline
```

Fallbacks must be visible in metadata.

Example:

> Baseline confidence: LOW  
> Baseline source: Corridor-level fallback  
> Segment-level historical sample: insufficient

This is significantly more robust than pretending all roads have equal analytical confidence.

---

# 13. Anomaly Detection

The anomaly engine should remain deterministic.

## Recommended initial method

Use baseline deviation plus confidence.

```text
observed_metric
      ↓
compare
      ↓
expected_baseline
      ↓
deviation_percent
      ↓
severity_threshold
```

Initial calibrated thresholds:

| Severity | Deviation |
|---|---:|
| Normal | < 30% |
| Moderate | ≥ 30% |
| High | ≥ 45% |
| Critical | ≥ 60% |

These are:

- initial calibration values;
- configuration values;
- not universal traffic standards.

They should be stored in configuration.

## Do not start with machine learning

An advanced anomaly model is unnecessary for the MVP because:

- sample density is uneven;
- explainability matters;
- operational users need understandable rules;
- threshold calibration already has empirical grounding.

Advanced methods can later be compared against the deterministic baseline.

---

# 14. Event Engine

A single anomaly is not necessarily an event.

## Event construction

```text
ANOMALIES
    │
    ▼
TEMPORAL CONTINUITY
    │
    ▼
SPATIAL CONTINUITY
    │
    ▼
EVENT CANDIDATE
    │
    ▼
MERGE / EXTEND
    │
    ▼
TRAFFIC EVENT
```

## MVP event rules

An event may require:

- consecutive abnormal observations;
- minimum persistence duration;
- same or adjacent segment;
- compatible severity.

Example:

```text
18:00  +32%
18:05  +41%
18:10  +47%
18:15  +44%
```

Can become:

```text
Event ID: EVT-102

Start: 18:00
End: 18:15

Peak deviation: +47%

Duration: 15 minutes

Severity: HIGH
```

## Event lifecycle

```text
DETECTED
   ↓
ACTIVE
   ↓
STABILISING
   ↓
RESOLVED
```

For historical replay, these states are simulated according to replay time.

---

# 15. Priority Scoring

Priority should not be confused with raw severity.

A high deviation on an obscure, low-confidence segment may not deserve the same attention as a persistent event on an important corridor.

## Initial score

```text
Priority Score

=
Severity Score
× Persistence Factor
× Confidence Factor
× Corridor Importance Factor
```

For MVP, corridor importance can initially be:

- configurable;
- manually assigned;
- transparently labelled.

Do not claim it is objectively inferred until validated.

## Output

```text
Priority 1
HIGH

Reason:
High deviation + persistent condition + high-confidence baseline
```

This explanation should be shown directly in the UI.

---

# 16. Pattern Intelligence

Pattern intelligence should be narrowly scoped.

## MVP questions

- Has a similar event occurred before?
- At what times does this segment commonly worsen?
- Is the current condition persistent or short-lived?
- How variable is this corridor?
- Does the same pattern repeat?

## Similar-event retrieval

A simple first version can match:

```text
Same segment
+
similar hour
+
similar deviation band
+
similar duration
```

This is preferable to prematurely using embeddings or LLM similarity.

---

# 17. Network Intelligence: Critical Scope Correction

The earlier architecture gave "network intelligence" too much prominence.

With the current data, causal network propagation should not be claimed.

The MVP should instead implement:

> **Spatial context**

rather than full network intelligence.

## MVP spatial context

When investigating an event, show:

- nearby analysed segments;
- nearby abnormal segments;
- same-corridor conditions;
- geographic relationship.

The system may say:

> Nearby analysed segments also show elevated travel-time ratios.

It should not say:

> This event caused congestion to spread into those corridors.

Causality requires stronger evidence.

## Future network intelligence

Later:

```text
Road graph
+
topology
+
time-lag analysis
+
propagation analysis
+
incident ground truth
```

Only then should network propagation claims be explored.

---

# 18. Visualization Philosophy

The previous approach proposed many charts but did not define what each visualisation is supposed to answer.

Every visualization must answer one decision question.

| Visualization | Decision question |
|---|---|
| Priority list | What deserves attention? |
| Map | Where is it? |
| Timeline | When did it start and evolve? |
| Baseline chart | Why is it unusual? |
| Historical recurrence | Has it happened before? |
| Spatial context | What else is nearby? |
| City profile | What patterns define the city? |
| Confidence indicator | How much should I trust this? |

If a chart does not answer a decision question, remove it.

---

# 19. Visualization Architecture

```text
                    USER
                     │
                     ▼
             TRAFFIC WORKSPACE
                     │
      ┌──────────────┼──────────────┐
      │              │              │
      ▼              ▼              ▼
 PRIORITY VIEW    MAP VIEW     INVESTIGATION
      │              │              │
      └──────────────┼──────────────┘
                     │
                     ▼
               VIEW MODEL API
                     │
                     ▼
         TRAFFIC INTELLIGENCE SERVICES
                     │
                     ▼
                DOMAIN MODELS
```

The frontend should not:

- calculate anomalies;
- calculate baselines;
- infer event status;
- perform traffic scoring.

The backend should return visualisation-ready view models.

---

# 20. Screen 1 — Traffic Intelligence Home

This is the main operational screen.

```text
┌──────────────────────────────────────────────────────────────────┐
│ SARGVISION TRAFFIC INTELLIGENCE                     SILIGURI     │
├──────────────────────────────────────────────────────────────────┤
│ Historical Replay: ● RUNNING   18:30   [Pause] [2x] [10x]        │
├───────────────────┬──────────────────────────────────────────────┤
│ ATTENTION         │                                              │
│                   │                                              │
│ 1 HIGH            │                                              │
│ Corridor / Area   │                  MAP                         │
│ +52%              │                                              │
│                   │            SEGMENT OVERLAY                   │
│ 2 MODERATE        │                                              │
│ Corridor / Area   │                                              │
│ +34%              │                                              │
│                   │                                              │
│ 3 MODERATE        │                                              │
│ Corridor / Area   │                                              │
├───────────────────┴──────────────────────────────────────────────┤
│ ASK TRAFFIC COPILOT                                               │
│ What should I investigate at this time?                          │
└──────────────────────────────────────────────────────────────────┘
```

## Design principle

The officer should understand the top priorities without reading charts.

---

# 21. Screen 2 — Event Investigation Workspace

```text
┌──────────────────────────────────────────────────────────────────┐
│ ← BACK        EVENT INVESTIGATION                HIGH            │
├──────────────────────────────────────────────────────────────────┤
│ Segment / Corridor Context                                      │
│                                                                  │
│ [MAP WITH SELECTED SEGMENT + NEARBY CONTEXT]                     │
├──────────────────────────────────────────────────────────────────┤
│ WHAT HAPPENED?                                                   │
│                                                                  │
│ Observed metric      Expected baseline      Deviation             │
│     1.52                   1.00               +52%               │
│                                                                  │
│ Persistence: 25 minutes        Confidence: HIGH                  │
├──────────────────────────────────────────────────────────────────┤
│ HOW DID IT EVOLVE?                                               │
│                                                                  │
│                  ●                                               │
│              ●       ●                                           │
│          ●               ●                                       │
│  ______●___________________●_____                                │
│                                                                  │
│  Expected range + observed timeline                              │
├──────────────────────────────────────────────────────────────────┤
│ WHAT DO WE KNOW?                                                 │
│                                                                  │
│ Evidence summary                                                 │
│                                                                  │
│ [Observation] [Comparison] [Limitation] [Next step]              │
└──────────────────────────────────────────────────────────────────┘
```

This should be the most important screen in the product.

---

# 22. Screen 3 — Historical Traffic Replay

The replay must be technically honest.

The UI must always display:

> **Historical Replay**

## Replay model

```text
DATASET TIMESTAMP
        │
        ▼
REPLAY CLOCK
        │
        ▼
CURRENT SIMULATED TIME
        │
        ▼
ANALYTICS WINDOW
        │
        ▼
EVENT STATE
        │
        ▼
UI
```

## Controls

- date selection;
- start;
- pause;
- speed multiplier;
- reset;
- jump to known event.

## Important limitation

Replay does not prove real-time detection latency.

It proves that the analytical pipeline can process temporal observations and produce intelligence outputs.

This distinction should be explicit.

---

# 23. Screen 4 — Corridor Intelligence

A corridor page should answer:

> How does this location normally behave?

Recommended visualisations:

## A. Typical daily profile

```text
Traffic ratio

        observed
           ●
          / \
    ●----/---\----●

──────────────────────────
06  09  12  15  18  21
```

## B. Historical distribution

Show:

- median;
- expected range;
- current/replay observation.

## C. Reliability

Do not simply display a generic score.

Show the definition.

Example:

```text
Reliability

HIGH VARIABILITY

Reason:
Wide historical distribution for comparable periods.

Sample:
n = 420
```

---

# 24. Screen 5 — City Intelligence

This is a strategic screen, not a command screen.

## Recommended visuals

### Hourly city profile

Answers:

> When does traffic historically become difficult?

### Day × hour heatmap

Answers:

> When do recurring patterns appear?

### Observation coverage map

This is essential.

It shows:

> Where does the system actually have evidence?

This should have been included in the earlier visualization proposal.

### Confidence distribution

Shows:

- high-confidence areas;
- low-confidence areas;
- insufficient-data areas.

This prevents the map from implying city-wide intelligence where evidence is sparse.

---

# 25. The Most Important New Visualization: Evidence Coverage

The product should explicitly visualise data density.

```text
EVIDENCE COVERAGE

HIGH COVERAGE
██████████████

MODERATE
████████

LOW
███

INSUFFICIENT
░░
```

Spatially:

```text
CITY MAP

████  High evidence
▓▓▓▓  Moderate evidence
▒▒▒▒  Low evidence
░░░░  Insufficient evidence
```

This is critical for credibility.

Without it, a map can falsely imply that the entire city is equally observed.

---

# 26. Map Architecture

## Recommended MVP stack

```text
Google Maps JavaScript API
+
GeoJSON overlays
+
Application-generated segment layers
```

## Layers

### Layer 1 — Base map

Google Maps.

### Layer 2 — Analytical segments

GeoJSON / data-driven overlays.

### Layer 3 — Current replay state

Segment styling based on event or anomaly state.

### Layer 4 — Selected investigation

Highlighted segment.

### Layer 5 — Evidence coverage

Optional analytical overlay.

### Layer 6 — Context

Nearby analysed segments.

## Do not use map colours alone

Severity should also be communicated using:

- labels;
- icons;
- patterns;
- tooltips;
- textual status.

---

# 27. AI Copilot Architecture

The AI Copilot should be introduced after deterministic tools exist.

```text
USER
 │
 ▼
COPILOT API
 │
 ▼
INTENT + TOOL ROUTING
 │
 ├── get_priorities
 ├── investigate_event
 ├── get_segment_profile
 ├── get_historical_matches
 ├── get_spatial_context
 └── get_city_patterns
 │
 ▼
STRUCTURED TOOL RESULTS
 │
 ▼
GROUNDING LAYER
 │
 ▼
GEMINI
 │
 ▼
ANSWER WITH EVIDENCE + LIMITATIONS
```

## Key rule

The LLM should not receive raw datasets and be asked:

> Analyse the traffic.

Instead:

```text
Deterministic service
        ↓
Validated structured result
        ↓
LLM explanation
```

---

# 28. AI Response Schema

The Copilot should ideally return structured content.

```json
{
  "summary": "...",
  "observation": "...",
  "comparison": "...",
  "evidence": [
    {
      "metric": "...",
      "value": "...",
      "source": "..."
    }
  ],
  "limitations": [
    "..."
  ],
  "suggested_next_step": "..."
}
```

The frontend renders this structure.

Do not depend on uncontrolled prose parsing.

---

# 29. Tool Definitions

## get_priorities

Input:

```text
time
mode
```

Output:

```text
prioritised events
+
reason
+
confidence
```

## investigate_event

Input:

```text
event_id
```

Output:

```text
event timeline
baseline comparison
historical matches
spatial context
limitations
```

## get_segment_profile

Input:

```text
segment_id
time window
```

Output:

```text
baseline
distribution
sample count
reliability
confidence
```

## get_city_patterns

Output:

```text
hourly profile
recurring patterns
coverage
limitations
```

---

# 30. Backend Architecture

Recommended initial architecture:

```text
NEXT.JS FRONTEND
        │
        ▼
FASTAPI APPLICATION
        │
        ├───────────────┐
        ▼               ▼
APPLICATION       COPILOT SERVICE
SERVICES               │
        │               ▼
        │           GEMINI
        ▼
DOMAIN SERVICES
        │
        ├── BaselineService
        ├── AnomalyService
        ├── EventService
        ├── InvestigationService
        └── PatternService
        │
        ▼
REPOSITORIES
        │
        ▼
PARQUET / DUCKDB
```

This is sufficient for the MVP.

Do not begin with microservices.

---

# 31. Technology Stack

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
TanStack Query
Google Maps JavaScript API
Apache ECharts
```

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy only where needed
```

## Analytics

```text
Polars
DuckDB
PyArrow
NumPy
SciPy
GeoPandas
Shapely
OSMnx as needed
```

## AI

```text
Vertex AI
Gemini
Structured tool calling
```

## Storage

MVP:

```text
Parquet
DuckDB
Cloud Storage
```

Later:

```text
BigQuery
PostGIS / PostgreSQL
```

## Infrastructure

```text
Cloud Run
Artifact Registry
Cloud Storage
Secret Manager
Cloud Logging
Cloud Monitoring
Vertex AI
```

---

# 32. Why DuckDB + Parquet First?

For the existing scale, a large production database is unnecessary.

The MVP dataset is manageable.

Benefits:

- simple local development;
- low cost;
- analytical SQL;
- reproducibility;
- fast iteration;
- easy cloud export.

The architecture should hide storage behind repository interfaces.

Example:

```python
class TrafficObservationRepository(Protocol):
    def get_observations(...):
        ...
```

Then later:

```text
DuckDBTrafficRepository

BigQueryTrafficRepository

PostgresTrafficRepository
```

This avoids storage lock-in.

---

# 33. Data Provider Abstraction

This is the most important future-proofing pattern.

```text
TrafficDataProvider
        │
        ├── HistoricalDatasetProvider
        │
        ├── FutureLicensedProvider
        │
        ├── CitySystemProvider
        │
        └── SensorProvider
```

All providers produce:

```text
CanonicalTrafficObservation
```

The intelligence engine should not care where observations came from.

---

# 34. Repository Structure

```text
sargvision-traffic-intelligence/
│
├── apps/
│   ├── web/
│   └── api/
│
├── packages/
│   ├── domain/
│   │   ├── models/
│   │   ├── repositories/
│   │   └── services/
│   │
│   ├── analytics/
│   │   ├── ingestion/
│   │   ├── spatial/
│   │   ├── baseline/
│   │   ├── anomaly/
│   │   ├── events/
│   │   ├── patterns/
│   │   └── replay/
│   │
│   ├── intelligence/
│   │   ├── priorities/
│   │   ├── investigations/
│   │   └── view_models/
│   │
│   └── copilot/
│       ├── tools/
│       ├── prompts/
│       └── grounding/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── curated/
│   └── samples/
│
├── scripts/
│
├── notebooks/
│
├── docs/
│   ├── architecture/
│   ├── methodology/
│   └── data_provenance/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── data/
│
└── infrastructure/
```

---

# 35. MVP Engineering Phases

## Phase 0 — Data and Spatial Feasibility Spike

**Duration: 3–5 days**

Questions:

- What exact geometry exists in the observations?
- Can observations be spatially assigned reliably?
- What segment size is appropriate?
- What coverage exists?
- How many segments meet minimum sample thresholds?

Deliverable:

> Spatial feasibility report.

This phase should happen before frontend work.

---

## Phase 1 — Canonical Data Pipeline

**Duration: 3–5 days**

Build:

- reproducible ingestion;
- data validation;
- canonical observation table;
- provenance logging.

Deliverable:

```text
processed_observations.parquet
```

with reproducible generation.

---

## Phase 2 — Spatial Model

**Duration: 1–2 weeks**

Build:

- road/segment model;
- spatial assignment;
- corridor aggregation;
- coverage metrics.

Deliverable:

> Segment-level analytical dataset.

This is likely the most uncertain technical phase.

---

## Phase 3 — Intelligence Engine

**Duration: 1 week**

Build:

- baselines;
- confidence;
- anomaly classification;
- event construction;
- priority scoring.

Deliverable:

> Reproducible event output.

---

## Phase 4 — Historical Replay

**Duration: 3–5 days**

Build:

- replay clock;
- event lifecycle;
- deterministic playback.

Deliverable:

> API-driven historical replay.

---

## Phase 5 — Visualization Workspace

**Duration: 1–2 weeks**

Build:

- home;
- map;
- priorities;
- investigation;
- corridor intelligence;
- city intelligence;
- evidence coverage.

Deliverable:

> End-to-end visual investigation workflow.

---

## Phase 6 — AI Copilot

**Duration: 4–7 days**

Build:

- tool definitions;
- structured results;
- grounding;
- answer schema;
- limitation handling.

Deliverable:

> Controlled traffic intelligence Copilot.

---

## Phase 7 — Validation and Demo

**Duration: 1 week**

Validate:

- calculations;
- reproducibility;
- false claims;
- UI labels;
- AI hallucination;
- demo scenarios.

---

# 36. Realistic Timeline

The earlier six-week estimate was optimistic if one person is simultaneously solving spatial modelling and product engineering.

A more realistic timeline:

| Phase | Duration |
|---|---:|
| Data feasibility | 1 week |
| Spatial model | 1–2 weeks |
| Intelligence engine | 1 week |
| Replay | 1 week |
| UI | 1–2 weeks |
| AI Copilot | 1 week |
| Testing and polish | 1 week |

## Total

> **7–10 weeks for a robust solo MVP**

A basic visual prototype can appear sooner, but should not be confused with a validated intelligence product.

---

# 37. Testing Strategy

## Data tests

Verify:

- row counts;
- null handling;
- invalid values;
- duplicate observations;
- route rank logic.

## Analytical tests

Test:

- baseline calculation;
- percentile calculation;
- deviation calculation;
- severity thresholds;
- confidence rules.

## Event tests

Test:

- event creation;
- event extension;
- event merging;
- resolution.

## Spatial tests

Test:

- observation-to-segment assignment;
- direction;
- segment boundaries;
- coverage.

## AI tests

Create a fixed evaluation set.

Example:

```text
Question:
Why is this event important?

Expected:
Must cite deviation, persistence and confidence.

Must not:
Invent physical cause.
```

This should be automated.

---

# 38. Key Dependencies

## Independent now

- historical dataset;
- open-source geospatial data;
- local analytics;
- GCP;
- Gemini;
- Google Maps visualisation.

## Future dependencies

- persistent licensed live traffic observations;
- government operational data;
- intervention records;
- validated road hierarchy;
- institutional adoption.

The architecture should ensure that none of these future dependencies block MVP development.

---

# 39. Major Risks

## Risk 1 — Insufficient spatial coverage

### Mitigation

Show evidence coverage explicitly.

Do not produce intelligence where confidence is insufficient.

---

## Risk 2 — False operational appearance

### Mitigation

Clearly label:

> Historical Replay

Do not simulate "live" without disclosure.

---

## Risk 3 — AI hallucination

### Mitigation

Tool-only evidence retrieval.

Structured answer schema.

Mandatory limitations.

---

## Risk 4 — Overbuilding network intelligence

### Mitigation

Implement spatial context first.

Defer causal propagation modelling.

---

## Risk 5 — Premature machine learning

### Mitigation

Use explainable deterministic methods first.

Benchmark advanced models later.

---

## Risk 6 — UI overemphasises maps

### Mitigation

The map must support decisions.

The primary entry point remains prioritised intelligence.

---

## Risk 7 — Historical data interpreted as current truth

### Mitigation

Attach:

- time period;
- sample count;
- confidence;
- provenance

to analytical outputs.

---

# 40. Recommended MVP Scope

## Must Build

### Data

- reproducible ingestion;
- canonical observation model;
- spatial assignment;
- segment model.

### Intelligence

- baseline;
- confidence;
- anomaly;
- event;
- priority;
- historical comparison.

### Visualization

- priority workspace;
- map;
- event investigation;
- timeline;
- baseline chart;
- evidence coverage;
- historical replay.

### AI

- five to seven controlled tools;
- grounded explanation;
- limitation disclosure.

---

## Explicitly Defer

- live continuous collection;
- signal optimisation;
- intervention recommendation automation;
- causal network propagation;
- CCTV;
- ANPR;
- computer vision;
- digital twin;
- predictive traffic forecasting;
- reinforcement learning.

---

# 41. MVP Success Metrics

The MVP should not be judged by generic dashboard metrics.

Measure:

## Analytical validity

- percentage of outputs with reproducible derivation;
- percentage of baselines above confidence threshold;
- event reproducibility.

## AI safety

- unsupported factual claim rate;
- missing limitation rate;
- tool grounding rate.

## Usability

Can a user answer:

> What deserves attention?

within 30 seconds?

Can they answer:

> Why?

within 2 minutes?

## Demo credibility

Can every displayed number be traced back to:

- source;
- formula;
- sample;
- limitation?

If not, it is not ready.

---

# 42. Architecture Evolution

## Stage 1 — Historical Intelligence

```text
Historical Data
      ↓
Spatial Model
      ↓
Traffic Intelligence Engine
      ↓
Replay
      ↓
Investigation Workspace
      ↓
AI Copilot
```

## Stage 2 — Live Observation Adapter

```text
Live Licensed Data
       ↓
Provider Adapter
       ↓
Canonical Observation
       ↓
Existing Intelligence Engine
```

No rewrite of core analytics.

## Stage 3 — Intervention Intelligence

```text
Before
   ↓
Intervention Record
   ↓
After
   ↓
Impact Evaluation
```

## Stage 4 — Expanded City Mobility Intelligence

Potential additional sources:

- incident reports;
- road works;
- events;
- weather;
- public transport;
- authorised camera analytics.

Only after the evidence and governance model is mature.

---

# 43. Final Architecture

```text
                     DATA PROVIDERS
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
 Historical Data      Future Licensed      Future City
                      Live Provider        Systems
         │                 │                 │
         └─────────────────┼─────────────────┘
                           │
                           ▼
                 INGESTION ADAPTERS
                           │
                           ▼
            CANONICAL TRAFFIC OBSERVATION
                           │
                           ▼
                   SPATIAL MODEL
                    │         │
                    ▼         ▼
                 SEGMENTS   CORRIDORS
                    │         │
                    └────┬────┘
                         ▼
                 METRIC AGGREGATION
                         │
                         ▼
                  BASELINE ENGINE
                         │
                         ▼
                  ANOMALY ENGINE
                         │
                         ▼
                   EVENT ENGINE
                         │
                         ▼
                 PRIORITY ENGINE
                         │
          ┌──────────────┴──────────────┐
          │                             │
          ▼                             ▼
  INVESTIGATION VIEW               AI TOOLS
          │                             │
          ▼                             ▼
    VISUAL WORKSPACE               GEMINI COPILOT
          │                             │
          └──────────────┬──────────────┘
                         ▼
                    HUMAN USER
```

---

# 44. Final Recommendation

Proceed with the project, but start in this order:

## Step 1

Validate the spatial model.

Do not build the UI first.

## Step 2

Create the canonical observation dataset.

Make the pipeline reproducible.

## Step 3

Build segment-level metrics and evidence coverage.

Determine where the data is genuinely useful.

## Step 4

Build deterministic baseline, anomaly and event logic.

## Step 5

Create historical replay.

## Step 6

Build the visual investigation workspace.

## Step 7

Add the AI Copilot last.

The AI Copilot should sit on top of a working intelligence system.

It should not become a substitute for one.

---

# Final Strategic Position

The proprietary value is not:

- the Google map;
- the LLM;
- the dashboard;
- the historical dataset.

The defensible asset is the combination of:

> **Canonical traffic data model + spatial intelligence model + deterministic evidence engine + investigation workflow + AI interface.**

The MVP should prove that SARGVISION can transform imperfect traffic observations into transparent, explainable and operationally useful intelligence.

That is technically feasible today.

The next major uncertainty is not whether the software can be built.

It is whether the existing observations can be converted into a sufficiently reliable spatial model for meaningful segment-level intelligence.

Therefore the correct first engineering task is:

> **Run a Spatial Feasibility Spike before committing to the rest of the implementation.**
