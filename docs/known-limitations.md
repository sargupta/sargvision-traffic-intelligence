# Known Limitations

Kept current deliberately. Anything on this list must not be claimed away in a demo,
a document, or a conversation with a client.

## The corridors are not roads

Corridor identifiers are **~1 km grid-cell pairs** — `SIL_2968_9825__2967_9826`.
**Nothing maps to "Sevoke Road" or "Hill Cart Road".** Converting these to named
corridors is the first unblocking task, and it carries real risk: grid pairs reach
300+ observations by aggregating a whole cell, while named corridors are narrower and
may fall below threshold.

## Coverage is thin

**2,621 grid-pair corridors exist; only 32 reach 300+ observations** and enter the
scored set. 7,333 of 101,418 observations are scored, because scoring requires a
baseline bin with ≥12 samples.

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
