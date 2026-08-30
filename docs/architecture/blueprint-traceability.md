# Blueprint v2 — Traceability

`30 August 2026` · Source: [`docs/source-documents/`](../source-documents/)

Written because the honest answer to *"did you copy everything?"* was **no**. This is the
section-by-section account, so nothing is assumed adopted that is not.

| § | Topic | Status | Where / why |
|---|---|---|---|
| 1–4 | Product definition, scope discipline | ✅ Adopted | `README.md` |
| 2 | Feasibility scores | 📋 Reference | Not code. Kept in the source document |
| 5 | Canonical data contract | ✅ Adopted | `packages/domain/canonical.py` |
| 6 | User workflow | ✅ Adopted | `docs/design/ui-ux.md` |
| 7 | Data reality, minimum samples | ✅ Adopted | `packages/analytics/confidence.py` |
| **8** | **Spatial hierarchy with SEGMENT** | ❌ **Rejected on evidence** | **No route geometry. [Spike](../methodology/spatial-feasibility-spike.md) Q1/Q2.** Segment removed; OD zone pair is the atom |
| **9** | **Map matching, OSMnx, PostGIS** | ❌ **Deleted** | Nothing to map-match. Saves the 1–2 week Phase 2 |
| 10 | Canonical data model | ✅ Adopted | `canonical.py` — `TrafficObservation`, `UnitMetric` (was `SegmentMetric`), `TrafficAnomaly`, `TrafficEvent`, `Investigation` |
| 11 | Traffic metrics | ✅ Adopted | `Observation` / `TrafficObservation` properties |
| **12** | **Baseline confidence + hierarchical fallback** | ✅ **Adopted — was the biggest gap** | `packages/analytics/confidence.py`. `baseline_source` records which level produced the figure |
| 13 | Anomaly detection, deterministic | ✅ Adopted | `packages/analytics/anomalies.py` |
| 14 | Event engine | ⚠️ Partial | State machine is `NORMAL→ELEVATED→ACTIVE→RESOLVED`; blueprint proposes `DETECTED→ACTIVE→STABILISING→RESOLVED`. **`STABILISING` not implemented** |
| **15** | **Priority incl. confidence factor** | ✅ **Adopted** | `packages/intelligence/priority.py`. INSUFFICIENT confidence scores **zero** |
| 16 | Pattern / similar-event retrieval | ❌ Not built | Phase 3 |
| 17 | Spatial context, not network intelligence | ❌ Not built | Phase 3. Scope correction accepted |
| 18–19 | Visualisation philosophy | ✅ Adopted | `docs/design/ui-ux.md` |
| 20–24 | Screens 1–5 | ✅ Adopted, adapted | Four screens. **Arcs, not road overlays** — the spike's constraint |
| **25** | **Evidence coverage visualisation** | ✅ **Promoted to correctness requirement** | Only 9.5% of units carry usable evidence |
| 26 | Map architecture, layers | ⚠️ Partial | Layer model adopted; **road-styling layers rejected** |
| 27–29 | Copilot architecture, schema, tools | ❌ Not built | `packages/copilot/` scaffolded only. Phase 6 — deliberately last |
| 30–33 | Backend, stack, DuckDB-first, provider abstraction | ✅ Adopted | `packages/providers/base.py` |
| 34 | Repository structure | ✅ Aligned | `copilot/`, `analytics/spatial/`, `notebooks/`, `data/curated/`, `tests/{unit,integration,data}` added |
| 35–36 | Phases and timeline | ⚠️ Revised | **Phase 0 done.** Phase 2 collapses from 1–2 weeks to days |
| 37 | Testing strategy | ⚠️ Partial | Contract tests only. **Data, analytical, event, spatial and AI tests not written** |
| 38–39 | Dependencies and risks | ✅ Adopted | `docs/known-limitations.md` |
| 40–41 | Scope, success metrics | ⚠️ Partial | Scope adopted; **success metrics not instrumented** |
| 42–44 | Evolution, final architecture | ✅ Adopted | — |

---

## Known gaps before building

1. **`STABILISING` event state** — the blueprint's lifecycle has four states, ours has an
   implicit merge of two.
2. **Pattern intelligence (§16)** and **spatial context (§17)** — not started.
3. **Copilot (§27–29)** — scaffolded, empty. Correct: it comes last.
4. **Test coverage (§37)** — four contract tests. No data, analytical, event, spatial or
   AI-evaluation tests.
5. **Success metrics (§41)** — defined in the source document, not instrumented.
6. **The 12% problem** — the pipeline still runs at 1 km / ≥300 and scores 12% of the
   data. The confidence and fallback machinery now exists; **wiring it into the service is
   the next commit**, and it takes the engine to 91%.

## Rejected, and why

**§8 segments and §9 map matching.** Not deferred — *rejected on evidence*. The
observations carry origin and destination points and no path. Building a segment model
would produce numbers that look rigorous and are assumptions.
