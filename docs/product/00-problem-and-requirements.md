# Siliguri Traffic Command — Problem Statement and Requirements

`status: authoritative` · 30 August 2026 · **Every agent working on this product reads this first.**

---

## 1. The question we were actually asked

> *"The time it takes from point A to point B is much higher than expected.
> What are the different choke points? What are the different traffic prone
> areas? What are the time frames? When exactly it happens?"*

Four questions. **Where, what kind, what time, how bad.** Then a fifth the user
did not have to say out loud, because it is what a police department is for:

> **What do I do about it, and did it work?**

## 2. What we got wrong before this document existed

| Mistake | Consequence |
|---|---|
| Made the primary object a k-means zone pair (`SIL_Z00__SIL_Z03`) | No officer thinks in zone pairs. The product spoke a language nobody in the room uses. |
| Treated Siliguri as an abstract graph | Discarded fifteen **named junctions with measured V/C ratios** that we already held. |
| Built detection and explanation, no action | An officer could see a problem and do nothing with it. The system had no verbs. |
| Dark "control room" aesthetic | Wrong for daytime office use, wrong for printing, wrong for the actual users. |
| Conflated congestion with danger | Venus More is the most dangerous junction in the city **and one of the least congested.** A single "severity" ranking hides that. |

## 3. Who uses this

| Role | What they need | Session |
|---|---|---|
| **Duty Officer** (control room) | What is wrong right now, where, how bad, who is on it | All shift, one screen, glanceable |
| **Traffic Sergeant / OC** (field) | My assignments, directions, log what I did | Phone, 30 seconds at a time |
| **Traffic Inspector** | Junction history, recurring problems, staffing decisions | Daily, 10–20 minutes |
| **DCP Traffic / Commissioner** | Is the city getting better, what changed, what to brief | Weekly, needs printable output |

The **Duty Officer is the primary user.** Every design decision resolves in
their favour when there is a conflict.

## 4. The domain — Siliguri's real geography

Junctions, with V/C ratio from CMP 2011 (published in Siliguri CDP 2041) and
accident evidence from Roy, Mohammadi & Roy, *Geographies* 6(2):55 (2026).

| Junction | Control | V/C | Safety signal |
|---|---|---|---|
| Jalpai More | **Non-signalised** | **1.14** | — |
| Mahananda Bridge (Hill Cart Road) | Signalised | 1.13 | — |
| Champasari More | Signalised | 1.09 | secondary hotspot |
| Darjeeling More | Signalised | 1.03 | evening leader, 16.13% |
| Pani Tanki More | Signalised | 0.81 | — |
| Check Post More | Signalised | 0.77 | — |
| Jhankaar More (Hyderpara) | Mixed | 0.75 | — |
| Wall Ford Rd × Bypass | Non-signalised | 0.69 | — |
| Air View More | Signalised | 0.60 | approaches reach TTI 4.095 |
| Thana More | Signalised | 0.52 | — |
| Wall Ford Rd × Sevoke Rd | Signalised | 0.48 | — |
| Sevoke More | Signalised | 0.41 | — |
| **Venus More** | Signalised | **0.39** | **highest accident density, 14.21/km², intensifying** |
| Ashighar More | Non-signalised | 0.38 | — |
| Mallaguri Crossing | Grade separated | 0.08 | — |

**The load-bearing fact:** congestion and danger are in different places.
Venus More is fourth-from-bottom on congestion and worst in the city on
accidents. A product with one severity score cannot say this. Ours must.

## 5. Requirements

### R1 — Speak the city's language
Every location is a **named junction or named corridor**. No grid identifiers
reach a screen. `Hill Cart Road: Darjeeling More → Mahananda Bridge`, never
`SIL_Z00__SIL_Z03`.

### R2 — Answer the four questions on one screen
Where, what kind, when, how bad — visible without a click.

### R3 — Separate congestion from safety
Two independent scores, never averaged. A junction may be red for one and
green for the other, and that must be legible at a glance.

### R4 — Give the officer verbs
Acknowledge · Assign · Add note · Request field check · Escalate · Resolve ·
Reopen. Every alert has a next action and an owner.

### R5 — Time windows, not instants
"When exactly does it happen" is answered with recurring windows
(`Tue–Fri 17:30–20:00`), not a single timestamp.

### R6 — Shift continuity
A shift handover produces a written record: what is open, what was done, what
the next shift inherits.

### R7 — Field-usable
The sergeant's view works on a phone, one-handed, on a poor connection.

### R8 — Printable
Daily and weekly briefings print to A4 without a screenshot.

### R9 — Light interface
Daytime office use, projector-friendly, prints legibly. Dark is a preference,
not the default.

### R10 — Evidence on every claim
Sample size and confidence travel with every number. Where there is no
evidence the interface says so rather than showing an empty state that reads
as "fine".

### R11 — Never imply a cause
The system reports what changed and by how much. Cause is the officer's
judgement, recorded by them, not asserted by us.

### R12 — Compliance is structural
Google Maps Terms permit caching lat/lng only. No durable store of Routes API
durations. See `packages/providers/live.py`.

## 6. Explicitly out of scope

Signal optimisation · CCTV/ANPR · vehicle detection · digital twin · automated
enforcement · challan issuance · anything that acts on the road without an
officer deciding.

## 7. Definition of done

An officer can open the application cold, see the three things most worth their
attention, understand why each is on the list, assign one to a sergeant, record
what was found, close it, and hand over a written shift summary — without
training and without asking what a term means.
