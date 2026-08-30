# Data Provenance

## Canonical figure

> **101,418 valid primary-route observations**

**Not** "101,418 observations". The raw joined count is **115,347**. The qualifier is
load-bearing and must appear in any formal document.

## Derivation

```
Zenodo 10.5281/zenodo.10499064  ·  CC BY 4.0  ·  no login
Akbar, Couture, Duranton & Storeygard, "Mobility and Congestion in Urban India",
American Economic Review 113(4), 2023
        │
        ▼
WUP_cities.dta            row 154 → India / Siliguri / citycode 21405
        │
        ▼
alltrips_India.dta        2,735,442 India trip records
        │  filter citycode = 21405
        ▼
                             14,612 Siliguri trip records
        │  join world_main_India_precleaned.dta (21,657,714 observations)
        ▼
                            115,347 raw joined observations
        │  remove traffic_s / notraffic_s / dist_m ≤ 0
        ▼
                            115,330 valid observations
        │  keep primary route (minimum route_rank)
        ▼
                            101,418 valid primary-route observations
                             14,558 distinct trips represented
                                 54 trips with no valid primary-route observation
```

**Window:** 2019-06-13 → 2019-11-05.

Neither `.dta` was downloaded whole — the archive is 1.6 GB. Two members were pulled by
HTTP range request.

## Why primary-route only

One origin-destination query returns several alternative routes. Treating each as an
independent observation counts the same trip-time query two or three times and inflates
the sample. Selecting minimum `route_rank` gives one analytical observation per
trip-time instance.

## What this data may be used for

Methodology validation · baseline development · threshold calibration · historical
pattern analysis · product demonstration · traffic replay.

## What it may **not** be represented as

Comprehensive current operational monitoring · high-confidence analysis of every
corridor · live traffic management.
