"""Junctions and corridors — the only spatial objects the product exposes.

A junction is a named place a traffic officer already talks about: Venus More,
Jalpai More, Darjeeling More. A corridor is the named road between two of them.
No grid identifier, zone id or cluster label reaches a screen.

Every junction carries how confidently it was located. A geocoder always
returns something, and a confident pin placed because the API answered is
exactly the false precision this product exists to avoid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

JUNCTIONS = Path("data/curated/junctions.json")
CORRIDORS = Path("data/curated/corridors.json")


@dataclass(frozen=True)
class Junction:
    junction_id: str
    name: str
    lat: float
    lon: float
    control: str  # SIGNALISED | NON_SIGNALISED | MIXED | GRADE_SEPARATED
    vc_ratio: float | None  # CMP 2011, via Siliguri CDP 2041
    match_quality: str  # CONFIRMED | NEAR | ROAD_ONLY
    match_note: str
    formatted_address: str | None = None

    @property
    def pin_is_approximate(self) -> bool:
        return self.match_quality == "ROAD_ONLY"

    @property
    def congestion_pressure(self) -> str | None:
        """The 2011 volume-to-capacity reading, banded.

        Historical and structural — it describes the junction's designed
        capacity against measured volume, not today. Kept separate from live
        congestion for that reason.
        """
        if self.vc_ratio is None:
            return None
        if self.vc_ratio >= 1.0:
            return "OVER_CAPACITY"
        if self.vc_ratio >= 0.8:
            return "NEAR_CAPACITY"
        return "WITHIN_CAPACITY"


@dataclass(frozen=True)
class Corridor:
    corridor_id: str
    name: str
    from_junction: str
    from_name: str
    to_junction: str
    to_name: str
    endpoints_quality: tuple[str, ...]

    @property
    def located_approximately(self) -> bool:
        return "ROAD_ONLY" in self.endpoints_quality


@dataclass
class Network:
    junctions: dict[str, Junction]
    corridors: dict[str, Corridor]

    def junction(self, jid: str) -> Junction | None:
        return self.junctions.get(jid)

    def corridor(self, cid: str) -> Corridor | None:
        return self.corridors.get(cid)

    def corridors_at(self, junction_id: str) -> list[Corridor]:
        return [
            c for c in self.corridors.values() if junction_id in (c.from_junction, c.to_junction)
        ]

    def neighbours(self, junction_id: str) -> list[str]:
        out = []
        for c in self.corridors_at(junction_id):
            out.append(c.to_junction if c.from_junction == junction_id else c.from_junction)
        return sorted(set(out))


def load_network(junctions_path: Path = JUNCTIONS, corridors_path: Path = CORRIDORS) -> Network:
    junctions = {
        j["junction_id"]: Junction(
            junction_id=j["junction_id"],
            name=j["name"],
            lat=j["lat"],
            lon=j["lon"],
            control=j["control"],
            vc_ratio=j.get("vc_ratio"),
            match_quality=j["match_quality"],
            match_note=j["match_note"],
            formatted_address=j.get("formatted_address"),
        )
        for j in json.loads(junctions_path.read_text())
    }
    corridors = {
        c["corridor_id"]: Corridor(
            corridor_id=c["corridor_id"],
            name=c["name"],
            from_junction=c["from_junction"],
            from_name=c["from_name"],
            to_junction=c["to_junction"],
            to_name=c["to_name"],
            endpoints_quality=tuple(c["endpoints_quality"]),
        )
        for c in json.loads(corridors_path.read_text())
    }
    return Network(junctions=junctions, corridors=corridors)
