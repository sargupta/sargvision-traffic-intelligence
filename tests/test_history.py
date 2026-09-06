"""The corridor memory: its aggregates are honest, its percentiles are sane, its
persistence round-trips, and it stores nothing that could reconstruct a reading.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from packages.history.model import BIN_COUNT, Bucket, ObservationHistory
from packages.history.store import (
    MemoryHistoryStore,
    from_document,
    to_document,
)

TUE_6PM = datetime(2026, 9, 1, 18, 0)  # a Tuesday


class TestBucket:
    def test_percentile_never_below_the_minimum(self):
        # the float-binning bug this guards: 1.4/0.1 floors to bin 13, not 14
        b = Bucket()
        for _ in range(10):
            b.fold(1.4, congested=False, when=TUE_6PM)
        s = b.summary()
        assert s["p50"] >= s["min"] - 1e-9
        assert s["p95"] >= s["p50"]

    def test_percentiles_are_ordered_and_bracket_the_data(self):
        b = Bucket()
        for v in (1.0, 1.2, 1.4, 1.6, 1.8, 2.0):
            b.fold(v, congested=v >= 1.25, when=TUE_6PM)
        s = b.summary()
        assert s["min"] <= s["p50"] <= s["p85"] <= s["p95"] <= s["max"] + 0.1
        assert 0.0 <= s["congested_share"] <= 1.0

    def test_extreme_index_lands_in_the_top_bin_not_out_of_range(self):
        b = Bucket()
        b.fold(99.0, congested=True, when=TUE_6PM)
        assert sum(b.hist) == 1 and b.hist[BIN_COUNT - 1] == 1


class TestNowVsBaseline:
    def _corridor_with_history(self, index=1.3, n=30):
        h = ObservationHistory()
        for k in range(n):
            h.fold("C1", "Test Road", TUE_6PM + timedelta(weeks=k), index, index >= 1.25)
        return h

    def test_thin_history_is_admitted_not_guessed(self):
        h = ObservationHistory()
        h.fold("C1", "Test Road", TUE_6PM, 1.3, True)
        r = h.now_vs_baseline("C1", TUE_6PM, 2.0)
        assert r["verdict"] == "not enough history"
        assert r["confidence"] == "low"

    def test_a_spike_reads_as_worse_than_typical(self):
        h = self._corridor_with_history(index=1.2)
        # feed a little spread so std is non-zero
        for k in range(30, 40):
            h.fold("C1", "Test Road", TUE_6PM + timedelta(weeks=k), 1.25, False)
        r = h.now_vs_baseline("C1", TUE_6PM, 2.2)
        assert r["verdict"] == "worse than typical"
        assert r["z_score"] > 0

    def test_normal_reads_as_typical(self):
        h = self._corridor_with_history(index=1.2)
        for k in range(30, 40):
            h.fold("C1", "Test Road", TUE_6PM + timedelta(weeks=k), 1.25, False)
        r = h.now_vs_baseline("C1", TUE_6PM, 1.22)
        assert r["verdict"] == "typical for the hour"

    def test_unknown_corridor_is_handled(self):
        r = ObservationHistory().now_vs_baseline("NOPE", TUE_6PM, 1.5)
        assert r["verdict"] == "not enough history"


class TestTrendAndForecast:
    def _worsening(self):
        h = ObservationHistory()
        # 20 days, index climbing from 1.1 to 1.5
        for d in range(20):
            idx = 1.1 + d * 0.02
            h.fold("C1", "Test Road", TUE_6PM + timedelta(days=d), idx, idx >= 1.25)
        return h

    def test_trend_detects_worsening(self):
        tr = self._worsening().trend("C1")
        assert tr["direction"] == "worsening"
        assert tr["drift"] > 0

    def test_forecast_is_labelled_baseline_not_prediction(self):
        # build enough per-bucket history for the forecast hours to resolve
        h = ObservationHistory()
        base = datetime(2026, 9, 1, 12, 0)
        for wk in range(8):
            for hr in range(24):
                h.fold("C1", "Test Road", base.replace(hour=hr) + timedelta(weeks=wk), 1.3, True)
        fc = h.forecast("C1", base, hours=3)
        assert fc is not None and len(fc["steps"]) == 3
        assert "not a prediction" in fc["caveat"]
        assert fc["steps"][0]["expected"] is not None

    def test_forecast_admits_when_a_bucket_is_unlearned(self):
        h = ObservationHistory()
        h.fold("C1", "Test Road", TUE_6PM, 1.3, True)  # one reading only
        fc = h.forecast("C1", TUE_6PM, hours=2)
        assert all(s["expected"] is None for s in fc["steps"])


class TestRetention:
    def test_daily_rollups_are_capped(self):
        h = ObservationHistory()
        start = datetime(2026, 1, 1, 18, 0)
        for d in range(200):  # 200 days, retention is 120
            h.fold("C1", "Test Road", start + timedelta(days=d), 1.3, True)
        ch = h.corridors["C1"]
        assert len(ch.days) <= 121  # the coarse history honours a cache limit


class TestPersistence:
    def test_round_trips_through_a_document(self):
        h = ObservationHistory()
        for k in range(15):
            h.fold("C1", "Test Road", TUE_6PM + timedelta(weeks=k), 1.3 + (k % 3) * 0.1, True)
        doc = to_document(h.corridors["C1"])
        back = from_document(doc)
        assert back.observations() == h.corridors["C1"].observations()
        assert back.baseline(1, 18) == h.corridors["C1"].baseline(1, 18)

    def test_store_load_all_reconstructs_the_memory(self):
        store = MemoryHistoryStore()
        h = ObservationHistory()
        h.fold("C1", "Test Road", TUE_6PM, 1.3, True)
        store.save(h.corridors["C1"])
        loaded = store.load_all()
        assert "C1" in loaded.corridors

    def test_document_holds_no_raw_reading(self):
        # the compliance property: only aggregates leave the process
        h = ObservationHistory()
        h.fold("C1", "Test Road", TUE_6PM, 1.37, True)
        doc = to_document(h.corridors["C1"])
        # buckets are histograms + counters; no duration/second/timestamp field
        blob = str(doc)
        assert "duration" not in blob and "static_duration" not in blob
        bucket = next(iter(doc["buckets"].values()))
        assert set(bucket) <= {
            "n",
            "total",
            "total_sq",
            "min_index",
            "max_index",
            "hist",
            "congested_n",
            "last_seen",
        }


class TestCoverage:
    def test_coverage_states_the_compliance_boundary(self):
        h = ObservationHistory()
        h.fold("C1", "Test Road", TUE_6PM, 1.3, True)
        cov = h.coverage()
        assert cov["total_observations"] == 1
        assert "No raw travel-time" in cov["note"] or "no raw" in cov["note"].lower()
