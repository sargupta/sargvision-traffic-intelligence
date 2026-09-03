# Known Limitations

Kept current deliberately. Anything on this list must not be claimed away in a demo,
a document, or a conversation with a client.

## The corridors are not roads

Corridor identifiers are **~1 km grid-cell pairs** — `SIL_2968_9825__2967_9826`.
**Nothing maps to "Sevoke Road" or "Hill Cart Road".** Converting these to named
corridors is the first unblocking task, and it carries real risk: grid pairs reach
300+ observations by aggregating a whole cell, while named corridors are narrower and
may fall below threshold.

## Coverage is thin — improved, still partial

Hierarchical 1 km → 2 km fallback now scores **42,988 of 101,418 observations (42.4%)**
across **820 baseline bins** and **91 units**, up from 12,220 / 385 / 32 (12.0%).

> ⚠️ **This is below the 91% the spike reported at the 2 km unit, and deliberately so.**
> The spike measured coverage at a **≥12-sample bin floor**. We publish at **≥30**, because
> a median computed on twelve observations is not a baseline anyone should act on. The
> cost is coverage; the gain is that every published figure is defensible.
>
> **42.4% at a ≥30 floor is the honest number. 91% at ≥12 would be a worse product.**

Of what is scored, **36,431 observations carry LOW confidence** and 6,557 MODERATE — and
**none is HIGH**. The UI must render that, not average it away.

Only **876 observations** resolve against a 1 km baseline; the rest fall back to 2 km.
`baseline_source` records which, on every figure.

## This is historical replay, not live monitoring

`is_live` is `False` everywhere and the API returns the mode on every response. Any
demonstration must say so out loud.

## Free-flow is modelled, not observed

`notraffic_s` is Google's modelled free-flow, **not** an observed speed — demonstrated
by TTI falling below 1.0 overnight, which is physically impossible. Any statement about
the congestion share of the speed gap must be given as a **range (10–15%)**, never a
decimal.

## Untested components

- **Persistence** — the middle term of the priority formula has never been exercised on
  a live cadence. The 2019 sample has no regular per-corridor time series.
- **Corridor importance** — reads a value nobody has assigned. No corridor has been
  classified by the Commissionerate.
- **Reliability weights** — invented placeholders, not derived.

## Thresholds are city-specific

+30/+45/+60 were calibrated against Siliguri 2019 observations. They are configuration,
not constants, and must be recalibrated for any other city or data source.

## Officer identity is only as good as the tokens issued

Recording an action requires a bearer token. With `OFFICER_TOKENS` set — a JSON object
of token to officer id — the server derives the actor from the credential and ignores
whatever `by` the console sends, so a console cannot record in another officer's name
and the trail names a person. `/health` reports `attribution: per-officer`.

With only `WRITE_TOKEN` set, one secret is shared by the room. The gate still holds, but
the server cannot tell one officer from another, so it has to believe the claimed `by`
and the record names a seat. That state is reported honestly as
`attribution: shared` rather than left to be assumed from "gated".

What remains: tokens are issued by hand and revoked by rotation. There is no directory,
no expiry, and no way to revoke one officer without reissuing to everyone. That is a
sign-in problem, not a longer-token problem.

## Rate limiting is per instance, and per IP

Reads are capped at 240/min per caller and writes at 30/min, with a much tighter 10/min
on rejected credentials so the token cannot be guessed at the write rate. The event
stream is exempt: one long-lived connection per console is not traffic. A caller is
identified by the head of `X-Forwarded-For`, because `request.client` is Cloud Run's
load balancer and would put the whole city in one bucket.

The counters live in the process, which is correct while `--max-instances=1` holds — and
that is a correctness constraint, not a cost one, since each instance keeps its own
corridor state and poll loop. If the cap is ever raised these limits become per-instance
and have to move to a shared store.

What remains: this bounds accidental and casual abuse. It is not DDoS protection, and an
attacker with many addresses is unaffected. That needs a limit at the edge.

## The command interface is tested, but thinly

`apps/command-web` now has a test runner (Vitest, jsdom) and a linter (ESLint,
`next/core-web-vitals`, warnings as errors), both gating in CI alongside `tsc` and the
build. 36 tests cover the officer verbs on a card, the typed failure paths including the
409 that means another officer got there first, the token store and its behaviour when a
browser refuses storage, the run-class encoding invariants — that a class is never
distinguished by colour alone, and that all three survive a monochrome printer — and the
map projection.

The projection was extracted to `lib/project.ts` to be testable, because it caused the
worst defect in this repository: the plan drew the city about 1.5x longer per kilometre
east-west than north-south while a comment above it claimed to keep the city's shape
honest. It is now asserted against the real junction bounding box, in landscape and
portrait boxes, for one shared scale across every pair of points, north-up, east-right,
containment within the label gutter, the longitude cosine, and degenerate input.

What is still not covered: label decluttering, pan and zoom clamping, and the Google
basemap layer. Those need a real layout engine or a GPU, and jsdom gives neither, so they
remain browser-verified by hand. The three-second and above-the-fold properties at
1366x768 are also unasserted — they are questions about rendered geometry, and the honest
tool for them is a headless browser rather than jsdom.
