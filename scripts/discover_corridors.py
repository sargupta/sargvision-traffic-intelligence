"""Work out which junctions are actually connected, and how far apart by road.

A corridor is the thing an officer names: "Hill Cart Road, Darjeeling More to
Mahananda Bridge". Rather than guess the topology, ask the road network: if the
driving distance between two junctions is close to the straight line between
them, they are directly connected. If the road takes half again as long, there
is something in between and they are not neighbours.

**What this script persists, and what it does not.** The Maps Service Specific
Terms permit caching latitude and longitude. They do not permit building a
durable store of travel content. So this writes the corridor *identity* — which
junction pairs are neighbours, along which road — which is our own editorial
conclusion. Distances and durations are fetched live at runtime and are printed
here only to inform the decision.

Run:  GEO_API_KEY=... .venv/bin/python scripts/discover_corridors.py
"""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.request
from pathlib import Path

JUNCTIONS = Path("data/curated/junctions.json")
OUT = Path("data/curated/corridors.json")
KEY = os.environ.get("GEO_API_KEY", "")

ENDPOINT = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"

# A pair is a neighbour when the road is not much longer than the crow flight,
# the two are close enough to be one corridor an officer would name, AND no
# third junction lies between them.
#
# The betweenness test is what makes this a network rather than a complete
# graph. In a compact city almost every junction is within a few kilometres of
# every other, so distance alone kept 105 of 160 pairs — everything joined to
# everything. If the road from A to C and on to B is barely longer than A to B
# directly, then B is reached THROUGH C and "A to B" is not a corridor anyone
# would name; it is two corridors.
MAX_DETOUR = 1.45
MAX_ROAD_M = 6_000
MIN_ROAD_M = 250
BETWEEN_SLACK = 1.15


def haversine(a: dict, b: dict) -> float:
    R = 6_371_000
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = p2 - p1
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def route_matrix(points: list[dict]) -> dict[tuple[int, int], dict]:
    waypoints = [
        {"waypoint": {"location": {"latLng": {"latitude": p["lat"], "longitude": p["lon"]}}}}
        for p in points
    ]
    body = {
        "origins": waypoints,
        "destinations": waypoints,
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_UNAWARE",
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": KEY,
            "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters,duration,condition",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        rows = json.loads(r.read())
    return {
        (int(e["originIndex"]), int(e["destinationIndex"])): e
        for e in rows
        if e.get("condition") == "ROUTE_EXISTS"
    }


def main() -> None:
    if not KEY:
        sys.exit("GEO_API_KEY is not set")

    junctions = json.loads(JUNCTIONS.read_text())
    matrix = route_matrix(junctions)
    print(f"route matrix: {len(matrix)} of {len(junctions) ** 2} pairs routable\n")

    def road(i: int, j: int) -> float | None:
        e = matrix.get((i, j))
        d = e.get("distanceMeters") if e else None
        return float(d) if d is not None else None

    def has_junction_between(i: int, j: int, direct: float) -> str | None:
        """Return the name of a junction that lies on the way, if one does."""
        for k in range(len(junctions)):
            if k in (i, j):
                continue
            ik, kj = road(i, k), road(k, j)
            if ik is None or kj is None:
                continue
            if ik + kj < direct * BETWEEN_SLACK:
                return junctions[k]["name"]
        return None

    seen: set[frozenset[str]] = set()
    corridors: list[dict] = []
    rejected_detour = 0
    rejected_between = 0

    for (i, j), entry in sorted(matrix.items(), key=lambda kv: kv[1].get("distanceMeters", 1e9)):
        if i == j:
            continue
        a, b = junctions[i], junctions[j]
        pair = frozenset({a["junction_id"], b["junction_id"]})
        if pair in seen:
            continue

        road_m = entry.get("distanceMeters")
        if road_m is None or not (MIN_ROAD_M <= road_m <= MAX_ROAD_M):
            continue

        crow = haversine(a, b)
        detour = road_m / crow if crow else 99
        if detour > MAX_DETOUR:
            rejected_detour += 1
            continue

        through = has_junction_between(i, j, float(road_m))
        if through:
            rejected_between += 1
            continue

        seen.add(pair)
        corridors.append(
            {
                "corridor_id": f"C_{a['junction_id'][2:]}__{b['junction_id'][2:]}",
                "from_junction": a["junction_id"],
                "from_name": a["name"],
                "to_junction": b["junction_id"],
                "to_name": b["name"],
                "name": f"{a['name']} → {b['name']}",
                # Retained so the interface can say how sure it is of the pin at
                # each end; the corridor is only as located as its junctions.
                "pin_quality": min(
                    a["match_quality"], b["match_quality"],
                    key=lambda q: {"CONFIRMED": 0, "NEAR": 1, "ROAD_ONLY": 2}[q],
                ) if a["match_quality"] == b["match_quality"] else "MIXED",
                "endpoints_quality": [a["match_quality"], b["match_quality"]],
            }
        )
        print(
            f"{a['name']:<26} → {b['name']:<26} road {road_m:>5} m  "
            f"crow {crow:>5.0f} m  detour {detour:.2f}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(corridors, indent=1))
    print(
        f"\n{len(corridors)} corridors kept · {rejected_detour} rejected as too "
        f"indirect · {rejected_between} rejected because another junction lies between"
    )
    degree: dict[str, int] = {}
    for c in corridors:
        degree[c["from_name"]] = degree.get(c["from_name"], 0) + 1
        degree[c["to_name"]] = degree.get(c["to_name"], 0) + 1
    print("\njunction degree (how many corridors meet there):")
    for name, d in sorted(degree.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<28} {d}")
    isolated = [j["name"] for j in junctions if j["name"] not in degree]
    if isolated:
        print(f"\nno corridor reaches: {', '.join(isolated)}")
    print(f"wrote {OUT} — identity only; distances and durations are fetched live")


if __name__ == "__main__":
    main()
