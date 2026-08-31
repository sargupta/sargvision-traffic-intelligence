"""The tools the copilot is allowed to use.

Every one of these is a query against tables the deterministic engines
produced. The model may choose which to call and how to phrase what comes back.
It may not compute a traffic figure, and it has no path to the raw
observations — if a number is not returned by a tool on this page, the model
has no way to obtain it and must say so.

    Analytics discovers.  AI explains.  Humans decide.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import duckdb

DB = Path("data/curated/siliguri.duckdb")


@dataclass
class Toolbox:
    """Read-only access to the curated tables, plus the live loop if one is running."""

    db_path: Path = DB
    loop: Any = None

    def movement_ids(self) -> dict[str, str]:
        """Name to id, so a view directive that names a movement can address it."""
        return {
            r["movement_name"]: r["movement_id"]
            for r in self._q("SELECT movement_id, movement_name FROM movements")
        }

    def _q(self, sql: str, params: list | None = None) -> list[dict]:
        con = duckdb.connect(str(self.db_path), read_only=True)
        try:
            cur = con.execute(sql, params or [])
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]
        finally:
            con.close()

    # ── historical tools ─────────────────────────────────────────────────────
    def get_movement_summary(self, movement: str | None = None, limit: int = 10) -> dict:
        """Median travel time, delay and speed for a movement, or the busiest few."""
        if movement:
            rows = self._q(
                "SELECT movement_id, movement_name, sample_size, expected_minutes, median_delay_pct, "
                "median_speed_kmh, median_distance_m, confidence FROM movements "
                "WHERE lower(movement_name) LIKE lower(?) ORDER BY sample_size DESC LIMIT ?",
                [f"%{movement}%", limit],
            )
        else:
            rows = self._q(
                "SELECT movement_id, movement_name, sample_size, expected_minutes, median_delay_pct, "
                "median_speed_kmh, confidence FROM movements ORDER BY sample_size DESC LIMIT ?",
                [limit],
            )
        return {"tool": "get_movement_summary", "rows": rows, "unit": "minutes, %, km/h"}

    def get_reliability(self, order: str = "worst", limit: int = 8) -> dict:
        """Which movements can be planned around and which cannot."""
        direction = "DESC" if order == "worst" else "ASC"
        rows = self._q(
            f"SELECT movement_id, movement_name, buffer_pct, reliability, median_minutes, p90_minutes, "
            f"extra_minutes, sample_size, confidence FROM reliability "
            f"ORDER BY buffer_pct {direction} LIMIT ?",
            [limit],
        )
        return {
            "tool": "get_reliability",
            "rows": rows,
            "definition": (
                "buffer_pct is the extra time over a typical journey needed to arrive on "
                "time nine trips in ten, computed on seconds per kilometre"
            ),
        }

    def get_time_pattern(self, movement: str | None = None, day_type: str = "WEEKDAY") -> dict:
        """How a movement, or the city, behaves hour by hour."""
        if movement:
            rows = self._q(
                "SELECT hour, expected_minutes, normal_low_minutes, normal_high_minutes, "
                "median_tti, sample_size, confidence FROM baselines "
                "WHERE lower(movement_name) LIKE lower(?) AND day_type = ? ORDER BY hour",
                [f"%{movement}%", day_type],
            )
        else:
            rows = self._q(
                "SELECT hour, median_tti, median_speed_kmh, median_delay_pct, sample_size, "
                "congested FROM patterns_hourly WHERE day_type = ? ORDER BY hour",
                [day_type],
            )
        return {"tool": "get_time_pattern", "day_type": day_type, "rows": rows}

    def get_anomalies(self, movement: str | None = None, limit: int = 10) -> dict:
        """Historical departures from a movement's own baseline."""
        if movement:
            rows = self._q(
                "SELECT movement_id, movement_name, observed_at, hour, expected_minutes, observed_minutes, "
                "deviation_pct, severity, baseline_confidence FROM anomalies "
                "WHERE lower(movement_name) LIKE lower(?) ORDER BY deviation_pct DESC LIMIT ?",
                [f"%{movement}%", limit],
            )
        else:
            rows = self._q(
                "SELECT movement_id, movement_name, observed_at, hour, expected_minutes, observed_minutes, "
                "deviation_pct, severity FROM anomalies ORDER BY deviation_pct DESC LIMIT ?",
                [limit],
            )
        return {
            "tool": "get_anomalies",
            "rows": rows,
            "note": "historical departures from the 2019 baseline; not live events",
        }

    def get_data_confidence(self, movement: str | None = None) -> dict:
        """How much evidence sits behind an answer, and where there is none."""
        if movement:
            rows = self._q(
                "SELECT movement_id, movement_name, sample_size, confidence FROM movements "
                "WHERE lower(movement_name) LIKE lower(?)",
                [f"%{movement}%"],
            )
        else:
            rows = self._q(
                "SELECT confidence, count(*) AS movements, sum(sample_size) AS observations "
                "FROM movements GROUP BY confidence ORDER BY observations DESC"
            )
        bins = self._q("SELECT count(*) AS published_bins FROM baselines")
        return {
            "tool": "get_data_confidence",
            "rows": rows,
            "published_baseline_bins": bins[0]["published_bins"] if bins else 0,
            "floor": "30 observations per movement-hour-daytype bin; below that nothing is published",
        }

    # ── live tools ───────────────────────────────────────────────────────────
    def get_current_state(self, status: str | None = None) -> dict:
        """What the city is doing right now, according to the running loop."""
        if self.loop is None:
            return {
                "tool": "get_current_state",
                "available": False,
                "reason": "no live loop is running in this process",
            }
        snap = self.loop.snapshot()
        movements = snap["movements"]
        if status:
            movements = [m for m in movements if m["status"] == status.upper()]
        return {
            "tool": "get_current_state",
            "available": True,
            "mode": snap["mode"],
            "is_live": snap["is_live"],
            "updated_at": snap["updated_at"],
            "headline": snap["headline"],
            "counts": snap["counts"],
            "movements": movements,
        }

    def get_recent_changes(self, limit: int = 8) -> dict:
        """What the intelligence engine has raised, most important first."""
        if self.loop is None:
            return {
                "tool": "get_recent_changes",
                "available": False,
                "reason": "no live loop is running in this process",
            }
        return {
            "tool": "get_recent_changes",
            "available": True,
            "findings": self.loop.feed_entries()[:limit],
        }

    def get_movement_history(self, movement_id: str) -> dict:
        """The recent trace of one movement, for showing a trend."""
        if self.loop is None:
            return {"tool": "get_movement_history", "available": False}
        return {
            "tool": "get_movement_history",
            "available": True,
            "movement_id": movement_id,
            "readings": self.loop.history(movement_id)[-48:],
        }


SCHEMAS: list[dict] = [
    {
        "name": "get_current_state",
        "description": "Current status of every monitored movement: deviation from expected travel time, status band, how long it has held. Use for anything about now.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["NORMAL", "MODERATE", "HIGH", "CRITICAL"]}
            },
        },
    },
    {
        "name": "get_recent_changes",
        "description": "Findings the intelligence engine has raised, ranked by priority. Use for 'what changed', 'what is wrong', 'what should I look at'.",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
    },
    {
        "name": "get_movement_history",
        "description": "Recent readings for one movement, to show how it got to its current state.",
        "parameters": {
            "type": "object",
            "properties": {"movement_id": {"type": "string"}},
            "required": ["movement_id"],
        },
    },
    {
        "name": "get_movement_summary",
        "description": "Historical median travel time, delay and speed for a movement, or the busiest movements.",
        "parameters": {
            "type": "object",
            "properties": {"movement": {"type": "string"}, "limit": {"type": "integer"}},
        },
    },
    {
        "name": "get_reliability",
        "description": "Which movements are dependable and which are not, by buffer time. Use for 'unreliable', 'unpredictable', 'variable'.",
        "parameters": {
            "type": "object",
            "properties": {
                "order": {"type": "string", "enum": ["worst", "best"]},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_time_pattern",
        "description": "Hour-by-hour behaviour of a movement or the whole city, weekday or weekend.",
        "parameters": {
            "type": "object",
            "properties": {
                "movement": {"type": "string"},
                "day_type": {"type": "string", "enum": ["WEEKDAY", "WEEKEND", "ALL"]},
            },
        },
    },
    {
        "name": "get_anomalies",
        "description": "Historical departures from baseline in the 2019 data. NOT live events.",
        "parameters": {
            "type": "object",
            "properties": {"movement": {"type": "string"}, "limit": {"type": "integer"}},
        },
    },
    {
        "name": "get_data_confidence",
        "description": "How much evidence supports an answer, and where there is not enough to say anything.",
        "parameters": {"type": "object", "properties": {"movement": {"type": "string"}}},
    },
]
