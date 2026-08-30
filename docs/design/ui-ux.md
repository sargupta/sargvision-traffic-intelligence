# Design & UI/UX

`status: proposed` · 30 August 2026 · Adapted from Blueprint v2 §18–26, **corrected by the
[spatial feasibility spike](../methodology/spatial-feasibility-spike.md).**

---

## 0. The constraint that shapes every screen

The spike found the observations carry **origin and destination points only — no route
geometry.** That is not merely a data note. It is the dominant design constraint:

> # We cannot colour roads, because we do not know which roads.

Every conventional traffic UI — the red/amber/green road overlay everyone has seen on a
traffic map — is **unavailable to us and would be a lie if we drew it.** Painting Sevoke
Road red would assert that the delay happened *on Sevoke Road*, which this data cannot
establish.

**What we can honestly draw is a relationship between two areas.**

```
  ✗  WRONG — implies a known path            ✓  RIGHT — states what we measured
  ═══════════════════════                    ○ ─ ─ ─ ─ ─ ─ ─ ▷ ○
  a red line along a road                    Zone A          Zone D
  "this road is congested"                   "travel between these areas
                                              is 43% slower than normal"
```

The visual language is **arcs between zone centroids**, drawn deliberately as *abstract
connectors* — dashed, curved, clearly not following the street grid — so no viewer can
mistake them for a route.

> **This is a design advantage, not a limitation to hide.** Every competitor's map implies
> precision it cannot support. Ours states exactly what it knows, and that is the product's
> entire proposition made visible.

---

## 1. Design principles

| # | Principle | Consequence |
|---|---|---|
| 1 | **Never imply precision we do not have** | Arcs, not road overlays. Zone areas, not street lines |
| 2 | **Every number carries confidence and sample size** | No bare figure appears anywhere in the UI |
| 3 | **Absence of evidence is rendered, not hidden** | Unobserved areas are visibly unobserved |
| 4 | **The list is the entry point, the map is context** | Blueprint Risk 6 — officers must not have to hunt a map |
| 5 | **Replay mode is always visible** | A persistent banner, never a subtle label |
| 6 | **Severity is not priority, and the UI shows both** | Two distinct visual encodings |
| 7 | **Colour is never the only signal** | Labels, icons, patterns — accessibility and print |

---

## 2. Visual language

### Severity — how abnormal

| | Band | Colour | Token | Also shown as |
|---|---|---|---|---|
| ○ | EXPECTED | slate-400 | `--sev-expected` | "within normal range" |
| ◔ | MODERATE ≥30% | amber-500 | `--sev-moderate` | "+34% vs expected" |
| ◑ | HIGH ≥45% | orange-600 | `--sev-high` | "+51% vs expected" |
| ● | CRITICAL ≥60% | red-600 | `--sev-critical` | "+72% vs expected" |

### Priority — how much attention

Rendered as a **rank chip**, deliberately unlike severity so they cannot be confused:

```
 P1   solid, filled      P2   solid, outlined
 P3   muted outline      P4   text only
```

> A **P1 MODERATE** and a **P4 CRITICAL** must both be legible at a glance, because that
> pairing is the entire reason the two quantities are separate. The UI must make the
> juxtaposition feel deliberate rather than contradictory.

### Confidence — how much to trust it

**Never a colour.** Confidence is structural, shown as a sample-size bar plus a word:

```
HIGH        ████████  n = 412
MODERATE    ████░░░░  n = 156
LOW         ██░░░░░░  n = 41      ⚠ interpret with caution
INSUFFICIENT ░░░░░░░░  n = 8      — no baseline published
```

### Evidence coverage — the map's fourth dimension

From the spike: **only 9.5% of spatial units carry usable evidence.**

```
████  HIGH          n ≥ 300     32 units    1.2%
▓▓▓▓  MODERATE      n 100–299  218 units    8.3%
▒▒▒▒  LOW           n 30–99    639 units   24.4%
░░░░  INSUFFICIENT  n < 30   1,732 units   66.1%
```

**Unobserved zones render as a visible hatch, not as empty basemap.** An officer must be
able to tell "nothing is wrong here" from "we cannot see here" — and on a conventional
traffic map those look identical. Making them different is a correctness feature.

---

## 3. Screens

### Screen 1 — Attention (home)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  SARGVISION TRAFFIC INTELLIGENCE            Siliguri                     │
├──────────────────────────────────────────────────────────────────────────┤
│  ⏱ HISTORICAL REPLAY · 03 Jul 2019 · 18:30   [❚❚] [1x] [10x] [⟲]         │
├────────────────────────────┬─────────────────────────────────────────────┤
│  WHAT DESERVES ATTENTION   │                                             │
│                            │        ╭──────────────────────╮             │
│  ┌──────────────────────┐  │        │  ▓▓▓  ░░░░░░  ▒▒▒    │             │
│  │ P1  ● CRITICAL       │  │        │   ○ ─ ─ ─ ─ ▷ ○      │             │
│  │ Central ▷ Station    │  │        │  ████    ░░░░░░      │             │
│  │ +72% vs expected     │  │        │      ▒▒▒▒▒▒          │             │
│  │ 25 min · n=412 HIGH  │  │        ╰──────────────────────╯             │
│  └──────────────────────┘  │                                             │
│  ┌──────────────────────┐  │   ░░ we have no evidence here               │
│  │ P1  ◔ MODERATE       │  │   Arcs show measured area-to-area travel.   │
│  │ North ▷ Central      │  │   They are NOT routes.                      │
│  │ +34% · 45 min        │  │                                             │
│  │ n=340 HIGH           │  │                                             │
│  └──────────────────────┘  │                                             │
├────────────────────────────┴─────────────────────────────────────────────┤
│  ASK  ▸ What should I look at first, and why?                            │
└──────────────────────────────────────────────────────────────────────────┘
```

**Note the second card: MODERATE severity, P1 priority.** Persistent, on an important
pair, high confidence. It outranks a brief CRITICAL. The card layout puts priority first
and severity second precisely so that reads as intended.

**The officer must be able to answer "what deserves attention?" in under 30 seconds
without touching the map.**

### Screen 2 — Investigation

The most important screen in the product.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ←  INVESTIGATION · Central ▷ Station          P1   ● CRITICAL           │
├──────────────────────────────────────────────────────────────────────────┤
│  WHAT WE MEASURED                                                        │
│    observed 27.4 min   ·   expected 15.9 min   ·   +72%                  │
│    "72% above the expected travel-time ratio for this pair at 18:30      │
│     on a weekday"                            ← never a bare "+72%"       │
│    persistence 25 min  ·  confidence HIGH  ·  n = 412  ·  baseline: 1 km │
├──────────────────────────────────────────────────────────────────────────┤
│  HOW IT EVOLVED                                                          │
│      ratio                                    ● observed                 │
│   1.8 ┤                    ●●●                ▨ expected range (p25–p75) │
│   1.4 ┤             ●▨▨▨▨▨▨▨▨▨▨●                                          │
│   1.0 ┤ ●●●▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨▨●●●                                      │
│       └──────────────────────────────────                                │
│        16:00      18:00      20:00                                       │
├──────────────────────────────────────────────────────────────────────────┤
│  HAS THIS HAPPENED BEFORE?     7 comparable occasions · median +48%      │
├──────────────────────────────────────────────────────────────────────────┤
│  WHAT ELSE IS NEARBY?          2 adjacent pairs also elevated            │
│    ⚠ Spatial proximity only. This is NOT evidence of congestion          │
│      spreading from one to the other.                                    │
├──────────────────────────────────────────────────────────────────────────┤
│  WHAT WE DO NOT KNOW                                                     │
│    · The physical cause is not established by this data.                 │
│    · Which roads were used is not recorded — only origin and destination.│
│    · Historical replay of 2019 data, not live observation.               │
├──────────────────────────────────────────────────────────────────────────┤
│  ▸ ASK COPILOT     "Why does this matter?"                               │
└──────────────────────────────────────────────────────────────────────────┘
```

> **"What we do not know" is a fixed section, not a tooltip.** It has the same visual
> weight as the findings. This is the screen that earns institutional trust, and it earns
> it by being the only traffic product in the room that says what it cannot see.

### Screen 3 — City Intelligence

Strategic, not operational. Hourly profile · day×hour heatmap · **evidence coverage map**
· confidence distribution.

The coverage map is not an appendix. **It is the answer to "how much of this city can you
actually see?"**, and blueprint §25 was right to insist on it.

### Screen 4 — Copilot

Renders the structured `AnswerContract` — never free prose:

```
  OBSERVATION      Travel between Central and Station is taking 27.4 minutes.
  COMPARISON       That is 72% above the expected 15.9 minutes for 18:30 on a
                   weekday, based on 412 comparable observations.
  INTERPRETATION   The condition has persisted 25 minutes, beyond the threshold
                   at which conditions usually resolve.               ⓘ inference
  LIMITATION       The physical cause is not established. Which roads were used
                   is not recorded. This is 2019 historical replay.
  NEXT STEP        Field verification would establish whether an obstruction or
                   an incident is present.

  ▸ evidence: 3 metrics   ▸ tools: get_priorities, investigate_event, get_history
```

Each section is a **separately styled block**. `INTERPRETATION` carries an inference
marker. `LIMITATION` cannot be collapsed or dismissed — the contract will not construct
without it, and the UI will not render without showing it.

---

## 4. Layout and interaction

**Three-pane on desktop**: priority list (left, fixed 380px) · map (centre, fluid) ·
investigation (right, slides over on selection). Below 1024px the map collapses to a
tab — the list survives, because the list is the product.

**The replay bar is persistent**, top of viewport, above everything, with an amber left
border. It is never dismissible.

## 5. Type and colour

Inter or Geist for UI; **tabular figures mandatory** for all numerics so columns align and
digits do not jitter during replay. Slate neutrals, with severity as the only saturated
colour in the interface — so severity reads as signal rather than decoration.

Dark mode is the default: this is a control-room product, often on a wall display, often
at night.

## 6. What we will not build

Speedometer gauges · animated traffic flow along roads · a 3D city · vehicle icons ·
anything that implies live monitoring · anything implying we know which roads were used ·
any chart that does not answer a decision question (blueprint §18).

## 7. Accessibility

WCAG 2.1 AA. Severity never encoded by colour alone. Full keyboard navigation of the
priority list and investigation. Replay controls operable without a pointer. Tested at
200% zoom, because control-room displays are viewed from across a room.
