"""SARGVISION Traffic Intelligence — API.

Serves the live city state, the intelligence feed, the historical context
behind any finding, and the copilot. A background task drives the intelligence
loop; every endpoint reads what that loop has produced.

The mode — live or replay — is returned on every response that could be
mistaken for current conditions. That is not decoration: this system is
designed to run on replayed 2019 data during demonstration, and a client that
cannot tell the difference would be dangerous.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from packages.copilot.agent import Copilot
from packages.copilot.tools.analytics import Toolbox
from packages.providers.live import GoogleRoutesProvider, ReplayProvider
from packages.realtime.engine import IntelligenceLoop, load_baselines
from packages.registry.movements import load_registry

CURATED = Path("data/curated")
REPLAY_DATE = int(os.environ.get("REPLAY_DATE", "20190722"))
# How much replayed time passes per real second. 60 means a replayed day takes
# 24 minutes, which is long enough to watch a condition build and clear.
REPLAY_SPEED = float(os.environ.get("REPLAY_SPEED", "60"))
TICK_SECONDS = float(os.environ.get("TICK_SECONDS", "5"))
LIVE = os.environ.get("PROVIDER", "replay").lower() == "google"

STATE: dict = {"loop": None, "copilot": None, "clock": None, "subscribers": set()}


def _build_loop() -> IntelligenceLoop:
    registry = load_registry()
    baselines = load_baselines(pl.read_parquet(CURATED / "baselines.parquet"))
    if LIVE:
        provider = GoogleRoutesProvider()
    else:
        provider = ReplayProvider(
            pl.read_parquet(CURATED / "observations.parquet"),
            replay_date=REPLAY_DATE,
            speed=REPLAY_SPEED,
        )
    return IntelligenceLoop(registry=registry, provider=provider, baselines=baselines)


async def _drive() -> None:
    """Advance the loop on a wall-clock cadence.

    In replay the simulated clock runs faster than real time, so a demonstration
    covers a whole day. In live mode the two are the same and the cadence is the
    registry's sampling interval.
    """
    loop: IntelligenceLoop = STATE["loop"]
    sim = STATE["clock"]
    step = timedelta(seconds=TICK_SECONDS * (REPLAY_SPEED if not LIVE else 1))
    day_end = sim.replace(hour=23, minute=55)

    while True:
        try:
            result = await asyncio.to_thread(loop.tick, sim)
            payload = json.dumps({"type": "tick", **result})
            for q in list(STATE["subscribers"]):
                q.put_nowait(payload)
        except Exception as exc:  # noqa: BLE001 — a bad tick must not kill the loop
            for q in list(STATE["subscribers"]):
                q.put_nowait(json.dumps({"type": "error", "detail": str(exc)[:200]}))

        sim = sim + step
        if not LIVE and sim >= day_end:
            # Wrap to the start of the replay day so a demonstration can be left
            # running. The wrap is announced rather than silent.
            sim = sim.replace(hour=5, minute=0)
            for q in list(STATE["subscribers"]):
                q.put_nowait(json.dumps({"type": "replay_wrapped", "at": sim.isoformat()}))
        STATE["clock"] = sim
        await asyncio.sleep(TICK_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["loop"] = _build_loop()
    STATE["copilot"] = Copilot(Toolbox(loop=STATE["loop"]))
    start = datetime.strptime(str(REPLAY_DATE), "%Y%m%d").replace(hour=5)
    STATE["clock"] = datetime.now() if LIVE else start
    task = asyncio.create_task(_drive())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="SARGVISION Traffic Intelligence",
    description="Real-time urban mobility intelligence for Siliguri.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _loop() -> IntelligenceLoop:
    loop = STATE["loop"]
    if loop is None:
        raise HTTPException(503, "intelligence loop is not running")
    return loop


@app.get("/health")
def health() -> dict:
    loop = STATE["loop"]
    return {
        "ok": loop is not None,
        "ticks": loop.ticks if loop else 0,
        "mode": loop.city.mode if loop else None,
        "is_live": loop.city.is_live if loop else None,
    }


@app.get("/api/state")
def state() -> dict:
    loop = _loop()
    snap = loop.snapshot()
    snap["clock"] = STATE["clock"].isoformat(timespec="seconds") if STATE["clock"] else None
    return snap


@app.get("/api/feed")
def feed(include_resolved: bool = Query(False)) -> dict:
    loop = _loop()
    return {
        "mode": loop.city.mode,
        "is_live": loop.city.is_live,
        "headline": loop.city.headline(),
        "findings": loop.feed_entries(include_resolved=include_resolved),
    }


@app.get("/api/movements/{movement_id}/history")
def history(movement_id: str) -> dict:
    loop = _loop()
    readings = loop.history(movement_id)
    if not readings:
        raise HTTPException(404, f"no readings for {movement_id}")
    state = loop.city.movements[movement_id]
    return {
        "movement_id": movement_id,
        "name": state.name,
        "status": state.status.value,
        "mode": loop.city.mode,
        "is_live": loop.city.is_live,
        "readings": readings,
    }


@app.get("/api/context/{movement_id}")
def context(movement_id: str, day_type: str = Query("WEEKDAY")) -> dict:
    """The historical baseline behind a live movement — the comparison layer."""
    baselines = pl.read_parquet(CURATED / "baselines.parquet").filter(
        (pl.col("movement_id") == movement_id) & (pl.col("day_type") == day_type)
    )
    reliability = pl.read_parquet(CURATED / "reliability.parquet").filter(
        pl.col("movement_id") == movement_id
    )
    if baselines.height == 0:
        raise HTTPException(404, f"no published baseline for {movement_id} on {day_type}")
    return {
        "movement_id": movement_id,
        "day_type": day_type,
        "hours": baselines.sort("hour").to_dicts(),
        "reliability": reliability.to_dicts()[0] if reliability.height else None,
        "note": "2019 historical baseline; the comparison layer, not current conditions",
    }


@app.get("/api/registry")
def registry() -> dict:
    reg = load_registry()
    loop = STATE["loop"]
    prov = loop.provider.provenance() if loop else {}
    return {
        "movements": [m.as_dict() for m in reg.movements],
        "active": len(reg.active),
        "calls_per_hour": reg.calls_per_hour(),
        "provenance": prov,
    }


@app.get("/api/insights")
def insights() -> dict:
    """Findings from the historical discovery engine — the slow, structural layer."""
    path = CURATED / "insights.json"
    if not path.exists():
        raise HTTPException(404, "run scripts/discover.py to produce the insight store")
    return json.loads(path.read_text())


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=500)


@app.post("/api/copilot")
async def copilot(q: Question) -> dict:
    agent: Copilot = STATE["copilot"]
    if agent is None:
        raise HTTPException(503, "copilot is not initialised")
    answer = await asyncio.to_thread(agent.ask, q.question)
    loop = _loop()
    return {**answer.as_dict(), "mode": loop.city.mode, "is_live": loop.city.is_live}


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    """Server-sent events: one message per tick, so the client never polls."""
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=64)
    STATE["subscribers"].add(queue)

    async def events():
        try:
            loop = _loop()
            yield f"data: {json.dumps({'type': 'hello', 'mode': loop.city.mode, 'is_live': loop.city.is_live})}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"data: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            STATE["subscribers"].discard(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
