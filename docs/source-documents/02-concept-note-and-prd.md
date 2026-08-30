# SARGVISION TRAFFIC INTELLIGENCE COPILOT
## An AI-Powered Traffic Intelligence Platform for Siliguri

### Project Vision, Concept Note and Product Requirements Document

**Prepared by:** SARGVISION Intelligence Pvt. Ltd.  
**Pilot Geography:** Siliguri Metropolitan Area  
**Technology Foundation:** Google Maps Platform, Google Cloud Platform and Agentic AI  
**Document Version:** 1.0

---

# 1. Executive Summary

Siliguri is one of the most strategically important cities in Eastern India. As the gateway to North Bengal, the Northeast, Sikkim, Bhutan and neighbouring international corridors, the city experiences a complex and continuously changing pattern of urban mobility.

Every day, thousands of vehicles move through key corridors connecting commercial areas, residential zones, railway stations, highways, educational institutions, hospitals and surrounding towns.

Traffic management teams face a difficult challenge:

They need to understand what is happening across the city, identify unusual congestion quickly, distinguish between normal daily traffic and exceptional events, and deploy attention and resources where they are needed most.

Today, much of this understanding depends on:

- field observation;
- CCTV monitoring;
- phone calls and manual reports;
- experience of traffic officers;
- public complaints;
- reactive intervention after congestion has already become significant.

At the same time, a large amount of traffic intelligence already exists in digital form.

Platforms such as Google Maps continuously observe traffic movement patterns and estimate travel times across the road network. However, raw traffic information alone does not solve the operational problem.

A red road on a map does not automatically answer:

- Is this congestion unusual?
- How severe is it compared with normal conditions?
- How long has it been occurring?
- Does this happen every day?
- Is the congestion spreading to adjacent corridors?
- Which areas require immediate attention?
- Is traffic behaviour improving or deteriorating over time?

The proposed solution addresses this gap.

# SARGVISION Traffic Intelligence Copilot

is an AI-powered decision-support platform designed to help traffic management authorities understand and monitor how traffic behaves across selected strategic corridors in Siliguri.

The system will use Google Maps traffic data to continuously build a historical understanding of traffic behaviour.

Over time, it will learn the difference between:

> **Normal traffic patterns**

and

> **Potentially unusual traffic conditions requiring human attention.**

The platform will provide a live operational dashboard, historical traffic analytics, anomaly detection and an AI Copilot that allows officers to investigate traffic conditions using natural language.

The fundamental purpose of the system is simple:

> **Move from seeing traffic to understanding traffic.**

---

# 2. The Core Problem

Traffic management is inherently dynamic.

A road that is congested at 6 PM may be operating completely normally if that congestion occurs every day during peak hours.

However, the same road experiencing similar congestion at 11 AM may represent an unusual event.

Therefore, traffic management cannot rely only on the question:

> “Is there traffic?”

The more important question is:

> “Is the current traffic behaviour different from what we normally expect?”

This distinction requires historical context.

For example:

### Scenario A

Sevoke Road is congested at 6:00 PM.

Historical analysis shows that similar congestion occurs almost every weekday between 5:30 PM and 8:00 PM.

The system may classify this as:

> Expected peak-hour congestion.

---

### Scenario B

Sevoke Road becomes heavily congested at 11:00 AM.

Historical data shows that traffic during this period is normally moderate.

The congestion persists for 30 minutes and travel time increases significantly.

The system may classify this as:

> Unusual traffic condition requiring investigation.

This ability to compare **current conditions against historical expectations** is the foundation of the proposed system.

---

# 3. Why Siliguri?

Siliguri presents a strong opportunity for a focused traffic intelligence pilot.

The city has several characteristics that make intelligent traffic monitoring valuable:

- rapid urban expansion;
- increasing vehicle density;
- strategic national and regional connectivity;
- high commercial activity;
- major railway and transport nodes;
- movement towards Darjeeling, Sikkim and the Northeast;
- multiple critical road corridors;
- seasonal and tourism-related traffic fluctuations;
- festival-related traffic events;
- complex interaction between local and through traffic.

At the same time, Siliguri is not a city where the first step should necessarily be an expensive smart-city infrastructure project involving:

- thousands of IoT sensors;
- new city-wide CCTV infrastructure;
- expensive traffic signal replacements;
- proprietary traffic management systems;
- large digital twin implementations.

The proposed approach is intentionally different.

# Start with intelligence.

Use infrastructure and data that are already available.

Build a practical AI layer on top.

Demonstrate measurable value.

Then expand based on real operational requirements.

---

# 4. Project Vision

The long-term vision is to create:

> **An AI-powered operational intelligence layer for urban traffic management in Siliguri.**

The platform should continuously answer four questions.

## 1. What is happening now?

The system continuously monitors selected traffic corridors and identifies their current traffic condition.

---

## 2. Is this normal?

The system compares current traffic behaviour against historical patterns.

---

## 3. What has changed?

The system detects unusual increases in travel time, persistent congestion and changes in traffic patterns.

---

## 4. Where should human attention go?

The system prioritises areas where unusual traffic conditions may require investigation or operational attention.

---

# 5. Product Philosophy

The proposed system is not intended to replace:

- traffic police;
- traffic engineers;
- field officers;
- existing traffic management systems;
- CCTV infrastructure;
- human decision-making.

Instead, it is designed as a:

# Traffic Intelligence Copilot

The system assists human operators by continuously analysing data and bringing meaningful information to their attention.

The human officer remains the decision-maker.

The AI system acts as an intelligence assistant.

---

# 6. Product Positioning

## What Google Maps Does

Google Maps provides highly valuable mobility and traffic information.

It can help estimate:

- travel duration;
- traffic-aware travel duration;
- route alternatives;
- traffic conditions along routes.

However, Google Maps is primarily designed as a navigation platform.

It does not provide Siliguri traffic authorities with a dedicated operational intelligence system that:

- builds a customised historical memory of selected city corridors;
- defines expected traffic behaviour;
- detects abnormal patterns;
- prioritises traffic events;
- analyses recurring congestion;
- compares corridor performance;
- creates daily operational intelligence;
- allows officers to ask questions about city traffic through an AI Copilot.

This is where SARGVISION adds value.

---

# 7. The SARGVISION Value Layer

The proposed architecture can be understood as follows:

```text
GOOGLE MAPS
     │
     ▼
TRAFFIC DATA
     │
     ▼
SARGVISION DATA COLLECTION
     │
     ▼
HISTORICAL TRAFFIC MEMORY
     │
     ▼
TRAFFIC ANALYTICS
     │
     ├──────────────────┐
     ▼                  ▼
ANOMALY DETECTION   PATTERN ANALYSIS
     │                  │
     └────────┬─────────┘
              │
              ▼
      TRAFFIC INTELLIGENCE
              │
              ▼
        AI COPILOT
              │
              ▼
      HUMAN DECISION MAKER
```

The fundamental distinction is:

> Google Maps helps users see traffic.

> SARGVISION helps city authorities understand traffic.

---

# 8. Proposed MVP

The recommended first phase is a focused Minimum Viable Product.

The objective is not to digitise the entire traffic management ecosystem.

The objective is to demonstrate that an AI-powered intelligence layer can generate meaningful operational insights using available data sources.

The MVP should focus on:

## 1. Selected Strategic Corridors

Initially, approximately 10–20 important corridors should be selected in consultation with Siliguri Traffic Police.

Potential categories include:

- major commercial corridors;
- railway connectivity corridors;
- high-density urban roads;
- critical intersections;
- hospital access corridors;
- tourism movement corridors;
- frequently congested roads.

The exact corridors should be determined jointly during the project discovery phase.

---

# 9. Core MVP Capabilities

The MVP will consist of six major capabilities.

---

# Capability 1: Traffic Data Collection

The system periodically collects traffic-aware travel information for selected corridors.

Each observation may include:

- timestamp;
- corridor;
- route distance;
- normal estimated travel duration;
- current traffic-aware travel duration;
- estimated delay;
- delay percentage.

Example:

```text
CORRIDOR
Sevoke Road

TIME
5:30 PM

EXPECTED TRAVEL TIME
15 minutes

CURRENT TRAVEL TIME
24 minutes

ESTIMATED DELAY
9 minutes

TRAFFIC IMPACT
+60%
```

Each observation becomes part of the city's traffic intelligence history.

---

# Capability 2: Historical Traffic Memory

Over time, the system builds a historical understanding of traffic behaviour.

For example:

```text
SEVOKE ROAD

MONDAY

5:00 PM – 6:00 PM

Historical Median Travel Time:
18 minutes

Typical Range:
15 – 22 minutes

High Congestion Range:
22 – 28 minutes

Severe Congestion:
Above 28 minutes
```

This allows the system to understand context.

Instead of simply saying:

> Traffic is heavy.

The system can say:

> Current travel time is 62% above the historical median for this corridor and time period.

That is a much more meaningful operational insight.

---

# Capability 3: Traffic Anomaly Detection

The system identifies traffic conditions that are significantly different from expected historical behaviour.

The system will consider:

- current travel time;
- expected travel time;
- historical variation;
- time of day;
- day of week;
- persistence of the condition.

For example:

```text
CURRENT TRAVEL TIME

30 minutes

EXPECTED TRAVEL TIME

18 minutes

DEVIATION

+67%

DURATION

25 minutes
```

The system may classify this as:

> HIGH PRIORITY TRAFFIC ANOMALY

Importantly, the system should avoid unnecessary alerts.

A single abnormal data point should not immediately create an operational event.

The abnormal condition must persist.

---

# Capability 4: Traffic Event Detection

Consecutive abnormal observations are grouped into a single traffic event.

Example:

```text
5:00 PM
High Congestion

5:05 PM
High Congestion

5:10 PM
High Congestion

5:15 PM
High Congestion
```

Instead of generating four separate alerts, the system creates:

```text
TRAFFIC EVENT

CORRIDOR
Sevoke Road

STARTED
5:00 PM

DURATION
15 Minutes

SEVERITY
High

STATUS
Active
```

This makes the system operationally useful rather than noisy.

---

# Capability 5: Traffic Pattern Intelligence

The system analyses historical traffic behaviour to identify recurring patterns.

Example:

```text
HILL CART ROAD

RECURRING PATTERN DETECTED

Weekdays

5:30 PM – 7:30 PM

Observed On

16 of the last 20 comparable days

Average Delay

47%
```

This information helps authorities understand:

- predictable congestion periods;
- unreliable corridors;
- changing traffic behaviour;
- emerging traffic patterns.

---

# Capability 6: AI Traffic Copilot

The AI Copilot is the primary intelligence interface.

Traffic officers should not need to manually analyse charts every time they have a question.

Instead, they should be able to ask:

> What requires my attention right now?

Or:

> Why is Sevoke Road congested?

Or:

> Is this congestion normal?

Or:

> Which corridor experienced the highest delays today?

Or:

> What time does Hill Cart Road usually become congested?

The AI Copilot will use authorised data tools to retrieve evidence and generate an understandable answer.

---

# 10. Example User Experience

An officer opens the system.

The dashboard displays:

# SILIGURI TRAFFIC PULSE

### Current City Status

```text
🟢 NORMAL CORRIDORS
12

🟡 ELEVATED CORRIDORS
4

🟠 HIGH PRIORITY
2

🔴 CRITICAL EVENT
1
```

---

### Top Priority

```text
SEVOKE ROAD

Current travel time is

62% above expected

Condition duration

35 minutes

STATUS

HIGH PRIORITY
```

The officer clicks:

> Investigate

The system displays:

```text
CURRENT CONDITION

Travel Time
26 minutes

Expected
16 minutes

Deviation
+62%

Duration
35 minutes
```

The officer then asks the AI Copilot:

> Is this unusual?

The AI responds:

> Yes. Current travel time is approximately 62% above the historical median for comparable weekdays and time periods. The condition has persisted for more than 30 minutes. Similar congestion was observed less frequently during the previous four weeks.

The officer now has context.

---

# 11. AI Copilot Architecture

The AI Copilot should not directly invent traffic insights.

It must operate through a controlled, evidence-based architecture.

```text
USER QUESTION
      │
      ▼
AI COPILOT
      │
      ▼
QUESTION UNDERSTANDING
      │
      ▼
TOOL SELECTION
      │
      ├─────────────────────┐
      │                     │
      ▼                     ▼
CURRENT DATA          HISTORICAL DATA
      │                     │
      ├──────────┬──────────┘
                 │
                 ▼
          ANALYTICS TOOLS
                 │
                 ▼
          EVIDENCE LAYER
                 │
                 ▼
          GEMINI RESPONSE
                 │
                 ▼
               USER
```

The AI must distinguish between:

### Observed facts

For example:

> Travel time increased by 62%.

### Statistical interpretation

For example:

> The condition is unusual compared with historical behaviour.

### Hypothesis

For example:

> The pattern may indicate a local disruption or increased traffic demand.

The system must not present hypotheses as facts.

---

# 12. Recommended AI Agent Model

For the MVP, SARGVISION should avoid unnecessary complexity.

Instead of deploying many autonomous agents, the system should use:

# One AI Orchestrator

supported by specialised analytical tools.

Conceptually, the system can contain four intelligence capabilities.

---

## Traffic Analyst

Responsible for:

- current traffic conditions;
- corridor comparison;
- anomaly investigation.

---

## Historical Analyst

Responsible for:

- historical patterns;
- recurring congestion;
- trend comparison.

---

## Network Analyst

Responsible for:

- relationships between connected corridors;
- possible congestion propagation;
- time-lag analysis.

---

## Traffic Copilot

Responsible for:

- understanding user questions;
- selecting analytical tools;
- combining evidence;
- generating responses.

---

# 13. Example AI Copilot Investigation

### User Question

> Why is Sevoke Road currently congested?

The system should not immediately generate an answer.

Instead:

```text
USER QUESTION
        │
        ▼
UNDERSTAND INTENT
        │
        ▼
INVESTIGATE CURRENT CONDITION
        │
        ├───────────────┐
        ▼               ▼
CURRENT TRAFFIC    HISTORICAL BASELINE
        │               │
        └───────┬───────┘
                │
                ▼
ANALYSE DEVIATION
                │
                ▼
CHECK ADJACENT CORRIDORS
                │
                ▼
GENERATE EVIDENCE-BASED RESPONSE
```

Example response:

> Sevoke Road is currently experiencing significantly higher travel times than expected for this time period. The abnormal condition began approximately 30 minutes ago and has persisted. Two connected corridors are also showing elevated travel times. The available data indicates an unusual traffic pattern; however, the current data alone cannot determine the exact physical cause. Field verification may be required.

This is operationally responsible.

---

# 14. Adjacent Corridor Intelligence

Traffic congestion does not always remain isolated.

A problem on one corridor may affect nearby roads.

The MVP should therefore analyse relationships between selected connected corridors.

Example:

```text
CORRIDOR A

Congestion begins
5:00 PM

        ↓

CORRIDOR B

Congestion begins
5:12 PM

        ↓

CORRIDOR C

Congestion begins
5:25 PM
```

If similar timing relationships occur repeatedly, the system may identify:

> A repeated temporal traffic relationship.

The system must avoid claiming direct causation unless validated by additional data.

Therefore, the system should use language such as:

- possible congestion propagation;
- recurring temporal relationship;
- correlated traffic behaviour.

---

# 15. Daily Traffic Intelligence Brief

The platform should automatically generate a concise daily operational summary.

Example:

# SILIGURI DAILY TRAFFIC BRIEF

## Previous Day Summary

- 4 significant traffic events detected.
- Highest recorded delay occurred on Sevoke Road.
- Hill Cart Road showed recurring evening congestion.
- Average travel time across monitored corridors increased during the evening peak.

---

## Areas Requiring Attention

```text
SEVOKE ROAD

Repeated high congestion
between

5:00 PM – 7:30 PM
```

---

## Historical Observation

```text
NJP CORRIDOR

Traffic began increasing

30 minutes earlier

than the normal evening pattern.
```

---

## Suggested Monitoring Period

```text
Morning

8:00 AM – 10:00 AM

Evening

5:00 PM – 8:00 PM
```

The purpose of this report is not to issue instructions.

It is to provide structured situational awareness.

---

# 16. Traffic Reliability Index

The system should calculate a corridor-level reliability score.

The objective is to identify roads where travel times are highly unpredictable.

For example:

```text
SEVOKE ROAD

TRAFFIC RELIABILITY

58 / 100

STATUS

LOW RELIABILITY
```

The score may consider:

- average delay;
- travel time variability;
- frequency of severe congestion;
- duration of congestion events.

This creates a useful planning metric.

A road may not always be congested.

However, if travel time is highly unpredictable, it can still be operationally important.

---

# 17. Recommended Technology Architecture

The MVP should use a pragmatic cloud-native architecture.

```text
                         USERS
                           │
                           ▼
                    WEB APPLICATION
                      NEXT.JS
                           │
                           ▼
                     API SERVICES
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
      TRAFFIC SERVICE  ANALYTICS     AI COPILOT
             │             │             │
             └─────────────┼─────────────┘
                           │
                           ▼
                    DATA PLATFORM
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
         PostgreSQL      BigQuery       Redis
          + PostGIS
             │
             ▼
      GOOGLE MAPS PLATFORM
```

---

# 18. Recommended Google Cloud Architecture

```text
CLOUD SCHEDULER
       │
       ▼
TRAFFIC COLLECTION SERVICE
       │
       ▼
GOOGLE MAPS ROUTES API
       │
       ▼
RAW TRAFFIC OBSERVATIONS
       │
       ▼
POSTGRESQL / BIGQUERY
       │
       ▼
ANALYTICS ENGINE
       │
       ├──────────────────┐
       ▼                  ▼
BASELINE ENGINE      EVENT ENGINE
       │                  │
       └─────────┬────────┘
                 │
                 ▼
           TRAFFIC API
                 │
                 ▼
            AI COPILOT
                 │
                 ▼
        GEMINI / VERTEX AI
                 │
                 ▼
             WEB UI
```

---

# 19. Core Data Model

The platform should maintain the following major entities.

## Corridors

```text
corridor_id
name
city
origin
destination
priority
monitoring_frequency
active_status
```

---

## Traffic Observations

```text
observation_id
timestamp
corridor_id
distance
static_duration
traffic_duration
delay_seconds
delay_percentage
```

---

## Traffic Events

```text
event_id
corridor_id
start_time
end_time
severity
maximum_delay
event_status
```

---

## Historical Baselines

```text
baseline_id
corridor_id
day_of_week
time_window
median_duration
p25
p75
p90
sample_size
```

---

## Anomalies

```text
anomaly_id
corridor_id
timestamp
anomaly_score
severity
confidence
```

---

# 20. Anomaly Detection Approach

The first version should prioritise:

# Explainability over complexity.

The system does not initially require advanced deep-learning models.

A robust statistical approach is recommended.

### Step 1

Determine expected traffic behaviour.

Example:

```text
Historical Median

18 minutes
```

### Step 2

Measure current traffic.

```text
Current Travel Time

30 minutes
```

### Step 3

Calculate deviation.

```text
Deviation

=

30 - 18

=

12 minutes
```

### Step 4

Calculate percentage deviation.

```text
12 / 18 × 100

=

66.7%
```

### Step 5

Measure persistence.

```text
Abnormal for

5 minutes
→ Monitor

Abnormal for

20 minutes
→ Event

Abnormal for

45 minutes
→ High Priority
```

This approach is transparent and easy for officers and stakeholders to understand.

---

# 21. Adaptive Data Collection

API usage must be managed carefully.

The system should not continuously poll every corridor at the highest frequency.

Instead:

```text
NORMAL

15-minute interval

       ↓

ELEVATED

10-minute interval

       ↓

ANOMALOUS

5-minute interval
```

Critical corridors may be monitored more frequently during known peak periods.

This creates a balance between:

- data quality;
- operational usefulness;
- API cost.

---

# 22. User Roles

## System Administrator

Can:

- configure corridors;
- manage thresholds;
- manage users;
- configure monitoring schedules.

---

## Traffic Officer

Can:

- view live traffic intelligence;
- investigate events;
- view corridor information;
- interact with AI Copilot.

---

## Senior Officer

Can:

- view city-wide analytics;
- compare historical performance;
- access reports;
- review long-term patterns.

---

# 23. MVP User Interface

The MVP should focus on four primary interfaces.

---

## Screen 1: Traffic Pulse

The operational homepage.

Displays:

- overall traffic condition;
- active events;
- priority corridors;
- emerging anomalies.

---

## Screen 2: Live Traffic Map

Displays:

- monitored corridors;
- current traffic status;
- active events;
- severity indicators.

---

## Screen 3: Corridor Intelligence

Displays:

- current travel time;
- expected travel time;
- historical patterns;
- recurring congestion;
- active events;
- reliability score.

---

## Screen 4: AI Traffic Copilot

Allows officers to ask questions such as:

> What needs attention right now?

> Which corridor is performing worse than usual?

> Is today's traffic worse than last Monday?

> Show me recurring congestion patterns.

> Which roads have become less reliable this month?

---

# 24. Recommended Project Phases

## Phase 0 — Discovery and Corridor Selection

### Duration

1–2 Weeks

Activities:

- stakeholder discussions;
- identification of pilot corridors;
- identification of key traffic challenges;
- selection of success metrics.

---

## Phase 1 — Traffic Data Foundation

### Duration

2 Weeks

Deliverables:

- corridor configuration system;
- Google Maps integration;
- traffic data collector;
- database infrastructure.

---

## Phase 2 — Intelligence Engine

### Duration

2–3 Weeks

Deliverables:

- historical baseline engine;
- anomaly detection;
- traffic event detection;
- pattern analytics.

---

## Phase 3 — Operations Dashboard

### Duration

2 Weeks

Deliverables:

- Traffic Pulse;
- live map;
- corridor intelligence pages;
- event prioritisation.

---

## Phase 4 — AI Copilot

### Duration

2 Weeks

Deliverables:

- Gemini integration;
- analytical tools;
- AI orchestration;
- evidence-based responses.

---

## Phase 5 — Pilot Validation

### Duration

4 Weeks

Activities:

- collect officer feedback;
- validate anomaly detection;
- refine thresholds;
- evaluate usefulness;
- identify Phase 2 opportunities.

---

# 25. What We Will Not Build in the First MVP

To ensure successful execution, the MVP should deliberately avoid excessive scope.

The following should not be included initially:

- direct traffic signal control;
- automatic signal optimisation;
- traffic light controller integration;
- autonomous intervention;
- city-wide CCTV analytics;
- expensive IoT infrastructure;
- full digital twin;
- reinforcement learning traffic optimisation.

These can become future modules.

The first objective is:

> Build a reliable traffic intelligence foundation.

---

# 26. Future Product Roadmap

Once the MVP is validated, the platform can evolve.

## Phase 2

### Multi-Source Traffic Intelligence

Integrate:

- police reports;
- road closures;
- planned events;
- festivals;
- weather conditions;
- public complaints.

---

## Phase 3

### Computer Vision

Integrate CCTV intelligence.

Potential capabilities:

- vehicle counting;
- queue length estimation;
- abnormal traffic behaviour;
- intersection occupancy.

---

## Phase 4

### Intervention Intelligence

The platform may eventually support:

```text
TRAFFIC PROBLEM
      │
      ▼
PATTERN ANALYSIS
      │
      ▼
POSSIBLE INTERVENTION
      │
      ▼
HUMAN REVIEW
      │
      ▼
IMPLEMENTATION
      │
      ▼
OUTCOME MONITORING
```

---

## Phase 5

### Traffic Signal Intelligence

Only after reliable data access and operational collaboration, the platform may investigate:

- signal timing analysis;
- intersection coordination;
- green split evaluation;
- congestion propagation;
- potential timing recommendations.

Human traffic engineers must remain responsible for signal decisions.

---

# 27. Project Success Metrics

The MVP should be evaluated based on practical usefulness.

## Technical Metrics

### Traffic Data Availability

Target:

> Greater than 95%

---

### Successful Observation Collection

Target:

> Greater than 95%

---

### Dashboard Availability

Target:

> Greater than 99%

during pilot operation.

---

## Intelligence Metrics

### Useful Anomaly Detection

Target:

> At least 70% of significant alerts considered operationally useful during pilot validation.

---

### AI Answer Grounding

Target:

> More than 95% of responses should be supported by available system data.

---

## Operational Value

The most important success question is:

> Did the platform help traffic officers identify, understand or investigate traffic conditions faster than existing manual methods?

---

# 28. Why This Project is Feasible

The proposed MVP is deliberately designed around existing capabilities.

SARGVISION already has access to and expertise around:

- Google Cloud Platform;
- Google Maps APIs;
- Generative AI;
- Agentic AI;
- cloud-native architectures;
- data engineering;
- AI application development.

Therefore, the first version does not require major new infrastructure investment.

The architecture can be developed incrementally.

---

# 29. Strategic Value for Siliguri

The project creates an opportunity for Siliguri to experiment with a practical model of:

# AI-Assisted Urban Operations

Instead of beginning with a large infrastructure-heavy smart-city programme, the city can begin with a focused intelligence pilot.

The model is:

```text
START SMALL

        ↓

SELECT CRITICAL CORRIDORS

        ↓

COLLECT DATA

        ↓

BUILD HISTORICAL INTELLIGENCE

        ↓

IDENTIFY PATTERNS

        ↓

ASSIST HUMAN OPERATORS

        ↓

MEASURE VALUE

        ↓

EXPAND RESPONSIBLY
```

This reduces financial risk.

It also ensures that future investments are driven by demonstrated operational value rather than technology adoption alone.

---

# 30. The Long-Term Vision

The proposed MVP is the first building block of a broader Urban Intelligence Platform.

Over time, Siliguri could develop an AI-enabled operational intelligence layer that helps authorities understand:

- traffic;
- mobility;
- incidents;
- congestion;
- public events;
- urban movement patterns.

The vision is not to create an automated city.

The vision is to create:

> **A better-informed city.**

---

# 31. Final Product Statement

# SARGVISION Traffic Intelligence Copilot

is an AI-powered decision-support platform designed to continuously observe, remember and analyse traffic behaviour across selected corridors in Siliguri.

Using traffic data from Google Maps Platform, cloud-based analytics and Agentic AI, the platform will:

- monitor traffic conditions;
- build historical traffic memory;
- identify unusual congestion;
- detect persistent traffic events;
- analyse recurring patterns;
- compare corridor performance;
- prioritise areas requiring attention;
- provide daily traffic intelligence;
- enable officers to investigate traffic through a natural-language AI Copilot.

The platform does not replace traffic officers.

It does not replace traffic engineers.

It does not autonomously control traffic infrastructure.

Instead:

> **It gives the people responsible for managing traffic a continuously learning intelligence layer that helps them understand what is happening, what is unusual and where attention may be required.**

---

# 32. The Core Vision in One Sentence

> **SARGVISION Traffic Intelligence Copilot transforms raw traffic data into operational intelligence for a smarter, more responsive Siliguri.**

---

# 33. Immediate Recommended Next Step

The recommended first engagement should be a:

# 90-Day Siliguri Traffic Intelligence Pilot

### Phase 1

Select 10–20 strategic corridors.

### Phase 2

Collect and analyse traffic data.

### Phase 3

Build the historical traffic baseline.

### Phase 4

Deploy anomaly detection.

### Phase 5

Launch the Traffic Intelligence Dashboard.

### Phase 6

Introduce the AI Traffic Copilot.

### Phase 7

Validate findings with traffic authorities.

---

# 34. Closing Statement

Siliguri does not need to wait for expensive infrastructure transformation before beginning its journey towards AI-enabled urban intelligence.

A meaningful first step can begin with the data and technology already available.

By combining:

- Google Maps traffic intelligence;
- Google Cloud infrastructure;
- historical analytics;
- explainable anomaly detection;
- Agentic AI;
- human operational expertise,

Siliguri can explore a practical, scalable and cost-conscious approach to traffic intelligence.

The proposed MVP is designed not as a technology demonstration, but as a real operational experiment.

Its purpose is straightforward:

> **Help the city understand its traffic better today, so that it can make better mobility decisions tomorrow.**