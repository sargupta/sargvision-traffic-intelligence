# From a board to a command system

*Product direction for the officer-facing console, grounded in how real traffic
command centres and dispatch systems work. This is the plan the `feature/command-system`
branch executes against.*

The board proves the capabilities — it measures the road, confirms an incident,
records an action. It is not yet a **command system**: a shift someone starts and
finishes, a chain of custody from control room to junction and back, and
intelligence no one else in the room could produce. Three research streams
(Indian ATCS/ITMS command centres; international TMCs — London, Singapore, Sydney,
NYC, Netherlands, Seoul; and dispatch-console + multimodal UX) converge on the
same answer for what to add.

## 1. Our lane

Every large console couples three things we deliberately do not have: **signal
hardware** (SCOOT/SCATS/CoSiCoSt adaptive control), **CCTV video-analytics + ANPR
e-challan enforcement**, and a **legal enforcement mandate**. We do not chase any
of them — they need kit and statute, not software.

What those consoles do *manually or badly* is the fourth thing, and it is our
whole product: **measurement, triage, field coordination, and verification as
software.** The honest gap between our board and a real command centre is four
software-only capabilities:

1. **Proactivity** — detect the incident from our own journey-time signal, and
   forecast the recurring ones. (SCATS *Unusual Congestion Monitor*; Bengaluru
   ASTraM's 15-minute congestion alerts.)
2. **Proof** — measure whether the deployment worked, on probe travel-time data.
   *No Indian console verifies a manual deployment* — Pune proves the algorithm,
   nobody proves the officer. NYC's Midtown-in-Motion (~10% travel-time cut) and
   FHWA's before/after method use exactly the data class Google Routes gives us.
3. **Field truth** — live guard status, root-cause capture, and field-originated
   incidents. (CAD self-initiated calls; ASTraM geo-tagged e-attendance.)
4. **Continuity** — an auto-written SBAR handover. Every 24/7 room runs on shift
   logs; none auto-writes them.

## 2. The backbone: one intent layer, three front-ends

The officer must be able to work by **voice, chatbot, or click — their choice, no
dependency on any one.** The way to build that once, not three times, is the model
Apple App Intents proves: define each action once; the surface is only an input
skin; every irreversible commit passes one confirm/readback gate.

```
      VOICE (push-to-talk → STT)   CHAT (NL text)   CLICK (buttons)
                 │                       │              │
             parse + slot-fill      parse + slot-fill   │ (already structured)
                 └──────────┬────────────┘              │
                            ▼                            │
                 ┌──────── IntentEnvelope ───────────────┐
                 │ { action, incidentId?, to?, params,   │
                 │   source, confidence, rawUtterance }  │
                 └───────────────────────────────────────┘
                            ▼
                 VALIDATOR / GROUNDER
                 • action ∈ the fixed verb set
                 • ids resolve to REAL entities (enum-constrained — the
                   parser may only *select* an incident/officer, never mint one)
                 • transition legal for current state (the existing state machine)
                            ▼
        reversible? ─yes→ optimistic execute + Undo toast
              │
              no (resolve / stand-down / reassign) → explicit readback → confirm
                            ▼
                 the ONE existing POST /api/incidents/{id}/{action}
                            ▼
                 append to the timestamped audit log (raw utterance + parsed
                 intent + params + who confirmed)
```

**Rules, each from a cited failure mode:**
- Click emits the envelope directly and never touches the parser — so the console
  is fully usable with voice/LLM offline. This *is* the "no dependency" guarantee.
- Gate only the genuinely irreversible acts (`resolve`, `stand-down`, reassign
  off an active call). Everything else is optimistic + Undo. Confirming everything
  trains click-through. (ATC readback + enterprise dual-lane voice.)
- Grounding is enum-constrained: the parser is handed the live incident list and
  roster as the only allowed values. Wrong-entity binding is the #1 NL failure.
- Voice defaults to **push-to-talk**, not an always-on wake word — a roadside
  control room is noisy, and false-accepts on a commit action are unacceptable.

## 3. Making each surface actionable, not informational

A dashboard tells you what is happening; a command surface lets you resolve it in
place. Concretely, per surface:

- **Board** — each incident card carries a live **countdown timer** and its single
  **next-best action** as one button (state-derived), with the legal transitions
  only. Timer expiry nudges, then **escalates to a supervisor lane** (CAD timed
  alerts — the mechanic that turns a status list into a queue that pressures
  action). Priority-stacked, not chronological.
- **Field** — the guard can **raise an incident**, not only respond to one
  (self-initiated call). Root cause captured from a fixed taxonomy. Live status
  (idle / en-route / on-scene) visible to the control room. One-hand targets,
  optimistic + Undo; `resolve`/`stand-down` still read back.
- **Handover** — not a read-only log: **SBAR** per open item (Situation /
  Background / Assessment / Recommendation) with a claim tick, plus assets down,
  permits in force (diversions, VIP), pending-carried-forward, and a countersigned
  sign-off. Auto-generated from the timeline (ICS-214 activity log), edited, both
  officers sign. Unstructured verbal handovers carry ~3× the error rate.
- **Network** — every junction becomes an **entity with verbs**, not a static row:
  a standing-deployment recommendation derived from chronic congestion × the
  accident record (Venus More: highest accident density, lowest V/C), a link to
  its live state, and a "watch tonight" / "pre-position" action. Plus a **corridor
  time-space ribbon** with the weakest-link junction highlighted (Delhi TraMM),
  instead of 20 isolated dots.

## 4. The verification engine (the differentiator)

On every incident, snapshot the corridor congestion index at each transition —
**detected, acknowledged, on-scene, resolved** — and attribute the change to the
officer and action. This captures the raw material for the "we verify" claim; it
must be captured live, because it cannot be reconstructed later.

The defensible before/after study, as history accumulates (FHWA / INRIX rules):
compare **same weekday, same window, multiple days**; exclude rain/festival/known-
incident days; report **corridor first, then per-leg**; check the gain **persisted**
past day one; check the jam **wasn't just pushed to an adjacent junction**; report
the **reliability delta** (95th-percentile / buffer index), not only the mean; and
attach a significance guardrail so one lucky day can't be overclaimed. When the
delta sits inside normal variability, **report "no measurable effect" honestly** —
that honesty is the differentiator.

Commissioner KPIs, all computable from Routes samples (FHWA formulas): Planning
Time Index, Buffer Index, Travel Time Index, 95th-percentile worst-day time,
frequency of congestion, and the board's own accountability metric — **deployment
effectiveness rate** (% of logged deployments with a statistically real
improvement).

## 5. Build order

Each step is independently shippable and compounds. Verified against the live
system, never a fixture.

1. **Verification foundation** — snapshot the index at every transition; show the
   within-incident effect and time-to-clear now; the ledger and counterfactual as
   baselines accumulate. Cheapest (we already log transitions) and it is the thesis.
2. **The intent layer** — envelope + validator/grounder + deterministic parser;
   the command bar (chat) and voice plumbing on top. Multimodal, offline-safe.
3. **Escalation timers** — due-by per (state, priority); overdue surfaces and
   escalates. Turns the board into a command queue.
4. **Field two-way** — field-originated incidents; cause taxonomy; live guard status.
5. **Auto-handover** — SBAR brief generated from the timeline, with sign-off.
6. **Network actionability** — standing-deployment recommendations; corridor ribbon.
7. **Baselines + auto-detect + forecast** — per-junction time-of-day × day-of-week
   bands; auto-raise on anomaly; pre-position on recurrence. (Needs accumulated
   history; the mechanism ships now and the value accrues.)
8. **Event / bandobast mode** — log a rally/puja/VIP route/closure; pre-assign a
   roster; the board expects those spikes instead of alarming on them.

## 6. Boundary — what we do not build

- **Adaptive signal control**, green-wave, hurry-call, forced-flash — needs signal
  hardware and controllers.
- **CCTV video wall + VIDS + ANPR/RLVD e-challan** — needs a camera network and an
  enforcement mandate. Our auto-detect (step 7) delivers the incident-detection
  benefit from journey time, without cameras.
- **Rebroadcasting Google's raw travel-time or traffic-layer data.** Any public
  advisory publishes *our own computed index* ("SARGVISION-computed"), never
  "Google says" — Maps Platform terms forbid the latter, and it is also the whole
  point of being an independent verifier.

## Sources

Indian: Bengaluru BATCS/ASTraM, Delhi DIMTS TraMM, Hyderabad HTRIMS, Pune ATCS
(delay −30%, ₹4.77 Cr/yr fuel — the one audited-ish adaptive KPI), Kolkata Traffic
Police, Kerala SAFE. International: TfL SITS/SCOOT, LTA i-Transport/EMAS, SCATS
Unusual Congestion Monitor, NYC Midtown-in-Motion (~10%), Rijkswaterstaat
scenario-based management, Seoul TOPIS. Dispatch/multimodal: LEITSC CAD functional
spec (status engine + timed alerts), FAA/ATC readback, deepsense dual-lane voice,
Apple App Intents, SBAR + ICS-214. Full URL list in the branch's research notes.
