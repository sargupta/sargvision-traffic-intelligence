"""Named places in and around Siliguri, used only to *name* zones.

These coordinates do not define zone boundaries. Boundaries come from the
observations (see `packages.zones.model`); the gazetteer supplies a human label
for a cluster the data produced, by nearest landmark.

**Provenance and its limits.** These are approximate centre points for
well-known localities, accurate to a few hundred metres, not survey data and not
an official administrative boundary set. A zone named "Matigara" means "the
cluster of journey endpoints whose centre lies nearest to Matigara" — it does
not mean the cluster is coterminous with Matigara ward, mouza or any gazetted
area. The distance from cluster centre to landmark is recorded on every zone so
the naming can be audited rather than trusted.

Nothing in the analytics keys on these names. Remove the gazetteer and the
engine still runs; the zones simply revert to identifiers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Landmark:
    name: str
    lat: float
    lon: float
    kind: str  # settlement | transport | junction | corridor


LANDMARKS: tuple[Landmark, ...] = (
    # Core city
    Landmark("Siliguri Central", 26.7160, 88.4290, "settlement"),
    Landmark("Pradhan Nagar", 26.7200, 88.4180, "settlement"),
    Landmark("Siliguri Junction", 26.7150, 88.4360, "transport"),
    Landmark("Jalpai More", 26.7060, 88.4310, "junction"),
    Landmark("Bhaktinagar", 26.7060, 88.4420, "settlement"),
    Landmark("Ashrampara", 26.7130, 88.4310, "settlement"),
    Landmark("Champasari", 26.7360, 88.4130, "settlement"),
    # North and north-east
    Landmark("Salugara", 26.7480, 88.4430, "settlement"),
    Landmark("Sevoke More", 26.7280, 88.4390, "junction"),
    Landmark("Sukna", 26.7600, 88.3700, "settlement"),
    # West
    Landmark("Matigara", 26.7185, 88.3720, "settlement"),
    Landmark("Shivmandir", 26.7020, 88.3750, "settlement"),
    Landmark("Kawakhali", 26.7000, 88.4150, "settlement"),
    Landmark("Bagdogra", 26.6810, 88.3290, "transport"),
    # South and east
    Landmark("NJP Station", 26.6870, 88.4290, "transport"),
    Landmark("Dabgram", 26.7020, 88.4600, "settlement"),
    Landmark("Fulbari", 26.6640, 88.4290, "settlement"),
    Landmark("Rangapani", 26.6800, 88.4620, "settlement"),
    Landmark("Eastern Bypass", 26.6950, 88.4680, "corridor"),
)
