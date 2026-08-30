# The Hypothesis — and What the Evidence Says So Far

`status: under test` · Source: [Focus Reset & Critical Validation](source-documents/06-focus-reset-and-critical-validation.md)

---

## What we claim, and what we do not

**We do not claim:** *Siliguri needs Traffic Intelligence.*

**We say:**

> **SARGVISION is exploring whether historical and live mobility data can help Siliguri
> develop a better understanding of recurring traffic patterns and support evidence-based
> traffic operations.**

The Data → Monitoring → Intelligence ladder is a **technology evolution and opportunity
framework** — not a claim that Siliguri unquestionably needs all three tiers.

---

## The hypothesis

> **Siliguri currently has limited structured, historical visibility into city-wide
> mobility patterns, and an intelligence layer combining historical pattern analysis with
> current traffic observations can help traffic authorities identify recurring problems and
> investigate unusual conditions more effectively.**

**It is testable, and it can be proven wrong.** That is what makes it worth having.

It also has **two halves**, and they must be scored separately:

| | Claim | Status |
|---|---|---|
| **A** | …help identify **recurring problems** | 🟢 **Supported so far** |
| **B** | …**investigate unusual conditions** more effectively | 🟡 **Weakened by our own data** |

---

## Half A — recurring problems · supported

The [insight hunt](methodology/insight-hunt.md) found Siliguri's 2019 traffic to be
**highly regular**: the same hour on different weekdays moves by a coefficient of variation
of only **0.02–0.04**, and there is no trend across five months.

**Regularity is what makes recurrence findable.** Concretely, the data yields:

- **no conventional morning peak** — 07:00 runs *below* free-flow; the plateau is 09:00–22:00;
- **the worst hour is 19:00**, not the assumed evening rush;
- **the weekend mirrors the weekday** — same 13-hour plateau, same peak hour, lower
  amplitude. A trade city, not a commuter city;
- **free-flow is only 19.66 km/h** — the roads are slow before any traffic arrives;
- **journey reliability varies 7% to 39%** in required time buffer.

**Three independent local sources agree congestion begins at 9–10am, not 8.** That is a
structured, historical, city-wide pattern statement that did not previously exist — which
is precisely the "limited structured historical visibility" the hypothesis names.

## Half B — unusual conditions · weakened

The same regularity that supports Half A **undermines Half B.**

```
median weekday TTI 1.123 · SD across days 0.026 · CV 0.024
days beyond 2 SD:  5 of 103  (4.9%)
```

**About 95% of days are unremarkable.** If an officer's Tuesday is nearly identical to their
Monday, *"what is unusual today?"* has little to find. Our own alert calibration pointed the
same way: gating at +60% deviation produced roughly **one alert per day city-wide**.

> **This is the strongest evidence against our own product hypothesis, and it came from our
> own data.**

### The caveat that could reverse it

**The dataset samples trips; it does not monitor continuously.** A 30-minute incident
affects few sampled trips, so **absence of detected anomalies is partly an artefact of the
sampling design.** A live feed might reveal volatility this data structurally cannot show.
Half B is **not disproven — it is untested at the right resolution.**

---

## What this implies

The evidence so far points at a **planning and diagnosis** product rather than an
**operations** product:

| | Answers | Evidence |
|---|---|---|
| Planning / diagnosis | *"Where does this city reliably lose time, and what would change it?"* | 🟢 Supported |
| Operations / alerting | *"What is unusual today?"* | 🟡 Thin, and possibly a sampling artefact |

**The officer's test — *"what will I do differently tomorrow morning?"* — may be the wrong
question for this data**, because on 95% of mornings the honest answer is *"nothing."* The
question this data can answer is *"what should I change this quarter?"*

That is not a smaller product. It is a different buyer and a different conversation.

---

## The next step, and it is not another document

> **Build the demo around the strongest demonstrable insight from the 101,418 valid
> primary-route observations. Then show the Commissionerate:**
>
> *"This is what we discovered about how Siliguri moves using historical data. Is this
> information useful to you?"*
>
> **Their reaction determines whether we have a product.**

**That test has not been run.** Everything in this repository is downstream of it, and no
amount of further analysis substitutes for asking.

## What would falsify the hypothesis

Stated in advance, so we cannot rationalise afterwards:

1. **The Commissionerate already knows the findings.** If "no morning peak" and "worst hour
   is 19:00" are unsurprising to them, the "limited structured visibility" premise is wrong.
2. **They know it and it changes nothing.** Visibility without a lever is not decision support.
3. **The structural findings are true but not actionable** — nothing in their remit can move
   free-flow speed.
4. **A live feed shows the same regularity**, confirming there is little unusual to detect
   and Half B fails on its merits rather than on sampling.

**Any of these should stop the programme, or change it substantially.**
