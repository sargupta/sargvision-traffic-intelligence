"""FastAPI — the five product endpoints.

Built around the officer's questions, not around database tables:

    What needs attention?     -> GET /priorities
    What is the city like?    -> GET /city/insights, /city/summary
    Replay a real day         -> GET /replay/{date}
    Is the alert stream sane? -> GET /city/alert-density
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException

from packages.intelligence.service import TrafficIntelligenceService

app = FastAPI(
    title="SARGVISION Traffic Intelligence Copilot",
    description="AI-powered traffic intelligence for Siliguri. "
                "Demonstrator mode runs on historical open data, not live monitoring.",
    version="0.1.0",
)
service = TrafficIntelligenceService()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "mode": "HISTORICAL_REPLAY", "is_live": False}


@app.get("/priorities")
def priorities(limit: int = 10) -> dict:
    return {"mode": "HISTORICAL_REPLAY", "priorities": service.priorities(limit)}


@app.get("/city/summary")
def city_summary() -> dict:
    return service.city_summary()


@app.get("/city/insights")
def city_insights() -> dict:
    return {"insights": [m.as_dict() for m in service.city_insights()]}


@app.get("/city/alert-density")
def alert_density() -> dict:
    return {"target_per_day": [3, 8], "readings": service.alert_density()}


@app.get("/replay/dates")
def replay_dates() -> dict:
    return {"dates": service.available_dates()}


@app.get("/replay/{date}")
def replay(date: int) -> dict:
    session = service.replay(date)
    if session.observations.height == 0:
        raise HTTPException(404, f"No observations for {date}")
    ticks = list(session.run())
    return {
        "date": date,
        "mode": session.mode,
        "is_live": session.is_live,
        "ticks": ticks,
        "events": session.events,
        "warning": "Historical replay. The analytics engine is production architecture; "
                   "the data source in this mode is 2019 history.",
    }
