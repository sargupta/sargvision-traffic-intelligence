"""Application service — the only thing the API talks to.

    API -> Application Service -> Domain/Analytics -> Provider -> Data Store

Never API -> LLM -> Database. The Copilot's tools call this service, exactly as the
HTTP routes do, so the AI can reach nothing the API cannot.
"""
from __future__ import annotations

from datetime import datetime

import polars as pl

from packages.analytics import anomalies, baselines
from packages.contracts.metric import Metric
from packages.domain.models import CorridorImportance
from packages.intelligence.alert_density import DensityReading
from packages.intelligence.priority import score
from packages.providers.historical import HistoricalProvider
from packages.replay.clock import ReplaySession

MIN_CORRIDOR_OBS = 300


class TrafficIntelligenceService:
    def __init__(self, provider: HistoricalProvider | None = None) -> None:
        self.provider = provider or HistoricalProvider()
        self._scored: pl.DataFrame | None = None
        self._baselines: pl.DataFrame | None = None

    # ---- internals -------------------------------------------------------
    def _prepared(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        if self._scored is None:
            raw = self.provider.fetch_observations(datetime(2019, 1, 1), datetime(2020, 1, 1))
            df = baselines.prepare(raw)
            counts = df.group_by("corridor_id").len()
            keep = counts.filter(pl.col("len") >= MIN_CORRIDOR_OBS)["corridor_id"]
            df = df.filter(pl.col("corridor_id").is_in(keep))
            self._baselines = baselines.build(df)
            self._scored = anomalies.score(df, self._baselines)
        return self._scored, self._baselines

    def _provenance(self) -> dict:
        return self.provider.provenance()

    # ---- product APIs ----------------------------------------------------
    def priorities(self, limit: int = 10) -> list[dict]:
        """What needs attention? Ranked by operational priority, not by severity."""
        scored, _ = self._prepared()
        worst = (
            scored.filter(pl.col("deviation_pct") >= anomalies.SILIGURI.moderate)
            .group_by("corridor_id")
            .agg(
                pl.col("deviation_pct").max().alias("peak_deviation_pct"),
                pl.len().alias("occurrences"),
            )
            .sort("peak_deviation_pct", descending=True)
            .head(limit)
        )
        out = []
        for row in worst.iter_rows(named=True):
            value, band = score(row["peak_deviation_pct"], 30.0, CorridorImportance.NORMAL)
            out.append({
                "corridor_id": row["corridor_id"],
                "peak_deviation_pct": round(row["peak_deviation_pct"], 1),
                "occurrences": row["occurrences"],
                "severity": anomalies.SILIGURI.classify(row["peak_deviation_pct"]).value,
                "priority": band.value,
                "priority_score": value,
            })
        return out

    def city_summary(self) -> dict:
        scored, base = self._prepared()
        return {
            "mode": "HISTORICAL_REPLAY" if not self.provider.is_live else "LIVE",
            "is_live": self.provider.is_live,
            "observations_scored": scored.height,
            "baseline_bins": base.height,
            "corridors": scored["corridor_id"].n_unique(),
            "operational_days": scored["date"].n_unique(),
            "provenance": self._provenance(),
        }

    def alert_density(self) -> list[dict]:
        scored, _ = self._prepared()
        days = scored["date"].n_unique()
        out = []
        for threshold in (anomalies.SILIGURI.moderate, anomalies.SILIGURI.high,
                          anomalies.SILIGURI.critical):
            n = scored.filter(pl.col("deviation_pct") >= threshold).height
            r = DensityReading(threshold_pct=threshold, events=n, days=days)
            out.append({"threshold_pct": threshold, "events": n,
                        "per_day": r.per_day, "status": r.status})
        return out

    def city_insights(self) -> list[Metric]:
        """Strategic intelligence. Every number carries its limitation.

        NOTE: computed over ALL prepared observations, not the scored subset. Scoring
        requires a baseline bin, which restricts to corridors dense enough to have one.
        A "city median" computed on that subset would be the median of the 32 best-observed
        corridors, which is a different quantity and would silently mislabel itself.
        """
        full = baselines.prepare(
            self.provider.fetch_observations(datetime(2019, 1, 1), datetime(2020, 1, 1))
        )
        prov = self._provenance()
        hourly = (
            full.group_by("hour")
            .agg(pl.col("tti").median().alias("tti"))
            .sort("tti", descending=True)
        )
        peak_hour = int(hourly["hour"][0])
        return [
            Metric(
                name="peak_hour", value=f"{peak_hour:02d}:00", unit="",
                definition="Hour with the highest median travel time index.",
                source=prov["source"],
                derivation="Median TTI grouped by hour across all 101,418 prepared "
                           "observations (not the scored subset).",
                limitation=prov["limitation"],
            ),
            Metric(
                name="median_speed", value=round(full["speed_kmh"].median(), 2), unit="km/h",
                definition="Median observed travel speed across all prepared observations.",
                source=prov["source"],
                derivation="distance_m/1000 over traffic_seconds/3600, median over all "
                           "101,418 valid primary-route observations.",
                limitation="City-wide across mixed trip lengths; not corridor-specific. "
                           + prov["limitation"],
            ),
        ]

    def replay(self, date: int) -> ReplaySession:
        scored, _ = self._prepared()
        day = scored.filter(pl.col("date") == date)
        return ReplaySession(date=date, observations=day)

    def available_dates(self) -> list[int]:
        return self.provider.available_dates()
