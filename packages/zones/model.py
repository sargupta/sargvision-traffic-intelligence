"""Data-driven zone model for Siliguri.

The observations carry an origin point and a destination point and no route
between them. A zone system is the smallest honest abstraction that turns those
points into something an officer can talk about: not "grid cell 1485_4911" but
"Matigara to NJP Station".

**Zones are derived from the data, not drawn by hand.** Journey endpoints are
clustered by weighted k-means in a local metric projection. The number of zones
is not chosen for tidiness — it is the finest zoning the evidence can actually
support, meaning the largest k at which every zone still carries enough
endpoint observations for its movements to clear the publishing floor. That
criterion is a product requirement, not a statistical one: a zone nobody has
enough evidence about is worse than no zone at all.

Naming is a separate, auditable step (see `packages.zones.gazetteer`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl

from packages.zones.gazetteer import LANDMARKS, Landmark

# Siliguri sits near 26.7 N. One degree of latitude is ~111.32 km; one degree of
# longitude shrinks by cos(latitude). Projecting with fixed factors around a
# local origin keeps k-means working in metres over an area this small without
# pulling in a projection library.
LAT_ORIGIN = 26.7145
LON_ORIGIN = 88.4215
M_PER_DEG_LAT = 111_320.0
M_PER_DEG_LON = 111_320.0 * float(np.cos(np.radians(LAT_ORIGIN)))

SEED = 20190613  # the first day in the observation window; any fixed value would do

# A zone must hold at least this many endpoint observations. Below it, the
# movements into and out of that zone cannot reach a publishable sample.
MIN_ZONE_ENDPOINTS = 2_000

# A zone must also be nameable. If the nearest landmark to a cluster's centre is
# further than this, we would be printing a name the geography does not support
# — calling a cluster "Shivmandir" when its centre is six kilometres from
# Shivmandir is not a labelling inconvenience, it is a false statement on a map.
# Splitting further buys spatial resolution at the price of honest names, and
# the names are the reason the zones exist.
MAX_NAME_DISTANCE_M = 1_500

K_RANGE = range(4, 13)


def to_metres(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    return np.column_stack([(lat - LAT_ORIGIN) * M_PER_DEG_LAT, (lon - LON_ORIGIN) * M_PER_DEG_LON])


def to_degrees(xy: np.ndarray) -> np.ndarray:
    return np.column_stack(
        [xy[:, 0] / M_PER_DEG_LAT + LAT_ORIGIN, xy[:, 1] / M_PER_DEG_LON + LON_ORIGIN]
    )


def _kmeanspp(
    points: np.ndarray, weights: np.ndarray, k: int, rng: np.random.Generator
) -> np.ndarray:
    """k-means++ seeding, weighted by how many observations sit at each point."""
    centres = np.empty((k, 2))
    first = rng.choice(len(points), p=weights / weights.sum())
    centres[0] = points[first]

    closest = ((points - centres[0]) ** 2).sum(axis=1)
    for i in range(1, k):
        probs = closest * weights
        total = probs.sum()
        if total <= 0:
            centres[i] = points[rng.integers(len(points))]
        else:
            centres[i] = points[rng.choice(len(points), p=probs / total)]
        closest = np.minimum(closest, ((points - centres[i]) ** 2).sum(axis=1))
    return centres


def _lloyd(
    points: np.ndarray, weights: np.ndarray, k: int, rng: np.random.Generator, iters: int = 120
) -> tuple[np.ndarray, np.ndarray, float]:
    """Weighted Lloyd's algorithm. Returns centres, labels and inertia."""
    centres = _kmeanspp(points, weights, k, rng)
    labels = np.zeros(len(points), dtype=int)

    for _ in range(iters):
        d = ((points[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        new_labels = d.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            m = labels == j
            if not m.any():
                # An empty cluster is re-seeded onto the worst-served point so
                # k always means k.
                worst = int((d.min(axis=1) * weights).argmax())
                centres[j] = points[worst]
                continue
            w = weights[m]
            centres[j] = (points[m] * w[:, None]).sum(axis=0) / w.sum()

    d = ((points[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
    labels = d.argmin(axis=1)
    inertia = float((d.min(axis=1) * weights).sum())
    return centres, labels, inertia


@dataclass
class ZoneModel:
    zones: pl.DataFrame
    k: int
    search: list[dict] = field(default_factory=list)

    @property
    def centres_deg(self) -> np.ndarray:
        return self.zones.select("lat", "lon").to_numpy()


def _endpoint_cloud(df: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Every journey endpoint, deduplicated to unique coordinates with weights.

    Origins and destinations are pooled: a place is a place regardless of which
    end of a trip it sat on, and clustering them separately would give two
    different geographies for the same city.
    """
    stacked = pl.concat(
        [
            df.select(pl.col("lat_orig").alias("lat"), pl.col("lon_orig").alias("lon")),
            df.select(pl.col("lat_dest").alias("lat"), pl.col("lon_dest").alias("lon")),
        ]
    )
    # group_by does not promise an order. Without the sort the point array
    # comes out shuffled between runs, k-means++ seeds differently and the
    # clustering lands on a different local optimum each time — which silently
    # changes the zone count. Sorting makes the whole pipeline reproducible.
    counted = stacked.group_by("lat", "lon").len().rename({"len": "w"}).sort(["lat", "lon"])
    pts = to_metres(
        counted["lat"].to_numpy().astype(float), counted["lon"].to_numpy().astype(float)
    )
    return pts, counted["w"].to_numpy().astype(float)


def _name_zones(centres_deg: np.ndarray) -> list[tuple[str, float, str]]:
    """Label each centre with its nearest unused landmark.

    Assigning greedily by distance, closest pair first, stops two clusters from
    claiming the same name and leaves the better-matched cluster with it.
    """
    pairs: list[tuple[float, int, int]] = []
    for zi, (lat, lon) in enumerate(centres_deg):
        for li, mark in enumerate(LANDMARKS):
            d = float(np.hypot((lat - mark.lat) * M_PER_DEG_LAT, (lon - mark.lon) * M_PER_DEG_LON))
            pairs.append((d, zi, li))
    pairs.sort()

    out: dict[int, tuple[str, float, str]] = {}
    used_landmarks: set[int] = set()
    for d, zi, li in pairs:
        if zi in out or li in used_landmarks:
            continue
        mark: Landmark = LANDMARKS[li]
        out[zi] = (mark.name, round(d), mark.kind)
        used_landmarks.add(li)

    return [out.get(i, (f"Zone {i}", -1.0, "unnamed")) for i in range(len(centres_deg))]


def build_zones(
    df: pl.DataFrame,
    min_endpoints: int = MIN_ZONE_ENDPOINTS,
    max_name_distance: float = MAX_NAME_DISTANCE_M,
    k_range: range = K_RANGE,
) -> ZoneModel:
    points, weights = _endpoint_cloud(df)
    rng_seed = SEED

    search: list[dict] = []
    best: tuple[int, np.ndarray, np.ndarray] | None = None

    for k in k_range:
        rng = np.random.default_rng(rng_seed)
        centres, labels, inertia = _lloyd(points, weights, k, rng)
        sizes = np.array([weights[labels == j].sum() for j in range(k)])
        distances = [d for _, d, _ in _name_zones(to_degrees(centres))]
        worst_name = max(distances)
        viable = bool(sizes.min() >= min_endpoints and worst_name <= max_name_distance)
        search.append(
            {
                "k": k,
                "inertia": round(inertia / 1e9, 3),
                "min_zone_endpoints": int(sizes.min()),
                "max_zone_endpoints": int(sizes.max()),
                "worst_name_distance_m": int(worst_name),
                "median_name_distance_m": int(np.median(distances)),
                "viable": viable,
            }
        )
        # Keep the largest viable k: the finest zoning the evidence supports.
        if viable:
            best = (k, centres, labels)

    if best is None:
        raise ValueError(
            f"No zone count in {k_range} gives every zone {min_endpoints}+ endpoints "
            f"and a landmark within {max_name_distance:.0f} m. Widen the observation "
            "window, add landmarks to the gazetteer, or relax a threshold explicitly."
        )

    k, centres, _ = best
    centres_deg = to_degrees(centres)
    named = _name_zones(centres_deg)

    # Report each zone's share of endpoints at the chosen k.
    rng = np.random.default_rng(rng_seed)
    _, labels, _ = _lloyd(points, weights, k, rng)
    sizes = [int(weights[labels == j].sum()) for j in range(k)]

    zones = pl.DataFrame(
        {
            "zone_id": [f"SIL_Z{j:02d}" for j in range(k)],
            "zone_name": [n[0] for n in named],
            "name_distance_m": [n[1] for n in named],
            "landmark_kind": [n[2] for n in named],
            "lat": centres_deg[:, 0].round(5),
            "lon": centres_deg[:, 1].round(5),
            "endpoint_observations": sizes,
        }
    ).sort("zone_name")

    return ZoneModel(zones=zones, k=k, search=search)


def assign(df: pl.DataFrame, model: ZoneModel) -> pl.DataFrame:
    """Attach an origin zone and a destination zone to every observation."""
    centres = to_metres(model.centres_deg[:, 0], model.centres_deg[:, 1])
    ids = model.zones["zone_id"].to_list()
    names = model.zones["zone_name"].to_list()

    def nearest(lat_col: str, lon_col: str) -> tuple[list[str], list[str]]:
        pts = to_metres(df[lat_col].to_numpy().astype(float), df[lon_col].to_numpy().astype(float))
        d = ((pts[:, None, :] - centres[None, :, :]) ** 2).sum(axis=2)
        idx = d.argmin(axis=1)
        return [ids[i] for i in idx], [names[i] for i in idx]

    o_id, o_name = nearest("lat_orig", "lon_orig")
    d_id, d_name = nearest("lat_dest", "lon_dest")

    return df.with_columns(
        pl.Series("origin_zone", o_id),
        pl.Series("origin_zone_name", o_name),
        pl.Series("dest_zone", d_id),
        pl.Series("dest_zone_name", d_name),
    ).with_columns(
        (pl.col("origin_zone") + pl.lit("__") + pl.col("dest_zone")).alias("movement_id"),
        (pl.col("origin_zone_name") + pl.lit(" → ") + pl.col("dest_zone_name")).alias(
            "movement_name"
        ),
    )
