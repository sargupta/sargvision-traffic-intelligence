# Source Documents

**The product definition of record.** Every document supplied for this programme, in
reading order. Later documents supersede earlier ones where they conflict; the
[traceability record](../architecture/blueprint-traceability.md) states which sections are
adopted, deferred or rejected on evidence.

| # | Document | What it establishes |
|---|---|---|
| **01** | [Vision — Siliguri Traffic Copilot](01-vision-siliguri-traffic-copilot.pdf) | Why the product exists. From *seeing* traffic to *understanding* it |
| **02** | [Concept Note & PRD](02-concept-note-and-prd.md) | The core problem, positioning against Google Maps, six MVP capabilities |
| **03** | [Product Requirements Document](03-product-requirements-document.md) · [pdf](03-product-requirements-document.pdf) | Functional requirements FR-01…FR-10, modules A–E, agentic design principles |
| **04** | [Siliguri MVP — Final Direction](04-siliguri-mvp-final-direction.md) | Build a demonstrator, not a production deployment. Three flagship workflows |
| **05** | [Technical Feasibility & Architecture Blueprint v2](05-technical-feasibility-blueprint-v2.md) | Canonical data contract, spatial model, visualisation philosophy, phases |

## How these are used

- **They are the specification.** Engineering decisions cite a section.
- **Where evidence contradicts them, evidence wins** — and the contradiction is recorded
  rather than quietly applied. Two sections of document 05 were **rejected on evidence**
  after the [spatial feasibility spike](../methodology/spatial-feasibility-spike.md):
  §8 (segment model) and §9 (map matching), because the observations carry no route geometry.
- **They are not edited.** Corrections live in the traceability record and in
  [`known-limitations.md`](../known-limitations.md), so the original intent stays legible.
