"""Invariants the analytics engine must not lose."""

from __future__ import annotations

import polars as pl
import pytest

from packages.analytics import anomalies as anom
from packages.analytics import baselines as base
from packages.analytics import patterns as pat
from packages.analytics import reliability as rel
from packages.zones.gazetteer import LANDMARKS
from packages.zones.model import MAX_NAME_DISTANCE_M, assign, build_zones


def _synthetic(n_per_bin: int = 60) -> pl.DataFrame:
    """Two movements, one hour, known distances and paces."""
    common = dict(
        movement_id="A__B", movement_name="A → B", day_type="WEEKDAY", hour=9,
        origin_zone="SIL_Z00", origin_zone_name="A", dest_zone="SIL_Z01",
        dest_zone_name="B", delay_pct=20.0, tti=1.2, speed_kmh=30.0,
        origin_lat=26.71, origin_lon=88.42, dest_lat=26.72, dest_lon=88.43,
    )
    rows = []
    for _ in range(n_per_bin):
        # A short trip and a long trip at the SAME pace: 120 s/km.
        rows.append(common | dict(distance_m=1000.0, traffic_seconds=120.0,
                                  freeflow_seconds=100.0, delay_seconds=20.0))
        rows.append(common | dict(distance_m=8000.0, traffic_seconds=960.0,
                                  freeflow_seconds=800.0, delay_seconds=160.0))
    return pl.DataFrame(rows)


class TestPaceBaselines:
    """The bug this class exists to prevent: baselines on raw journey time.

    Zone movements pool trips of very different lengths. A baseline on seconds
    makes every long trip look anomalous, which measures geography, not delay.
    """

    def test_long_trip_at_normal_pace_is_not_an_anomaly(self):
        obs = _synthetic()
        baselines = base.build(obs, min_samples=30)
        scored = anom.score(obs, baselines)

        assert scored.height == obs.height, "every observation should be scorable"
        # Both the 1 km and the 8 km trip run at 120 s/km, so neither deviates.
        assert scored["deviation_pct"].abs().max() < 1e-6
        assert (scored["severity"] == "EXPECTED").all()

    def test_slow_trip_is_an_anomaly_regardless_of_length(self):
        obs = _synthetic()
        # One long trip at double the normal pace.
        slow = obs.head(1).with_columns(
            pl.lit(8000.0).alias("distance_m"),
            pl.lit(1920.0).alias("traffic_seconds"),  # 240 s/km
        )
        baselines = base.build(obs, min_samples=30)
        scored = anom.score(pl.concat([obs, slow]), baselines)
        worst = scored.sort("deviation_pct", descending=True).head(1)

        assert worst["deviation_pct"][0] == pytest.approx(100.0, abs=0.01)
        assert worst["severity"][0] == "CRITICAL"

    def test_expected_minutes_scales_with_this_journey(self):
        """"Expected 18 min" must mean 18 for THIS trip, not for the average trip."""
        obs = _synthetic()
        baselines = base.build(obs, min_samples=30)
        scored = anom.score(obs, baselines)

        short = scored.filter(pl.col("distance_m") == 1000.0).head(1)
        long_ = scored.filter(pl.col("distance_m") == 8000.0).head(1)
        assert short["expected_minutes"][0] == pytest.approx(2.0, abs=0.05)
        assert long_["expected_minutes"][0] == pytest.approx(16.0, abs=0.05)


class TestPublishingFloor:
    def test_bins_below_the_floor_are_dropped_not_smoothed(self):
        obs = _synthetic(n_per_bin=5)  # 10 rows in one bin
        assert base.build(obs, min_samples=30).height == 0

    def test_unscorable_observations_are_dropped_not_guessed(self):
        obs = _synthetic()
        baselines = base.build(obs, min_samples=30)
        orphan = obs.head(1).with_columns(pl.lit(3).cast(obs.schema["hour"]).alias("hour"))
        scored = anom.score(pl.concat([obs, orphan]), baselines)
        assert scored.height == obs.height


class TestZoneModel:
    @pytest.fixture(scope="class")
    def observations(self) -> pl.DataFrame:
        return pl.read_parquet("data/processed/siliguri_observations.parquet")

    def test_zoning_is_reproducible(self, observations):
        a = build_zones(observations)
        b = build_zones(observations)
        assert a.k == b.k
        assert a.zones["zone_name"].to_list() == b.zones["zone_name"].to_list()
        assert a.zones["lat"].to_list() == b.zones["lat"].to_list()

    def test_every_zone_is_honestly_named(self, observations):
        zones = build_zones(observations).zones
        assert zones["name_distance_m"].max() <= MAX_NAME_DISTANCE_M
        assert zones["zone_name"].n_unique() == zones.height

    def test_names_come_from_the_gazetteer(self, observations):
        zones = build_zones(observations).zones
        known = {m.name for m in LANDMARKS}
        assert set(zones["zone_name"].to_list()) <= known

    def test_every_observation_gets_both_zones(self, observations):
        zoned = assign(observations, build_zones(observations))
        assert zoned.filter(pl.col("origin_zone").is_null()).height == 0
        assert zoned.filter(pl.col("dest_zone").is_null()).height == 0
        assert zoned["movement_id"].n_unique() <= build_zones(observations).k ** 2


class TestReliability:
    def test_buffer_is_length_independent(self):
        """Two movements with identical pace spread must score identically,
        even when one is eight times longer than the other."""
        rows = []
        for i in range(300):
            pace = 100.0 + (i % 30) * 2  # identical spread for both
            rows.append(dict(movement_id="SHORT", movement_name="s", origin_zone="A",
                             origin_zone_name="A", dest_zone="B", dest_zone_name="B",
                             distance_m=1000.0, traffic_seconds=pace * 1.0,
                             speed_kmh=3600.0 / pace))
            rows.append(dict(movement_id="LONG", movement_name="l", origin_zone="A",
                             origin_zone_name="A", dest_zone="B", dest_zone_name="B",
                             distance_m=8000.0, traffic_seconds=pace * 8.0,
                             speed_kmh=3600.0 / pace))
        scored = rel.score(pl.DataFrame(rows), min_samples=100)
        buffers = dict(zip(scored["movement_id"], scored["buffer_pct"]))
        assert buffers["SHORT"] == pytest.approx(buffers["LONG"], abs=1e-9)

    def test_bands_are_ordered(self):
        b = rel.Bands()
        assert b.classify(b.reliable - 1) == "HIGHLY_RELIABLE"
        assert b.classify(b.reliable + 1) == "MODERATELY_RELIABLE"
        assert b.classify(b.moderate + 1) == "UNPREDICTABLE"


class TestPatterns:
    def test_hours_below_the_bin_floor_are_not_plotted(self):
        obs = _synthetic(n_per_bin=5).with_columns(pl.lit(0).alias("day_of_week"))
        assert pat.by_hour(obs).height == 0

    def test_congested_flag_follows_the_stated_cut(self):
        obs = _synthetic().with_columns(pl.lit(0).alias("day_of_week"))
        hourly = pat.by_hour(obs)
        assert hourly["median_tti"][0] == pytest.approx(1.2)
        assert bool(hourly["congested"][0]) is (1.2 >= pat.CONGESTED_TTI)


class TestSeverityThresholds:
    def test_classification_boundaries(self):
        t = anom.Thresholds()
        assert t.classify(t.critical) == "CRITICAL"
        assert t.classify(t.high) == "HIGH"
        assert t.classify(t.moderate) == "MODERATE"
        assert t.classify(t.moderate - 0.01) == "EXPECTED"

    def test_hysteresis_sits_below_entry(self):
        t = anom.Thresholds()
        assert t.resolve < t.moderate
