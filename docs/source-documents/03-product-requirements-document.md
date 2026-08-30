# SARGVISION TRAFFIC COPILOT
## Product Requirements Document (PRD)

**Product:** SARGVISION Traffic Copilot  
**Version:** 1.0  
**Status:** Proposed MVP  
**Pilot City:** Siliguri, West Bengal  
**Primary Organization:** SARGVISION Intelligence  
**Primary Users:** Siliguri Traffic Police and Traffic Operations Personnel  
**Product Category:** AI-Powered Traffic Operations Intelligence  
**Deployment Model:** Cloud-Native, Software-First  
**Target MVP Timeline:** 8 Weeks

---

# 1. Product Overview

## 1.1 Product Name

**SARGVISION Traffic Copilot**

## 1.2 Product Vision

SARGVISION Traffic Copilot is an AI-powered traffic operations intelligence platform designed to help traffic authorities understand traffic conditions across selected urban corridors.

The system combines:

- traffic-aware route information;
- continuous travel-time observations;
- historical traffic patterns;
- anomaly detection;
- corridor intelligence;
- bottleneck analysis;
- Agentic AI.

The primary objective is to answer:

> **What requires attention, why does it require attention, and what should the officer investigate next?**

---

# 2. Problem Statement

Traffic management teams frequently operate with fragmented information.

Existing sources may include:

```text
CCTV

Field Officers

Manual Reports

Google Maps

Phone Calls

WhatsApp Groups

Public Complaints
```

These sources are useful individually.

However, they create several challenges.

---

## 2.1 Lack of Unified Situational Awareness

Officers may need to manually determine:

- which roads are congested;
- whether congestion is unusual;
- which congestion is most important;
- where problems are spreading.

---

## 2.2 Lack of Historical Context

Raw traffic information does not answer:

> Is this traffic condition expected?

Example:

```text
Current Travel Time:
25 minutes
```

This number alone has limited meaning.

However:

```text
Current Travel Time:
25 minutes

Expected Travel Time:
14 minutes

Deviation:
+78%
```

This is operational intelligence.

---

## 2.3 Reactive Operations

Traffic problems are often addressed after they become visible.

The proposed system aims to identify:

```text
Unexpected Pattern
      ↓
Early Detection
      ↓
Priority Alert
      ↓
Human Investigation
```

---

## 2.4 Limited Human Attention

Traffic personnel cannot continuously monitor every corridor.

Therefore, the system should optimize for:

# Attention Prioritization

The objective is not to display all available information.

The objective is to surface the information most likely to require attention.

---

# 3. Product Goals

## Primary Goals

### Goal 1

Provide a real-time and historical traffic intelligence view for selected Siliguri corridors.

### Goal 2

Detect abnormal traffic patterns.

### Goal 3

Identify recurring congestion and probable bottleneck zones.

### Goal 4

Provide an AI Copilot interface for traffic investigation.

### Goal 5

Generate daily operational traffic intelligence.

---

# 4. Non-Goals for MVP

The following capabilities are explicitly excluded from Version 1.

```text
Autonomous Traffic Signal Control

Signal Controller Integration

Automatic Signal Timing Changes

Digital Twin

Reinforcement Learning Traffic Control

City-Wide CCTV Processing

Automated Traffic Enforcement

Facial Recognition

Vehicle Identification

License Plate Recognition

Citizen Navigation Application
```

These exclusions are intentional.

The MVP must remain:

- low-cost;
- low-risk;
- software-first;
- fast to deploy.

---

# 5. Target Users

## Persona 1 — Commissioner / Senior Traffic Leadership

### Needs

- city-level overview;
- priority problems;
- historical trends;
- daily briefing;
- strategic insights.

### Typical Questions

> What are the most problematic corridors?

> Has congestion improved this month?

> Which locations require intervention?

---

## Persona 2 — Traffic Control Room Officer

### Needs

- current situation;
- priority alerts;
- unusual congestion;
- corridor comparison.

### Typical Questions

> What requires attention now?

> Which corridor is deteriorating?

> Is this congestion normal?

---

## Persona 3 — Traffic Analyst

### Needs

- historical data;
- pattern analysis;
- congestion trends;
- reliability analysis.

### Typical Questions

> Compare traffic on Fridays versus Mondays.

> What are the recurring evening bottlenecks?

---

# 6. Strategic Product Modules

The platform consists of five conceptual intelligence products.

The MVP will implement three.

---

## Module A — Traffic Incident Intelligence

### MVP Status

Included.

### Objective

Detect traffic conditions that significantly deviate from expected historical behaviour.

---

### Inputs

- current travel time;
- historical travel time;
- route metadata;
- time;
- day of week.

---

### Outputs

```text
Anomaly Score

Severity

Affected Corridor

Deviation Percentage

Start Time

Duration

Confidence
```

---

### Example

```text
CORRIDOR:
Sevoke Road

CURRENT:
28 minutes

EXPECTED:
16 minutes

DEVIATION:
+75%

ANOMALY SCORE:
0.91

SEVERITY:
HIGH
```

---

## Module B — Bottleneck Intelligence

### MVP Status

Included.

### Objective

Identify recurring congestion zones and probable traffic propagation patterns.

---

### Inputs

- corridor travel time;
- adjacent corridor data;
- historical observations;
- temporal correlations.

---

### Outputs

```text
Probable Bottleneck Zone

Recurring Time Window

Affected Corridors

Propagation Pattern

Confidence Score
```

---

## Module C — Mixed Traffic Intelligence

### MVP Status

Future Phase.

### Objective

Use computer vision to understand physical traffic behaviour.

---

### Future Detection Types

- vehicle classification;
- Toto clustering;
- bus obstruction;
- illegal parking;
- lane blockage;
- wrong-way movement.

---

## Module D — Traffic Operations Copilot

### MVP Status

Included.

### Objective

Provide natural language access to traffic intelligence.

---

## Module E — Mobility Decision Intelligence

### MVP Status

Future Phase.

### Objective

Support strategic mobility and infrastructure decisions.

---

# 7. MVP Scope

The initial deployment should monitor:

# 10–15 Strategic Traffic Corridors

Each corridor will consist of:

```text
Origin
   ↓
Destination
   ↓
Optional Intermediate Waypoints
```

---

# 8. Corridor Configuration

Example conceptual structure:

```json
{
  "corridor_id": "SIL_001",
  "name": "Sevoke Road Corridor",
  "origin": {
    "latitude": 26.xxxx,
    "longitude": 88.xxxx
  },
  "destination": {
    "latitude": 26.xxxx,
    "longitude": 88.xxxx
  },
  "priority": "CRITICAL",
  "monitoring_interval_minutes": 5
}
```

Final corridor definitions must be validated with Siliguri Traffic Police.

---

# 9. Functional Requirements

# FR-01 — Traffic Data Collection

The system shall collect traffic-aware route information for configured corridors.

---

## Data Fields

```text
timestamp

corridor_id

origin

destination

distance

normal_duration

traffic_duration

delay_duration

delay_percentage
```

---

## Formula

```text
delay_duration

=

traffic_duration

-

normal_duration
```

---

```text
delay_percentage

=

delay_duration
/
normal_duration

× 100
```

---

# FR-02 — Adaptive Monitoring

The system shall support different monitoring frequencies.

Example:

```text
CRITICAL CORRIDOR
Every 5 minutes

HIGH PRIORITY
Every 10 minutes

NORMAL PRIORITY
Every 20–30 minutes
```

Monitoring frequency may increase when an anomaly is detected.

Example:

```text
NORMAL STATE
15 minute polling

        ↓

ANOMALY DETECTED

        ↓

5 minute polling
```

This is required for API cost optimization.

---

# FR-03 — Historical Traffic Baseline

The system shall calculate expected traffic conditions.

Baselines should consider:

```text
Time of Day

Day of Week

Weekend / Weekday

Historical Travel Times
```

Example:

```text
Monday
5:00 PM

Historical Median:
18 minutes

Historical Range:
16–22 minutes
```

---

## Recommended Baseline Algorithm

Initial MVP:

```text
Rolling Median
+
Percentile Bands
```

Example:

```text
Expected:
Median

Normal Range:
P25 – P75

High Congestion:
Above P90
```

More advanced forecasting should not be required initially.

---

# FR-04 — Traffic Anomaly Detection

The system shall identify unexpected deviations.

---

## Proposed Anomaly Score

Conceptually:

```text
Anomaly Score

=

Current Deviation
+
Historical Variance
+
Persistence
+
Spatial Spread
```

Example factors:

### Current Deviation

How much current travel time differs from baseline.

### Persistence

How long abnormal conditions continue.

### Spatial Spread

Whether congestion spreads to connected corridors.

---

## Severity Levels

```text
LOW

MODERATE

HIGH

CRITICAL
```

Example thresholds should initially be configurable.

---

# FR-05 — Corridor Reliability Score

The system shall calculate corridor reliability.

Proposed factors:

```text
Travel Time Variability

+

Frequency of Severe Congestion

+

Average Delay

+

Peak Duration

=

Reliability Score
```

Suggested scale:

```text
0 – 100
```

Where:

```text
90–100
Highly Reliable

70–89
Reliable

50–69
Moderately Unreliable

Below 50
Highly Unreliable
```

The exact formula must be validated during the pilot.

---

# FR-06 — Bottleneck Analysis

The system shall analyze temporal relationships between connected corridors.

The goal is to identify:

```text
Congestion Origin

↓

Propagation

↓

Affected Network
```

---

## Initial Methodology

For MVP:

```text
Time-Series Correlation

+

Lag Analysis

+

Repeated Pattern Detection
```

Example:

```text
Corridor A slowdown

↓

15 minutes later

Corridor B slowdown

↓

10 minutes later

Corridor C slowdown
```

Repeated observations may indicate a propagation pattern.

---

## Important Constraint

The system must describe results as:

> Probable bottleneck zone

unless validated by physical or CCTV evidence.

---

# FR-07 — Traffic Pulse Dashboard

The system shall provide a city-level overview.

Display:

```text
Current Traffic Status

Critical Corridors

High Congestion Corridors

Normal Corridors

Highest Delay

Top Priority Areas
```

---

# FR-08 — Priority Alerts

The system shall generate alerts when:

- anomaly score exceeds threshold;
- severe congestion persists;
- congestion spreads;
- corridor reliability deteriorates.

---

## Alert Schema

```json
{
  "alert_id": "ALT_001",
  "corridor_id": "SIL_001",
  "severity": "HIGH",
  "type": "TRAFFIC_ANOMALY",
  "detected_at": "timestamp",
  "deviation_percentage": 65,
  "confidence": 0.91,
  "status": "ACTIVE"
}
```

---

# FR-09 — Daily Traffic Brief

The system shall generate a daily summary.

The report should include:

```text
Yesterday's Summary

Top Congestion Events

Most Affected Corridors

Recurring Patterns

Today's Expected Risk

Recommended Monitoring Areas
```

---

# FR-10 — AI Traffic Copilot

The system shall provide a conversational interface.

The Copilot must support:

```text
Current Status Queries

Historical Queries

Comparison Queries

Anomaly Investigation

Corridor Analysis

Daily Brief Queries
```

---

# 10. AI Copilot Architecture

The system should not use uncontrolled autonomous agents.

Recommended architecture:

```text
USER
 │
 ▼
COPILOT ORCHESTRATOR
 │
 ├── Intent Classification
 │
 ├── Tool Selection
 │
 ├── Context Assembly
 │
 └── Response Generation
 │
 ▼
SPECIALIZED TOOLS
```

---

# 11. Copilot Tools

## Tool 1

### get_current_traffic_status()

Inputs:

```text
corridor_id
time
```

Outputs:

```text
current_travel_time
normal_travel_time
delay
severity
```

---

## Tool 2

### analyze_historical_pattern()

Inputs:

```text
corridor_id

date_range

time_range
```

Outputs:

```text
average

median

variance

peak_period

trend
```

---

## Tool 3

### detect_traffic_anomaly()

Outputs:

```text
anomaly_score

severity

duration

confidence
```

---

## Tool 4

### compare_corridors()

Inputs:

```text
corridor_list

time_range
```

Outputs:

```text
ranking

delay

reliability
```

---

## Tool 5

### investigate_bottleneck()

Inputs:

```text
corridor_id

time_window
```

Outputs:

```text
probable_origin

affected_corridors

propagation_pattern

confidence
```

---

## Tool 6

### generate_daily_brief()

Outputs:

```text
summary

alerts

risk_areas

patterns

recommendations
```

---

# 12. Agentic AI Design Principles

The Copilot must follow strict principles.

## Principle 1

The LLM does not calculate traffic metrics.

Analytics services calculate metrics.

---

## Principle 2

The LLM does not invent observations.

Every factual claim should be supported by:

- database data;
- analytics output;
- external validated source.

---

## Principle 3

The LLM explains.

Analytics calculates.

```text
ANALYTICS ENGINE
        ↓
Structured Evidence
        ↓
LLM
        ↓
Human Explanation
```

---

## Principle 4

Recommendations must be clearly categorized.

```text
OBSERVATION

INFERENCE

RECOMMENDED INVESTIGATION
```

These categories should never be mixed.

---

# 13. System Architecture

```text
                        USERS

                           │

                           ▼

                   NEXT.JS FRONTEND

                           │

                           ▼

                      API GATEWAY

                           │

        ┌──────────────────┼──────────────────┐

        │                  │                  │

        ▼                  ▼                  ▼

TRAFFIC SERVICE      COPILOT SERVICE    ANALYTICS SERVICE

        │                  │                  │

        └──────────────────┼──────────────────┘

                           │

                           ▼

                     DATA PLATFORM

          ┌────────────────┼────────────────┐

          │                │                │

          ▼                ▼                ▼

     CLOUD SQL        BIGQUERY       OBJECT STORAGE

     POSTGRES         ANALYTICS
     + POSTGIS

                           ▲

                           │

                   DATA INGESTION

                           ▲

                           │

                  GOOGLE MAPS APIs
```

---

# 14. Recommended Technology Stack

## Frontend

```text
Next.js

TypeScript

Tailwind CSS

Map Visualization
```

---

## Backend

```text
Python

FastAPI

Pydantic
```

---

## Agent Framework

Recommended:

```text
Google ADK
```

Alternative abstraction layer may be used if required.

---

## LLM

```text
Gemini via Vertex AI
```

---

## Infrastructure

```text
Google Cloud Run
```

---

## Scheduling

```text
Cloud Scheduler
```

---

## Async Processing

```text
Cloud Tasks
or
Pub/Sub
```

---

## Transactional Database

```text
Cloud SQL

PostgreSQL

PostGIS
```

---

## Analytics

```text
BigQuery
```

Optional initially depending on data volume.

---

## Monitoring

```text
Cloud Logging

Cloud Monitoring
```

---

# 15. Data Architecture

## Core Tables

### corridors

```text
corridor_id

name

origin

destination

priority

monitoring_frequency

status
```

---

### traffic_observations

```text
observation_id

timestamp

corridor_id

normal_duration

traffic_duration

delay_duration

delay_percentage

distance

source
```

---

### traffic_baselines

```text
baseline_id

corridor_id

day_type

time_window

median_duration

p25_duration

p75_duration

p90_duration
```

---

### anomalies

```text
anomaly_id

corridor_id

timestamp

anomaly_score

severity

deviation

duration

status
```

---

### bottleneck_patterns

```text
pattern_id

primary_corridor

affected_corridor

time_lag

correlation

frequency

confidence
```

---

### copilot_interactions

```text
interaction_id

user_id

timestamp

query

tools_called

response

evidence_reference
```

---

# 16. Data Collection Strategy

Continuous API polling must be cost-controlled.

Recommended approach:

```text
CRITICAL CORRIDORS

Peak Hours:
Every 5 minutes

Off-Peak:
Every 15 minutes
```

---

```text
STANDARD CORRIDORS

Peak Hours:
Every 10 minutes

Off-Peak:
Every 30 minutes
```

---

# 17. Dynamic Monitoring Strategy

The monitoring engine should adapt.

```text
NORMAL
  │
  ▼
15 Minute Monitoring

ANOMALY
  │
  ▼
5 Minute Monitoring

SEVERE ANOMALY
  │
  ▼
High Priority Monitoring
```

This improves:

- operational awareness;
- API efficiency;
- cloud cost.

---

# 18. Analytics Engine

The Analytics Engine consists of four core components.

---

## 18.1 Baseline Engine

Calculates expected traffic.

Inputs:

```text
Historical Travel Time

Time of Day

Day Type
```

---

## 18.2 Anomaly Engine

Calculates:

```text
Current Observation

vs

Expected Range
```

---

## 18.3 Pattern Engine

Detects:

```text
Recurring Peaks

Recurring Congestion

Day-of-Week Patterns

Travel-Time Trends
```

---

## 18.4 Propagation Engine

Detects potential relationships between corridors.

Example:

```text
A
↓
B
↓
C
```

If repeated time-series relationships are detected, the system records a probable propagation pattern.

---

# 19. Copilot Query Flow

Example query:

> Why is Sevoke Road congested?

System workflow:

```text
1. User submits question

        ↓

2. Copilot identifies intent

        ↓

3. Extract corridor and time context

        ↓

4. Call Current Traffic Tool

        ↓

5. Call Historical Analysis Tool

        ↓

6. Call Anomaly Detection Tool

        ↓

7. Call Connected Corridor Tool

        ↓

8. Assemble Evidence

        ↓

9. Generate Response
```

---

# 20. Response Format

Copilot responses should be structured.

Example:

# Current Observation

Current travel time is 24 minutes.

Expected travel time for this period is approximately 15 minutes.

---

# Historical Context

Current traffic is 60% above the historical median.

---

# Pattern

The congestion began approximately 30 minutes earlier than the normal evening peak.

---

# Impact

Two connected corridors are also experiencing elevated delays.

---

# Recommended Investigation

Physical verification may be required near the probable bottleneck zone.

This format prevents vague AI responses.

---

# 21. Confidence Framework

All intelligence outputs should contain confidence.

Example:

```text
HIGH

MEDIUM

LOW
```

---

## Confidence Sources

```text
Amount of Historical Data

Pattern Consistency

Signal Strength

Data Quality

Spatial Correlation
```

---

# 22. Security Requirements

The MVP should implement:

- authenticated access;
- role-based access;
- audit logging;
- API key management;
- encrypted storage;
- encrypted communication.

---

# 23. Privacy Requirements

The initial MVP should avoid collecting:

```text
Faces

Vehicle Number Plates

Personal Identity Information
```

The initial data model focuses on:

- aggregated travel times;
- corridor performance;
- traffic patterns.

Future CCTV modules must undergo separate privacy and governance review.

---

# 24. Performance Requirements

## Dashboard

Target:

```text
Page Load
< 3 seconds
```

---

## Copilot

Target:

```text
Simple Query
< 5 seconds

Complex Investigation
< 15 seconds
```

---

## Alert Detection

Target:

```text
Within one monitoring interval
```

---

# 25. MVP Success Metrics

## Data Metrics

```text
Data Collection Success Rate

API Failure Rate

Observation Completeness
```

---

## Analytics Metrics

```text
Anomaly Detection Precision

False Positive Rate

Pattern Stability
```

---

## User Metrics

```text
Daily Active Officers

Copilot Queries

Alert Review Rate

Officer Feedback
```

---

## Operational Metrics

```text
Number of Significant Events Detected

Time Saved in Investigation

Recurring Bottlenecks Identified

Priority Areas Investigated
```

---

# 26. MVP Evaluation Framework

The pilot should not be judged based on:

> Did AI solve all traffic problems?

Instead evaluate:

### Question 1

Did the system identify traffic situations officers considered relevant?

### Question 2

Did historical context improve decision-making?

### Question 3

Did anomaly alerts identify unusual traffic conditions?

### Question 4

Did the Copilot reduce investigation effort?

### Question 5

Did the platform identify recurring patterns that were previously undocumented?

---

# 27. Product Roadmap

## Phase 1 — MVP

### Duration

8 weeks.

### Features

```text
Traffic Data Collection

Historical Database

Traffic Pulse

Anomaly Detection

Corridor Analytics

Bottleneck Analysis

Daily Brief

Traffic Copilot
```

---

## Phase 2 — Operational Context

Add:

```text
Road Closures

Manual Incident Input

Police Reports

Events

Festival Calendar
```

---

## Phase 3 — CCTV Intelligence

Pilot:

```text
2–3 Strategic Locations
```

Capabilities:

```text
Vehicle Classification

Queue Detection

Parking Detection

Toto Clustering

Road Obstruction Detection
```

---

## Phase 4 — Root Cause Intelligence

Combine:

```text
Traffic Data

CCTV

Officer Reports

Historical Patterns
```

The AI can then generate stronger evidence-based investigations.

---

## Phase 5 — Mobility Decision Intelligence

Support:

```text
Infrastructure Prioritization

Bottleneck Intervention

Corridor Improvement Analysis

Investment Prioritization
```

---

# 28. Engineering Backlog

## Epic 1 — Corridor Management

### Tasks

- Create corridor data model
- Corridor CRUD APIs
- Map configuration interface
- Priority configuration

---

## Epic 2 — Traffic Data Collection

### Tasks

- Google Maps API integration
- Route request service
- Route Matrix integration
- Scheduler
- Retry mechanism
- Rate limiting
- Cost monitoring

---

## Epic 3 — Historical Analytics

### Tasks

- Observation storage
- Baseline calculation
- Time-series aggregation
- Percentile calculations

---

## Epic 4 — Anomaly Detection

### Tasks

- Deviation calculation
- Severity scoring
- Persistence analysis
- Alert generation

---

## Epic 5 — Bottleneck Intelligence

### Tasks

- Corridor relationship model
- Time-lag analysis
- Correlation engine
- Pattern persistence scoring

---

## Epic 6 — Dashboard

### Tasks

- Traffic Pulse
- Map
- Corridor list
- Alert interface
- Historical charts

---

## Epic 7 — AI Copilot

### Tasks

- Intent recognition
- Tool definitions
- Agent orchestration
- Evidence aggregation
- Response formatting
- Guardrails

---

## Epic 8 — Daily Brief

### Tasks

- Summary engine
- Risk ranking
- Historical comparison
- Automated generation

---

# 29. Eight-Week Implementation Plan

## Week 1

### Foundation

- Finalize corridors
- Configure GCP
- Configure database
- Google Maps integration

---

## Week 2

### Data Collection

- Scheduler
- Route collection
- Data persistence
- Monitoring

---

## Week 3

### Historical Intelligence

- Baseline engine
- Aggregations
- Initial pattern analysis

---

## Week 4

### Anomaly Detection

- Anomaly scoring
- Severity classification
- Alert generation

---

## Week 5

### Dashboard

- Traffic Pulse
- Corridor analysis
- Alert interface

---

## Week 6

### Bottleneck Intelligence

- Corridor relationship model
- Lag analysis
- Pattern visualization

---

## Week 7

### AI Copilot

- Tool integration
- Gemini
- Agent orchestration
- Evidence-based responses

---

## Week 8

### Pilot Validation

- Testing
- Historical validation
- Officer feedback
- Dashboard refinement
- Demonstration preparation

---

# 30. Risks

## Risk 1 — Limited Historical Data

### Mitigation

Start collecting immediately.

Use:

```text
Pilot Data

+

Short-Term Baselines

+

Incremental Learning
```

---

## Risk 2 — Google API Cost

### Mitigation

Use:

- adaptive polling;
- corridor prioritization;
- peak-hour monitoring;
- caching;
- dynamic sampling.

---

## Risk 3 — False Positives

### Mitigation

Use:

- confidence scores;
- persistence requirements;
- human validation.

---

## Risk 4 — AI Hallucination

### Mitigation

Strict tool-based architecture.

The AI cannot generate quantitative claims without data.

---

## Risk 5 — User Adoption

### Mitigation

Focus on one simple question:

> What requires my attention?

Avoid building a complex dashboard.

---

# 31. Product Principles

## Principle 1

Human authority remains central.

---

## Principle 2

AI provides intelligence, not uncontrolled decisions.

---

## Principle 3

Every important insight should be evidence-based.

---

## Principle 4

Start without expensive infrastructure.

---

## Principle 5

Build progressively.

```text
DATA
↓
INSIGHT
↓
TRUST
↓
ACCESS
↓
DEEPER INTELLIGENCE
```

---

# 32. Final Product Definition

# SARGVISION Traffic Copilot

An AI-powered traffic intelligence system that combines traffic data, historical analysis and Agentic AI to help traffic authorities:

> **Know what is happening.**

> **Understand what is unusual.**

> **Identify recurring bottlenecks.**

> **Prioritize attention.**

> **Investigate traffic conditions through natural language.**

---

# 33. MVP Success Definition

The MVP will be considered successful if a Traffic Officer can open the platform and receive a meaningful answer to:

# What requires my attention today?

And then ask:

# Why?

The system should provide an evidence-based explanation using available traffic data.

That is the first step toward a much larger vision:

# Building AI-powered urban mobility intelligence for Indian cities.

---

# Final Product Promise

## Know what is happening.

## Understand what is unusual.

## Investigate intelligently.

## Help humans make better operational decisions.

**SARGVISION TRAFFIC COPILOT**  
### AI-Powered Traffic Intelligence for Siliguri