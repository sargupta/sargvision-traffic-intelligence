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

## The write credential is a room token, not an identity

Recording an action requires `Authorization: Bearer $WRITE_TOKEN` — one secret shared by
the control room. It proves the person at the console belongs there. It does not prove
*which* officer acted: `by` is whatever the console reports, so the audit trail is only
as trustworthy as the seat.

That is honest for a single duty-officer console and wrong for a shift with several
people held to their own record. Closing it needs a user directory and per-officer
sign-in, not a longer token. Until then, a rotated token is the only revocation
available, and rotating it locks out every console at once.

## Nothing rate-limits the API

There is no throttle on any endpoint, and the service runs at `--max-instances=1`
because each instance keeps its own corridor state and its own poll loop. Those two
facts combine badly: a trivial request flood, or a single misbehaving script, can
saturate the one instance and leave the duty officer looking at a board that will not
load. Reads are cheap in themselves — they serve from memory — but `/api/board` is
roughly 180 KB of corridor geometry per call.

The exposure is bounded by obscurity rather than by design, which is not a control.
A per-IP limit at the edge is the fix; raising `max-instances` is not, because it
would double the metered Routes bill and split incident state across instances.

## The command interface has no automated tests

`apps/command-web` is about 3,600 lines of the officer-facing surface and its only
gates are `tsc --noEmit` and a successful `next build`. There is no test runner
configured and no linter. Every defect found in it so far — the 34% squashed
projection, the action bar below the fold, the CORS preflight that would have refused
every write — was found by driving a browser, not by a suite.

That is the largest remaining gap in this repository. The Python side has 147 tests
covering the state machine, the API contract, the write gate and the analytics; the
interface has none, so a regression in it is invisible until someone looks.
