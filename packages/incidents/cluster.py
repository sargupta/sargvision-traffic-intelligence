"""Merge choke points that are the same physical problem.

A jam on Hill Cart Road appears on every corridor routed through it. Reported
raw, one blockage becomes four alerts, and an officer sent to deal with "four
problems" finds one. Merging them is not tidying — it is the difference between
a dispatch that makes sense and one that does not.

Two choke points are the same problem when their stretches of road are close
enough together that a single officer standing there would see both.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from packages.network.probe import ChokePoint

# A traffic officer posted at a junction can see and influence roughly this far.
# Choke points closer together than this are one deployment, not two.
SAME_PROBLEM_M = 350.0

SEVERITY_RANK = {"SLOW": 1, "TRAFFIC_JAM": 2}


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat = math.radians((a[0] + b[0]) / 2)
    return math.hypot((b[0] - a[0]) * 111_320.0, (b[1] - a[1]) * 111_320.0 * math.cos(lat))


@dataclass
class ChokeCluster:
    """One physical problem, seen from every corridor that runs through it."""

    centre: tuple[float, float]
    severity: str
    members: list[tuple[str, ChokePoint]] = field(default_factory=list)

    @property
    def corridors(self) -> list[str]:
        return sorted({cid for cid, _ in self.members})

    @property
    def corroboration(self) -> int:
        """How many independent corridors report this.

        Two corridors seeing the same jam is stronger evidence than one seeing
        it twice as badly, and the interface should say which it has.
        """
        return len(self.corridors)

    @property
    def length_m(self) -> float:
        return max((c.length_m for _, c in self.members), default=0.0)

    @property
    def worst_share(self) -> float:
        return max((c.share_of_corridor for _, c in self.members), default=0.0)

    def as_dict(self) -> dict:
        return {
            "centre": [round(self.centre[0], 6), round(self.centre[1], 6)],
            "severity": self.severity,
            "corridors": self.corridors,
            "corroboration": self.corroboration,
            "length_m": round(self.length_m),
            "worst_share_of_corridor": round(self.worst_share, 3),
        }


def cluster_chokes(
    per_corridor: dict[str, list[ChokePoint]], radius_m: float = SAME_PROBLEM_M
) -> list[ChokeCluster]:
    """Single-link clustering on midpoints.

    Single-link rather than centroid: a jam is a line along a road, not a blob,
    and two ends of the same queue should join even when their midpoints are
    further apart than the radius.
    """
    items: list[tuple[str, ChokePoint]] = [
        (cid, choke) for cid, chokes in per_corridor.items() for choke in chokes
    ]
    if not items:
        return []

    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[rj] = ri

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i][1], items[j][1]
            # Closest approach between the two stretches, not centre to centre.
            gap = min(
                metres(a.midpoint, b.midpoint),
                metres(a.start, b.end),
                metres(a.end, b.start),
                metres(a.start, b.start),
                metres(a.end, b.end),
            )
            if gap <= radius_m:
                union(i, j)

    groups: dict[int, list[tuple[str, ChokePoint]]] = {}
    for idx, item in enumerate(items):
        groups.setdefault(find(idx), []).append(item)

    clusters: list[ChokeCluster] = []
    for members in groups.values():
        lats = [c.midpoint[0] for _, c in members]
        lons = [c.midpoint[1] for _, c in members]
        severity = max(
            (c.severity for _, c in members), key=lambda s: SEVERITY_RANK.get(s, 0)
        )
        clusters.append(
            ChokeCluster(
                centre=(sum(lats) / len(lats), sum(lons) / len(lons)),
                severity=severity,
                members=members,
            )
        )

    clusters.sort(
        key=lambda c: (SEVERITY_RANK.get(c.severity, 0), c.corroboration, c.length_m),
        reverse=True,
    )
    return clusters
