# SARGVISION Traffic Intelligence Copilot
## Siliguri MVP — Final Product and Build Strategy

**Version:** 1.0  
**Status:** Final MVP Direction  
**Purpose:** Independent startup demonstrator built using existing historical data, Google Maps Platform access, open-source technologies, and GCP startup credits.

---

# 1. Executive Summary

SARGVISION should **not** begin by building a generic traffic dashboard, a signal optimisation system, or a historical analytics tool.

The MVP should be built as:

> # An AI-powered Traffic Intelligence and Investigation Copilot for Siliguri Traffic Authorities

The core purpose is to help a traffic officer answer:

- What needs attention?
- Why is it unusual?
- Has this happened before?
- What other roads or corridors may be affected?
- What patterns are emerging?
- What should be investigated next?
- What have we learned about Siliguri's traffic?

The system is positioned above raw traffic visualisation.

Google Maps can show that traffic is slow.

SARGVISION should help answer:

> **Is this unusual, how important is it, what historical evidence supports it, what else is connected, and what should an officer investigate?**

---

# 2. The Product We Are Actually Building

## Product Name

**SARGVISION Traffic Intelligence Copilot**

## Pilot City

**Siliguri, West Bengal**

## Primary User

Traffic police officers, traffic control room personnel, senior police officers and city mobility decision-makers.

## Core Product Category

**AI-powered traffic intelligence and decision-support system.**

The product is not intended to:

- autonomously control traffic signals;
- replace traffic engineers;
- operate CCTV;
- perform ANPR;
- claim physical causes without evidence;
- replace Google Maps.

It is intended to:

- organise traffic information;
- identify abnormal conditions;
- compare current conditions with historical behaviour;
- detect recurring patterns;
- prioritise what requires attention;
- help officers investigate traffic events;
- communicate intelligence through an AI Copilot.

---

# 3. The Strategic Positioning

## Google Maps answers:

> Where is traffic slow?

## SARGVISION answers:

> Is this unusual?

> Has this happened before?

> How significant is it?

> What else is affected?

> Is this part of a recurring pattern?

> What should I investigate next?

> What have we learned about the city's traffic structure?

The product therefore sits above the raw mobility data layer.

```text
RAW MOBILITY DATA
        ↓
CITY-SPECIFIC BASELINES
        ↓
ANOMALY DETECTION
        ↓
EVENT PRIORITISATION
        ↓
PATTERN & NETWORK ANALYSIS
        ↓
EVIDENCE RETRIEVAL
        ↓
AI-ASSISTED INVESTIGATION
        ↓
HUMAN DECISION
```

---

# 4. The MVP

The MVP should be a complete vertical slice of the actual product.

It should not be:

> A historical dashboard.

It should be:

> **A Traffic Intelligence and Investigation System with an AI Copilot interface.**

The MVP revolves around three flagship workflows.

---

# 5. Workflow 1 — What Needs Attention?

## User Question

> What should I pay attention to?

The system analyses available traffic intelligence and returns prioritised events.

Example:

```text
TRAFFIC PRIORITIES

1. Corridor A
   HIGH
   Travel time significantly above expected baseline

2. Corridor B
   HIGH
   Persistent abnormal condition

3. Corridor C
   MODERATE
   Recurring slowdown pattern
```

The officer should not need to manually search through dozens of roads.

The product should prioritise attention.

## Core Principle

Traffic severity is not the same as operational priority.

A useful priority model should eventually consider:

```text
OPERATIONAL PRIORITY

=

TRAFFIC MAGNITUDE

×

PERSISTENCE

×

CORRIDOR IMPORTANCE

×

RECURRENCE / CONTEXT
```

This should remain configurable and evidence-based.

---

# 6. Workflow 2 — Investigate a Traffic Problem

## User Action

The officer selects an event and asks:

> Why is this unusual?

The system investigates the event through deterministic tools.

```text
EVENT
  ↓
Historical comparison
  ↓
Time-of-day comparison
  ↓
Persistence analysis
  ↓
Related corridor analysis
  ↓
Recurring pattern analysis
  ↓
Evidence retrieval
  ↓
AI explanation
```

Example response:

> Travel time on this corridor is currently significantly above the historical median for comparable observations. The abnormal condition has persisted beyond the typical duration threshold. Similar conditions have occurred during comparable periods in the historical dataset. Related traffic conditions are also present on connected corridors. The available data does not establish the physical cause.

The response must clearly separate:

```text
OBSERVATION

↓

INTERPRETATION

↓

HYPOTHESIS

↓

LIMITATION

↓

RECOMMENDED NEXT STEP
```

The AI must never present a hypothesis as a fact.

---

# 7. Workflow 3 — What Have We Learned About Siliguri?

This workflow provides strategic city-level intelligence.

Example questions:

> What are Siliguri's biggest traffic patterns?

> When is traffic most difficult?

> Which corridors are least reliable?

> What recurring patterns deserve investigation?

> How much of the speed gap appears related to congestion versus structural traffic conditions?

Possible output:

```text
SILIGURI TRAFFIC INTELLIGENCE

1. No conventional morning peak was observed
   in the historical dataset.

2. Traffic forms a broad operational plateau
   approximately between 10:00 and 20:00.

3. The worst observed period is around 19:00.

4. Historical data indicates that structural
   mixed-traffic conditions may explain a larger
   proportion of reduced traffic performance than
   episodic congestion alone.

5. Corridor-level conclusions are limited by
   uneven historical sample density.
```

This is not a live operational workflow.

It is a strategic intelligence workflow.

---

# 8. The Historical Dataset

The historical dataset is an evidence and calibration layer.

It is not the entire product.

## Data Provenance

Zenodo record:

`10.5281/zenodo.10499064`

Dataset associated with the research by Akbar, Couture, Duranton and Storeygard on urban mobility and congestion in India.

## Siliguri Identification

```text
Country: India
City: Siliguri
City Code: 21405
```

## Canonical Derivation

```text
alltrips_India.dta
2,735,442 India trip records
        ↓
Filter citycode = 21405
        ↓
14,612 Siliguri trip records
        ↓
Join with world_main_India_precleaned.dta
21,657,714 observations
        ↓
115,347 raw joined observations
        ↓
Remove invalid records
traffic_s / notraffic_s / dist_m ≤ 0
        ↓
115,330 valid observations
        ↓
Keep primary route
minimum route_rank
        ↓
101,418 valid primary-route observations
        ↓
14,558 represented trips
```

## Date Range

```text
2019-06-13 → 2019-11-05
```

## Important Terminology

The canonical figure is:

> **101,418 valid primary-route observations**

It should not be described as:

> 101,418 raw observations.

The raw joined count is:

> **115,347 raw joined observations**

The historical dataset should be used for:

- methodology validation;
- baseline development;
- threshold calibration;
- historical traffic pattern analysis;
- product demonstration;
- traffic replay.

It should not be represented as sufficient for:

- comprehensive current operational monitoring;
- high-confidence analysis of every corridor;
- live traffic management.

---

# 9. Siliguri-Specific Findings

The pilot established several important findings.

## Peak Traffic Pattern

The historical analysis does not support a conventional assumption of:

```text
Morning Peak
+
Evening Peak
```

Instead, the observed pattern suggests:

```text
07:00
Below free-flow

10:00–20:00
Broad traffic plateau

Approximately 19:00
Worst observed period
```

Therefore:

> The platform must empirically derive city-specific traffic patterns rather than assuming generic urban peak-hour behaviour.

---

## Alert Threshold Calibration

The pilot tested anomaly thresholds against Siliguri observations.

Recommended initial thresholds:

| Severity | Deviation from Expected |
|---|---:|
| Normal | < 30% |
| Moderate | ≥ 30% |
| High | ≥ 45% |
| Critical | ≥ 60% |

These thresholds must remain configuration-driven.

They should not be permanently hard-coded.

The threshold system should evolve as additional validated data becomes available.

---

## Structural Traffic Finding

The pilot suggests that episodic congestion may explain only a minority of the observed traffic speed gap, while mixed-traffic characteristics may account for a larger structural component.

This should be treated carefully.

The platform may identify:

- speed differences;
- recurring patterns;
- structural correlations;
- corridor behaviour.

It should not claim causal certainty without additional evidence.

This finding motivates a future product area:

> **Mixed Traffic Intelligence**

but does not justify prematurely building CCTV or computer vision infrastructure.

---

# 10. The Correct MVP Architecture

```text
                    USER / OFFICER

                           │
                           ▼

                  TRAFFIC COPILOT UI

                           │

            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼

      QUESTION                        EVENT
      INVESTIGATION                   INVESTIGATION

            │                             │
            └──────────────┬──────────────┘
                           │
                           ▼

                    AI ORCHESTRATOR

                           │

           ┌───────────────┼────────────────┐
           │               │                │
           ▼               ▼                ▼

        EVENT TOOL     PATTERN TOOL    NETWORK TOOL

           │               │                │
           └───────────────┼────────────────┘
                           │
                           ▼

               TRAFFIC INTELLIGENCE ENGINE

                           │

           ┌───────────────┼─────────────────┐
           │               │                 │
           ▼               ▼                 ▼

      Historical      Google Maps       Derived
      Dataset         Context           Intelligence
```

---

# 11. Core Product Layers

## Layer 1 — Data Layer

Initial sources:

```text
Historical Siliguri Dataset
        +
Google Maps Visual Context
        +
Derived Product Intelligence
```

Future sources may include:

- authorised city mobility data;
- road closure information;
- police incident reports;
- event calendars;
- weather;
- CCTV analytics.

These are explicitly outside the first independent MVP.

---

## Layer 2 — Traffic Intelligence Engine

Deterministic services responsible for:

- baseline calculation;
- anomaly detection;
- event persistence;
- priority scoring;
- historical comparison;
- pattern detection;
- reliability analysis;
- network relationships.

No LLM should calculate these metrics.

---

## Layer 3 — Evidence Layer

Every product insight should be traceable.

Each important metric should carry:

```text
METRIC
  │
  ├── Definition
  ├── Source
  ├── Derivation
  └── Limitation
```

Example:

| Attribute | Example |
|---|---|
| Metric | 101,418 |
| Definition | Valid primary-route observations |
| Source | Historical research dataset |
| Derivation | City filter → join → validation → primary-route selection |
| Limitation | Historical and uneven corridor density |

---

## Layer 4 — AI Copilot

The AI is responsible for:

- understanding user questions;
- selecting appropriate tools;
- retrieving evidence;
- synthesising results;
- explaining findings;
- identifying limitations.

The AI is not responsible for:

- calculating traffic metrics;
- inventing observations;
- independently diagnosing physical causes;
- overriding deterministic results.

---

## Layer 5 — User Experience

The interface should support:

- map-based context;
- prioritised attention;
- event investigation;
- historical comparison;
- AI conversation.

The dashboard is an interface.

The intelligence engine is the product.

---

# 12. AI Copilot Architecture

```text
USER QUESTION
       │
       ▼
TRAFFIC COPILOT
       │
       ▼
INTENT CLASSIFICATION
       │
       ▼
SELECT TOOL(S)
       │
       ▼
DETERMINISTIC SERVICES
       │
       ▼
EVIDENCE
       │
       ▼
GEMINI
       │
       ▼
GROUNDED RESPONSE
```

Example tools:

```text
get_priorities()

get_active_events()

get_event_evidence()

get_corridor_intelligence()

get_historical_baseline()

get_event_history()

get_city_patterns()

get_related_corridors()

get_city_summary()
```

The architecture should be:

```text
Agent
  ↓
Validated Tool
  ↓
Application Service
  ↓
Domain Service
  ↓
Repository
  ↓
Data Store
```

The AI should never receive unrestricted database access.

---

# 13. Required AI Response Contract

Every important Copilot response should follow a structured reasoning output.

## Observation

What does the data show?

## Comparison

How does it compare with the expected or historical baseline?

## Interpretation

Why is this operationally relevant?

## Limitation

What does the available data not establish?

## Suggested Next Step

What should an officer investigate?

Example:

> **Observation:** Travel time is significantly above the expected historical range.

> **Comparison:** Comparable observations show materially lower travel times.

> **Interpretation:** The condition is operationally unusual and persistent.

> **Limitation:** Available data does not establish the physical cause.

> **Suggested Next Step:** Investigate whether a local incident, road obstruction or network-level condition is present.

---

# 14. MVP Demonstration Strategy

The MVP should use two modes.

## Mode A — Historical Traffic Replay

A historical day is replayed as though it were unfolding live.

```text
Historical Timestamp
        ↓
Replay Clock
        ↓
Current Simulated Time
        ↓
Traffic Intelligence Engine
        ↓
Events and Priorities
        ↓
AI Copilot
```

The user can:

- start;
- pause;
- reset;
- accelerate time;
- investigate events.

This demonstrates operational behaviour without claiming live production monitoring.

---

## Mode B — City Intelligence

The user explores:

- historical traffic profile;
- recurring patterns;
- corridor reliability;
- anomaly distribution;
- structural observations.

---

# 15. Demo Story

The product demonstration should be a story, not a feature tour.

## Scene 1 — The Problem

Show a map.

Explain:

> Seeing slow traffic does not tell an officer whether the condition is normal, unusual, recurring or operationally important.

---

## Scene 2 — Traffic Memory

Show:

> 101,418 valid primary-route observations analysed.

Then demonstrate the Siliguri traffic profile.

---

## Scene 3 — Traffic Event

Start the replay.

An abnormal event emerges.

Example:

```text
HIGH PRIORITY EVENT

Current deviation:
+52%

Expected travel time:
18 minutes

Observed travel time:
27 minutes

Persistence:
25 minutes
```

---

## Scene 4 — Investigation

Click:

> Investigate

Show:

- baseline comparison;
- timeline;
- event persistence;
- related corridors;
- historical recurrence.

---

## Scene 5 — AI Copilot

Ask:

> Why should I care about this?

The Copilot provides an evidence-grounded explanation.

---

## Scene 6 — Strategic Insight

Ask:

> What have we learned about Siliguri traffic?

Show city-level patterns and limitations.

---

# 16. Recommended Technology Stack

The stack should remain lean.

## Frontend

```text
Next.js
TypeScript
Tailwind CSS
shadcn/ui
TanStack Query
Apache ECharts
Google Maps JavaScript API
```

---

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy where required
```

---

## Data and Analytics

For the independent MVP:

```text
Python
Polars
Pandas where convenient
NumPy
SciPy
DuckDB
Parquet
```

Start locally with:

```text
Parquet + DuckDB
```

Move to BigQuery only when operational scale or cloud analytics requires it.

---

## AI

```text
Google Gemini
Vertex AI
Tool-based agent architecture
```

Google ADK may be introduced when multi-agent orchestration or more formal agent workflows become necessary.

It is not mandatory on day one.

---

## Cloud

```text
Cloud Run
Cloud Storage
Vertex AI
Secret Manager
Cloud Logging
Cloud Monitoring
```

Optional later:

```text
BigQuery
Cloud SQL / PostgreSQL
Pub/Sub
Cloud Scheduler
```

---

# 17. What Must Be Set Up Now

## Google Cloud Project

Create a dedicated project for the product.

Example:

```text
SARGVISION Traffic Intelligence
```

Enable:

- Cloud Run API;
- Artifact Registry API;
- Cloud Storage API;
- Vertex AI API;
- Secret Manager API;
- Cloud Logging;
- Cloud Monitoring.

---

## Google Maps

Enable:

- Maps JavaScript API.

Configure:

- API key restrictions;
- domain restrictions;
- usage quotas.

Routes API may be used experimentally where permitted, but the MVP architecture must not depend on continuous traffic polling or retention assumptions.

---

## Local Development

Recommended:

```text
Python 3.12+
Node.js 22+
pnpm
Git
Docker Desktop
Google Cloud CLI
VS Code
```

Python dependency management:

```text
uv
```

---

# 18. What We Do Not Need for MVP

Do not wait for:

```text
Roads Management Insights

City-wide live data integration

CCTV

ANPR

IoT sensors

Traffic signal APIs

Police operational systems

Kafka

Kubernetes

Microservices

Digital twins
```

These are not required to demonstrate the intelligence product.

---

# 19. Recommended Repository Structure

```text
sargvision-traffic-intelligence/
│
├── apps/
│   │
│   ├── web/
│   │
│   └── api/
│
├── packages/
│   │
│   ├── domain/
│   │
│   ├── analytics/
│   │   ├── baselines/
│   │   ├── anomalies/
│   │   ├── events/
│   │   ├── patterns/
│   │   └── network/
│   │
│   ├── intelligence/
│   │
│   ├── replay/
│   │
│   └── contracts/
│
├── data/
│   │
│   ├── raw/
│   ├── processed/
│   └── samples/
│
├── scripts/
│
├── notebooks/
│
├── docs/
│
├── infrastructure/
│
└── tests/
```

The architecture should follow clean boundaries.

Avoid:

```text
API → LLM → Database
```

Prefer:

```text
API
 ↓
Application Service
 ↓
Domain Service
 ↓
Repository
 ↓
Data Store
```

---

# 20. Correct Build Sequence

The build should be product-led but technically disciplined.

## Phase 1 — Define the Officer Workflow

Define the five core questions:

```text
What needs attention?

Why?

Has this happened before?

What else is affected?

What should I investigate?
```

These questions define the product APIs.

---

## Phase 2 — Build Product Intelligence APIs

Examples:

```text
GET /priorities

GET /events/{id}/investigation

GET /corridors/{id}/intelligence

GET /city/insights

GET /city/summary
```

Do not expose generic analytics tables as the primary product interface.

Build APIs around user decisions.

---

## Phase 3 — Build the Deterministic Intelligence Engine

Implement:

- historical baselines;
- anomaly detection;
- severity classification;
- persistence detection;
- event lifecycle;
- priority scoring;
- recurrence analysis.

This is the product's analytical core.

---

## Phase 4 — Build Historical Traffic Replay

Create a replay clock.

```text
Historical Data
       ↓
Replay Clock
       ↓
Simulated Current State
       ↓
Intelligence Engine
       ↓
Events
```

---

## Phase 5 — Build the AI Copilot

Add:

- intent recognition;
- tool selection;
- evidence retrieval;
- grounded response generation.

---

## Phase 6 — Build the Dashboard

Build only the screens required to support the workflows:

1. Traffic Pulse
2. Map
3. Event Investigation
4. City Intelligence
5. AI Copilot

---

## Phase 7 — Deploy

Deploy:

```text
Next.js Frontend
       ↓
Cloud Run

FastAPI Backend
       ↓
Cloud Run

Vertex AI
       ↓
Gemini
```

---

# 21. First Alpha Deliverable

The first meaningful product milestone should be:

# SARGVISION Traffic Intelligence Copilot — Alpha

A user should be able to:

1. Open the application.
2. See Siliguri on a map.
3. Start a historical traffic replay.
4. See prioritised traffic events.
5. Select an event.
6. Investigate why it is unusual.
7. View historical evidence.
8. Ask the AI Copilot follow-up questions.
9. Receive evidence-grounded answers.
10. Understand what the data does and does not establish.

---

# 22. MVP Success Criteria

The MVP is successful if a traffic officer can answer within approximately 30 seconds:

> What should I pay attention to?

And then within a few minutes:

> Why is this unusual?

> Has this happened before?

> What evidence supports this?

> What should I investigate next?

The MVP does not need to prove that SARGVISION can operate Siliguri's traffic infrastructure.

It needs to prove:

> **SARGVISION can convert traffic observations into operational intelligence and make that intelligence accessible through an AI Copilot.**

---

# 23. Non-Negotiable Product Principles

## Principle 1

> The LLM does not calculate traffic metrics.

---

## Principle 2

> The LLM does not invent observations.

---

## Principle 3

> The system distinguishes observation from interpretation and hypothesis.

---

## Principle 4

> Every important insight must be traceable to evidence.

---

## Principle 5

> Every important claim should state its limitation.

---

## Principle 6

> The AI explains intelligence; it does not manufacture intelligence.

---

## Principle 7

> Human authorities remain the decision-makers.

---

# 24. Final Product Vision

The immediate MVP is:

> **An AI-powered Traffic Intelligence and Investigation Copilot for Siliguri.**

The longer-term product can evolve into:

```text
PHASE 1
Understand Traffic

        ↓

PHASE 2
Monitor Traffic

        ↓

PHASE 3
Investigate Events

        ↓

PHASE 4
Measure Interventions

        ↓

PHASE 5
Understand Structural Mobility Problems

        ↓

PHASE 6
Support City-Level Mobility Decisions
```

The first objective is not to solve traffic.

The first objective is to create a reliable and explainable understanding of traffic behaviour.

Once that intelligence layer exists, the system can eventually integrate additional data sources and support more sophisticated intervention analysis.

---

# Final Positioning Statement

> **Google Maps helps people see traffic.**
>
> **SARGVISION Traffic Intelligence Copilot helps city authorities understand what the traffic means.**

The MVP should demonstrate that SARGVISION can take available traffic observations, combine them with city-specific historical context, detect unusual conditions, investigate patterns and present evidence-grounded intelligence through an AI Copilot.

That is the product to build first.
