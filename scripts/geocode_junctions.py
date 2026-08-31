"""Resolve Siliguri's named junctions to coordinates.

Caching latitude and longitude is the one thing the Maps Service Specific Terms
explicitly permit (S19.3), which is precisely why the junction gazetteer is
built this way and travel times are not.

Every result is written with the formatted address Google returned and the
location type, so a wrong match is visible rather than silent. A junction that
geocodes to a different city is a bug we can see.

Run:  GEO_API_KEY=... .venv/bin/python scripts/geocode_junctions.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path("data/curated/junctions.json")
KEY = os.environ.get("GEO_API_KEY", "")

# Siliguri's bounding box, used to reject a match that lands somewhere else.
BBOX = {"south": 26.60, "north": 26.83, "west": 88.30, "east": 88.55}

# V/C ratios from CMP 2011, published in Siliguri CDP 2041. Accident evidence
# from Roy, Mohammadi & Roy, Geographies 6(2):55 (2026).
JUNCTIONS: list[dict] = [
    {
        "name": "Jalpai More",
        "query": "Jalpai More, Siliguri, West Bengal",
        "vc": 1.14,
        "control": "NON_SIGNALISED",
    },
    {
        "name": "Mahananda Bridge",
        "query": "Mahananda Bridge, Hill Cart Road, Siliguri",
        "vc": 1.13,
        "control": "SIGNALISED",
    },
    {
        "name": "Champasari More",
        "query": "Champasari More, Siliguri, West Bengal",
        "vc": 1.09,
        "control": "SIGNALISED",
    },
    {
        "name": "Darjeeling More",
        "query": "Darjeeling More, Siliguri, West Bengal",
        "vc": 1.03,
        "control": "SIGNALISED",
    },
    {
        "name": "Pani Tanki More",
        "query": "Panitanki More, Siliguri, West Bengal",
        "vc": 0.81,
        "control": "SIGNALISED",
    },
    {
        "name": "Check Post More",
        "query": "Checkpost More, Siliguri, West Bengal",
        "vc": 0.77,
        "control": "SIGNALISED",
    },
    {
        "name": "Jhankaar More",
        "query": "Jhankar More, Hyderpara, Siliguri",
        "vc": 0.75,
        "control": "MIXED",
    },
    {
        "name": "Wall Ford Bypass Crossing",
        "query": "Eastern Bypass, Siliguri, West Bengal",
        "vc": 0.69,
        "control": "NON_SIGNALISED",
    },
    {
        "name": "Air View More",
        "query": "Air View More, Siliguri, West Bengal",
        "vc": 0.60,
        "control": "SIGNALISED",
    },
    {
        "name": "Thana More",
        "query": "Thana More, Siliguri, West Bengal",
        "vc": 0.52,
        "control": "SIGNALISED",
    },
    {
        "name": "Wall Ford Sevoke Crossing",
        "query": "Sevoke Road, Siliguri, West Bengal",
        "vc": 0.48,
        "control": "SIGNALISED",
    },
    {
        "name": "Sevoke More",
        "query": "Sevoke More, Siliguri, West Bengal",
        "vc": 0.41,
        "control": "SIGNALISED",
    },
    {
        "name": "Venus More",
        "query": "Venus More, Siliguri, West Bengal",
        "vc": 0.39,
        "control": "SIGNALISED",
    },
    {
        "name": "Ashighar More",
        "query": "Ashighar More, Siliguri, West Bengal",
        "vc": 0.38,
        "control": "NON_SIGNALISED",
    },
    {
        "name": "Mallaguri Crossing",
        "query": "Mallaguri, Siliguri, West Bengal",
        "vc": 0.08,
        "control": "GRADE_SEPARATED",
    },
    # Not in the CMP table but named repeatedly in the local literature.
    {
        "name": "Court More",
        "query": "Court More, Siliguri, West Bengal",
        "vc": None,
        "control": "UNKNOWN",
    },
    {
        "name": "Naukaghat",
        "query": "Naukaghat, Siliguri, West Bengal",
        "vc": None,
        "control": "UNKNOWN",
    },
    {
        "name": "NJP Station",
        "query": "New Jalpaiguri Railway Station, Siliguri",
        "vc": None,
        "control": "UNKNOWN",
    },
    {
        "name": "Siliguri Junction",
        "query": "Siliguri Junction Railway Station, West Bengal",
        "vc": None,
        "control": "UNKNOWN",
    },
    {
        "name": "Bagdogra Airport",
        "query": "Bagdogra Airport, West Bengal",
        "vc": None,
        "control": "UNKNOWN",
    },
]


def geocode(query: str) -> dict | None:
    url = "https://maps.googleapis.com/maps/api/geocode/json?" + urllib.parse.urlencode(
        {
            "address": query,
            "key": KEY,
            "region": "in",
            "bounds": f"{BBOX['south']},{BBOX['west']}|{BBOX['north']},{BBOX['east']}",
        }
    )
    with urllib.request.urlopen(url, timeout=20) as r:
        payload = json.loads(r.read())
    if payload.get("status") != "OK" or not payload.get("results"):
        return None
    best = payload["results"][0]
    loc = best["geometry"]["location"]
    return {
        "lat": round(loc["lat"], 6),
        "lon": round(loc["lng"], 6),
        "formatted_address": best.get("formatted_address"),
        "location_type": best["geometry"].get("location_type"),
        "place_id": best.get("place_id"),
        "types": best.get("types", []),
    }


# Google returns the name the place is registered under, which is not always the
# name an officer uses. These are the same place; without them the check reports
# a weak pin for a perfectly good match.
ALIASES: dict[str, tuple[str, ...]] = {
    "NJP Station": ("new jalpaiguri", "njp"),
    "Siliguri Junction": ("siliguri jn", "siliguri junction"),
    "Pani Tanki More": ("panitanki", "pani tanki"),
    "Check Post More": ("checkpost", "check post"),
    "Jhankaar More": ("jhankar", "jhankaar"),
    "Mallaguri Crossing": ("mallaguri",),
    "Naukaghat": ("nauka ghat", "naukaghat"),
    "Wall Ford Sevoke Crossing": ("sevoke rd", "sevoke road"),
    "Wall Ford Bypass Crossing": ("eastern bypass", "bypass"),
    "Bagdogra Airport": ("bagdogra",),
}


def match_quality(name: str, hit: dict) -> tuple[str, str]:
    """How much to trust this pin.

    A geocoder always returns something. Putting a confident marker on an
    officer's map because the API answered is the same false precision this
    product exists to avoid, so every pin carries how it was matched.

    CONFIRMED  the returned address names the junction, at rooftop precision
    NEAR       rooftop or centre precision, but the name did not come back
    ROAD_ONLY  matched a road or locality, not the junction itself
    """
    address = (hit.get("formatted_address") or "").lower()
    head = name.lower().replace(" more", "").replace(" crossing", "").strip()
    named = head in address or any(a in address for a in ALIASES.get(name, ()))
    precise = hit.get("location_type") in ("ROOFTOP", "GEOMETRIC_CENTER")

    if named and hit.get("location_type") == "ROOFTOP":
        return "CONFIRMED", "address names the junction, rooftop precision"
    if named and precise:
        return "NEAR", "address names the junction, centre precision"
    if precise:
        return "ROAD_ONLY", "matched a road or place, not the junction by name"
    return "ROAD_ONLY", "approximate match only"


def main() -> None:
    if not KEY:
        sys.exit("GEO_API_KEY is not set")

    out, suspect = [], []
    for j in JUNCTIONS:
        hit = geocode(j["query"])
        time.sleep(0.06)
        if hit is None:
            suspect.append((j["name"], "NO RESULT"))
            continue
        inside = (
            BBOX["south"] <= hit["lat"] <= BBOX["north"]
            and BBOX["west"] <= hit["lon"] <= BBOX["east"]
        )
        quality, why = match_quality(j["name"], hit)
        record = {
            "junction_id": "J_" + j["name"].upper().replace(" ", "_"),
            "name": j["name"],
            "vc_ratio": j["vc"],
            "control": j["control"],
            "in_siliguri_bbox": inside,
            "match_quality": quality,
            "match_note": why,
            **hit,
        }
        out.append(record)
        if not inside or quality == "ROAD_ONLY":
            suspect.append((j["name"], why if inside else "outside Siliguri"))
        print(
            f"{j['name']:<28} {hit['lat']:.5f},{hit['lon']:.5f}  "
            f"{quality:<10} {(hit['formatted_address'] or '')[:46]}"
        )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {len(out)} junctions to {OUT}")
    by_quality: dict[str, int] = {}
    for r in out:
        by_quality[r["match_quality"]] = by_quality.get(r["match_quality"], 0) + 1
    print(f"match quality: {by_quality}")
    if suspect:
        print(f"\n{len(suspect)} carry a weak pin and must render as approximate:")
        for name, why in suspect:
            print(f"  {name}: {why}")


if __name__ == "__main__":
    main()
