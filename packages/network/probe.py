"""Live corridor observation via the Routes API.

One request per corridor returns everything the product needs and nothing it
must not keep:

    duration          travel time in current traffic
    staticDuration    travel time in typical conditions
    speedReadingIntervals  NORMAL / SLOW / TRAFFIC_JAM along the polyline
    polyline          the route geometry those intervals index into

The congestion index is `duration / staticDuration`. It needs no history, which
is what makes this product work on its first request and what makes it
compliant: there is nothing to accumulate.

**Choke points are the point of this module.** A corridor-level index says Hill
Cart Road is slow. The speed intervals say *which 300 metres of it* is slow, at
a real coordinate. That is the difference between telling an officer their city
is congested and telling them where to send someone.

Retention: coordinates are cached (Maps Service Specific Terms permit lat/lng).
Durations are held in memory for a bounded window and never written to disk.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime

from packages.network.model import Corridor, Junction

ENDPOINT = "https://routes.googleapis.com/directions/v2:computeRoutes"

FIELD_MASK = ",".join(
    (
        "routes.duration",
        "routes.staticDuration",
        "routes.distanceMeters",
        "routes.description",
        "routes.polyline.encodedPolyline",
        "routes.travelAdvisory.speedReadingIntervals",
    )
)

# Google's own ordering, worst last.
SPEED_RANK = {"NORMAL": 0, "SLOW": 1, "TRAFFIC_JAM": 2}


def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Google's encoded polyline algorithm.

    Implemented here rather than pulled in as a dependency: it is thirty lines,
    it is a published format, and the alternative is a package we would have to
    trust for the geometry every choke point is placed on.
    """
    points: list[tuple[float, float]] = []
    index = lat = lon = 0
    while index < len(encoded):
        for target in ("lat", "lon"):
            shift = result = 0
            while True:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if target == "lat":
                lat += delta
            else:
                lon += delta
        points.append((lat / 1e5, lon / 1e5))
    return points


@dataclass(frozen=True)
class ChokePoint:
    """A stretch of a corridor that is slower than the rest of it."""

    severity: str  # SLOW | TRAFFIC_JAM
    start: tuple[float, float]
    end: tuple[float, float]
    midpoint: tuple[float, float]
    length_m: float
    share_of_corridor: float  # 0-1, how much of the route this is

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "start": list(self.start),
            "end": list(self.end),
            "midpoint": list(self.midpoint),
            "length_m": round(self.length_m),
            "share_of_corridor": round(self.share_of_corridor, 3),
        }


@dataclass(frozen=True)
class SpeedRun:
    """One stretch of the route at a single traffic classification.

    The whole polyline, split at every change of speed. This is what makes a
    map show the road rather than a line between two dots: the geometry is the
    carriageway Google routed over, and the colour is what it measured on each
    part of it.
    """

    speed: str  # NORMAL | SLOW | TRAFFIC_JAM
    path: tuple[tuple[float, float], ...]
    length_m: float

    def as_dict(self) -> dict:
        return {
            "speed": self.speed,
            # [lon, lat] — GeoJSON and deck.gl order, so the client never has
            # to remember which way round a coordinate pair is.
            "path": [[round(lon, 6), round(lat, 6)] for lat, lon in self.path],
            "length_m": round(self.length_m),
        }


@dataclass(frozen=True)
class CorridorReading:
    corridor_id: str
    observed_at: datetime
    duration_s: float
    static_duration_s: float
    distance_m: float
    roads: str
    choke_points: tuple[ChokePoint, ...] = field(default_factory=tuple)
    speed_runs: tuple[SpeedRun, ...] = field(default_factory=tuple)
    polyline: str = ""

    @property
    def congestion_index(self) -> float:
        """Current travel time against typical travel time.

        Above 1.0 is slower than typical. This is a comparison against Google's
        modelled expectation, not against a measured empty road — it can and
        does read below 1.0, and the interface must not call it "free flow".
        """
        return self.duration_s / self.static_duration_s if self.static_duration_s else 1.0

    @property
    def excess_minutes(self) -> float:
        return (self.duration_s - self.static_duration_s) / 60

    @property
    def worst_choke(self) -> ChokePoint | None:
        if not self.choke_points:
            return None
        return max(
            self.choke_points,
            key=lambda c: (SPEED_RANK.get(c.severity, 0), c.length_m),
        )

    @property
    def mean_speed_kmh(self) -> float:
        return (self.distance_m / 1000) / (self.duration_s / 3600) if self.duration_s else 0.0

    def as_dict(self, geometry: bool = True) -> dict:
        out = {
            "corridor_id": self.corridor_id,
            "observed_at": self.observed_at.isoformat(timespec="seconds"),
            "duration_minutes": round(self.duration_s / 60, 1),
            "typical_minutes": round(self.static_duration_s / 60, 1),
            "excess_minutes": round(self.excess_minutes, 1),
            "congestion_index": round(self.congestion_index, 3),
            "speed_kmh": round(self.mean_speed_kmh, 1),
            "distance_m": round(self.distance_m),
            "roads": self.roads,
            "choke_points": [c.as_dict() for c in self.choke_points],
        }
        if geometry:
            out["runs"] = [r.as_dict() for r in self.speed_runs]
        return out


def _metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    import math

    lat = math.radians((a[0] + b[0]) / 2)
    dx = (b[0] - a[0]) * 111_320.0
    dy = (b[1] - a[1]) * 111_320.0 * math.cos(lat)
    return math.hypot(dx, dy)


class RoutesProbe:
    """Reads one corridor's current condition.

    `retains_durations` is False and the collector checks it. Nothing in this
    class may be wired to a durable store.
    """

    name = "google-routes"
    is_live = True
    retains_durations = False

    def __init__(self, api_key: str, timeout: float = 20.0):
        if not api_key:
            raise ValueError("RoutesProbe needs an API key")
        self.api_key = api_key
        self.timeout = timeout

    def read(
        self, corridor: Corridor, origin: Junction, destination: Junction, at: datetime
    ) -> CorridorReading | None:
        body = {
            "origin": {"location": {"latLng": {"latitude": origin.lat, "longitude": origin.lon}}},
            "destination": {
                "location": {"latLng": {"latitude": destination.lat, "longitude": destination.lon}}
            },
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE_OPTIMAL",
            "extraComputations": ["TRAFFIC_ON_POLYLINE"],
            "polylineQuality": "HIGH_QUALITY",
            "languageCode": "en-IN",
            "regionCode": "IN",
        }
        request = urllib.request.Request(
            ENDPOINT,
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        routes = payload.get("routes") or []
        if not routes:
            return None
        route = routes[0]

        encoded = (route.get("polyline") or {}).get("encodedPolyline", "")
        points = decode_polyline(encoded) if encoded else []
        intervals = (route.get("travelAdvisory") or {}).get("speedReadingIntervals", []) or []

        total_m = float(route.get("distanceMeters") or 0)

        # Split the decoded path at every change of classification. Intervals
        # that Google does not classify are treated as NORMAL rather than
        # dropped, so the drawn road has no gaps in it.
        runs: list[SpeedRun] = []
        if points:
            covered: list[tuple[int, int, str]] = []
            for interval in intervals:
                lo = int(interval.get("startPolylinePointIndex", 0))
                hi = int(interval.get("endPolylinePointIndex", lo))
                if hi > lo:
                    covered.append((lo, min(hi, len(points) - 1), interval.get("speed", "NORMAL")))
            covered.sort()
            cursor = 0
            filled: list[tuple[int, int, str]] = []
            for lo, hi, speed in covered:
                if lo > cursor:
                    filled.append((cursor, lo, "NORMAL"))
                filled.append((lo, hi, speed))
                cursor = hi
            if cursor < len(points) - 1:
                filled.append((cursor, len(points) - 1, "NORMAL"))
            if not filled:
                filled = [(0, len(points) - 1, "NORMAL")]

            for lo, hi, speed in filled:
                span = points[lo : hi + 1]
                if len(span) < 2:
                    continue
                runs.append(
                    SpeedRun(
                        speed=speed,
                        path=tuple(span),
                        length_m=sum(_metres(span[i], span[i + 1]) for i in range(len(span) - 1)),
                    )
                )

        chokes: list[ChokePoint] = []
        for interval in intervals:
            speed = interval.get("speed")
            if speed not in ("SLOW", "TRAFFIC_JAM"):
                continue
            lo = int(interval.get("startPolylinePointIndex", 0))
            hi = int(interval.get("endPolylinePointIndex", lo))
            if not points or hi <= lo or hi >= len(points):
                continue
            span = points[lo : hi + 1]
            length = sum(_metres(span[i], span[i + 1]) for i in range(len(span) - 1))
            mid = span[len(span) // 2]
            chokes.append(
                ChokePoint(
                    severity=speed,
                    start=span[0],
                    end=span[-1],
                    midpoint=mid,
                    length_m=length,
                    share_of_corridor=(length / total_m) if total_m else 0.0,
                )
            )

        return CorridorReading(
            corridor_id=corridor.corridor_id,
            observed_at=at,
            duration_s=float(str(route["duration"]).rstrip("s")),
            static_duration_s=float(str(route["staticDuration"]).rstrip("s")),
            distance_m=total_m,
            roads=route.get("description") or "",
            choke_points=tuple(chokes),
            speed_runs=tuple(runs),
            polyline=encoded,
        )

    def provenance(self) -> dict:
        return {
            "source": self.name,
            "is_live": True,
            "retains_durations": False,
            "note": (
                "Travel times are held in memory only. Maps Service Specific Terms "
                "permit caching latitude and longitude; durations are not retained."
            ),
        }
