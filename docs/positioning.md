# Positioning

`status: canonical` · **This is the pitch. It leads every document, deck and conversation.**

<p align="center">
  <img src="design/assets/positioning-statement@1x.png" width="640"
       alt="Traffic Data struck through. Traffic Monitoring struck through. Traffic Intelligence." />
</p>

> **What the strikethroughs mean.** Not that data and monitoring are worthless — Siliguri
> **can manage both**. They mean **the focus has moved past them.** Those two tiers are
> available, or achievable, today. **The tier that is missing is intelligence**, and that
> is where attention now belongs.

---

# Siliguri doesn't just need more traffic data. It needs intelligence.

## Traffic Data

Siliguri already has multiple potential sources of mobility information — historical
travel observations, maps, GPS-based movement data and, in future, authorised city data.

**But raw data alone does not tell an officer what matters.**

```
                              ↓
```

## Traffic Monitoring

Existing tools can show what traffic looks like at a particular moment. They can answer:

> *Where is traffic slow right now?*

**But monitoring is reactive**, and does not necessarily explain whether a situation is
normal, recurring or unusual.

```
                              ↓
```

## Traffic Intelligence

**SARGVISION adds the intelligence layer.** It helps answer:

- **How does Siliguri move?**
- **What patterns are normal?**
- **Which journeys are unreliable?**
- **What is unusual today?**
- **What deserves attention?**

---

# The pitch

> **Traffic Data tells us what we have.**
>
> **Traffic Monitoring tells us what is happening.**
>
> **Traffic Intelligence helps us understand what it means.**

**SARGVISION Urban Mobility Intelligence is building this intelligence layer for Siliguri.**

---

# The sharper version — investors and government

> Siliguri does not need another traffic dashboard.
>
> **Traffic data already exists. Traffic monitoring tools already exist.**
>
> What is missing is **an intelligence layer** that can transform mobility observations
> into an understanding of how the city moves, identify recurring and unusual patterns,
> and help authorities focus their attention where it matters.
>
> **That is the gap SARGVISION aims to solve.**

---

# The positioning slide

```text
              TRAFFIC DATA
        What information do we have?
                   │
                   ▼
           TRAFFIC MONITORING
        What is happening right now?
                   │
                   ▼
          TRAFFIC INTELLIGENCE
       What does it mean and what
          deserves our attention?
                   │
                   ▼
          BETTER CITY DECISIONS
```

## SARGVISION's role

> **Transforming Traffic Data and Traffic Monitoring into actionable Traffic Intelligence
> for Siliguri.**

Note the verb: **transforming**, not replacing. The first two tiers are the **input** to
the third. A city that has invested in data collection and monitoring has not wasted that
investment — it has built the foundation the intelligence layer stands on.

---

# How this differentiates us from Google Maps

**Google can provide navigation and traffic visibility. SARGVISION builds the intelligence
and decision-support layer around urban mobility.**

That is a complement, not a competition — and it is the honest description of both. Google
is very good at the tiers it occupies. **Nobody occupies the third one for Siliguri.**

---

# The ladder is not just a slide — it is what we built

The framing is defensible because the engineering follows it exactly:

| Tier | In this product | Evidence |
|---|---|---|
| **Data** | 101,418 valid primary-route observations, openly licensed | [provenance](data-provenance.md) |
| **Monitoring** | Available to the city already; **not something we rebuilt** | — |
| **Intelligence** | Baselines · anomaly detection · confidence · operational priority · evidence coverage | [spike](methodology/spatial-feasibility-spike.md) · [limitations](known-limitations.md) |
| **Decisions** | Prioritised attention, with what we do not know stated alongside | [design](design/ui-ux.md) |

> **We built no monitoring tier, deliberately.** Siliguri can obtain monitoring. Adding a
> fourth traffic dashboard would have consumed the effort that the missing tier needed.

---

# What keeps the claim honest

The intelligence tier is only worth anything if it is trustworthy, so the product states
its limits as prominently as its findings:

- every figure carries **confidence** and **sample size**;
- every figure records **which baseline level produced it**;
- the map shows **where we have no evidence**, rather than rendering absence as calm;
- **42.4%** of observations are scored — published plainly, never implied as city-wide;
- the demonstrator says **historical replay**, never *live*.

**An intelligence layer that overclaims is just a dashboard with better adjectives.**
