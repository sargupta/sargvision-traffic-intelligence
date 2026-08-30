"""SARGVISION Traffic Command — API.

Serves the duty officer's board, the incident workflow, corridor detail and the
shift handover. A background task polls the corridor network and raises
incidents; every endpoint reads what that loop produced.

The polling cadence is the API bill and the compliance surface, so it lives in
one constant and the registry that drives it is one file.
"""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from packages.command.advice import recommend
from packages.command.centre import CommandCentre
from packages.incidents.model import IncidentState
from packages.network.model import load_network
from packages.network.probe import RoutesProbe

CURATED = Path("data/curated")
ROSTER = json.loads((CURATED / "roster.json").read_text())

# Siliguri time, always. Every timestamp here is read by an officer standing in
# West Bengal; a UTC clock in the header of a "what is happening now" screen is
# wrong by five and a half hours. Set explicitly rather than relying on the
# container's TZ so a misconfigured deployment cannot silently shift the clock.
IST = ZoneInfo("Asia/Kolkata")


def now() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)

# 34 corridors every 3 minutes is 680 requests an hour. That number is the bill
# and the compliance surface; it is deliberately one constant.
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "180"))

STATE: dict = {"centre": None, "subscribers": set(), "started_at": None}


def centre() -> CommandCentre:
    c = STATE["centre"]
    if c is None:
        raise HTTPException(503, "command centre is not running")
    return c


async def _drive() -> None:
    while True:
        try:
            result = await asyncio.to_thread(centre().poll, now())
            message = json.dumps({"type": "cycle", **result})
        except Exception as exc:  # noqa: BLE001 — a bad cycle must not kill the loop
            message = json.dumps({"type": "error", "detail": str(exc)[:200]})
        for q in list(STATE["subscribers"]):
            try:
                q.put_nowait(message)
            except asyncio.QueueFull:
                pass
        await asyncio.sleep(POLL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    key = os.environ.get("ROUTES_API_KEY") or os.environ.get("GEO_API_KEY", "")
    if not key:
        raise RuntimeError("ROUTES_API_KEY is required — the board has no data without it")
    STATE["centre"] = CommandCentre(network=load_network(), probe=RoutesProbe(key))
    STATE["started_at"] = now()
    task = asyncio.create_task(_drive())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="SARGVISION Traffic Command", version="2.0.0", lifespan=lifespan)
# Fail closed. A missing CORS_ORIGINS used to default to "*", so a
# misconfigured deployment silently served the command API to any origin on the
# internet. An empty allowlist is a visible outage; a wildcard is an invisible
# one.
_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict:
    c = STATE["centre"]
    return {
        "ok": c is not None,
        "cycles": c.cycles if c else 0,
        "last_poll": c.last_poll.isoformat(timespec="seconds") if c and c.last_poll else None,
        "poll_seconds": POLL_SECONDS,
        "started_at": STATE["started_at"].isoformat(timespec="seconds") if STATE["started_at"] else None,
    }


@app.get("/api/board")
def board() -> dict:
    """Everything the duty officer's main screen needs, in one request."""
    return centre().board()


@app.get("/api/advice")
def advice() -> dict:
    """What to do about the current state.

    Derived from the network and the readings by arithmetic. No language model
    participates, nothing here asserts a cause, and every item carries both the
    evidence it rests on and the thing it cannot establish — a suggestion an
    officer cannot audit is one they will stop reading.
    """
    c = centre()
    moment = c.last_poll or now()
    return {
        "at": moment.isoformat(timespec="seconds"),
        "recommendations": [r.as_dict() for r in recommend(c.network, c.board(moment), moment)],
    }


@app.get("/api/network")
def network() -> dict:
    net = centre().network
    return {
        "junctions": [
            {
                "junction_id": j.junction_id,
                "name": j.name,
                "lat": j.lat,
                "lon": j.lon,
                "control": j.control,
                "vc_ratio": j.vc_ratio,
                "congestion_pressure": j.congestion_pressure,
                "pin_approximate": j.pin_is_approximate,
                "pin_note": j.match_note,
            }
            for j in net.junctions.values()
        ],
        "corridors": [
            {
                "corridor_id": c.corridor_id,
                "name": c.name,
                "from_junction": c.from_junction,
                "to_junction": c.to_junction,
                "approximate": c.located_approximately,
            }
            for c in net.corridors.values()
        ],
    }


@app.get("/api/corridors/{corridor_id}")
def corridor(corridor_id: str) -> dict:
    c = centre()
    status = c.status.get(corridor_id)
    if status is None:
        raise HTTPException(404, f"no corridor {corridor_id}")
    corridor_def = c.network.corridors[corridor_id]
    return {
        "corridor_id": corridor_id,
        "name": status.name,
        "from_name": corridor_def.from_name,
        "to_name": corridor_def.to_name,
        "band": status.band,
        "index": round(status.index, 3) if status.index is not None else None,
        "trend_per_10min": round(t, 3) if (t := status.trend()) is not None else None,
        "approximate_location": corridor_def.located_approximately,
        "readings": [
            {
                "at": r.observed_at.isoformat(timespec="seconds"),
                "index": round(r.congestion_index, 3),
                "duration_minutes": round(r.duration_s / 60, 1),
                "typical_minutes": round(r.static_duration_s / 60, 1),
                "chokes": len(r.choke_points),
            }
            for r in status.readings
        ],
        "latest": status.latest.as_dict() if status.latest else None,
        "note": (
            "Index compares current travel time with Google's modelled typical time. "
            "It is not a measured free-flow speed and can read below 1.0."
        ),
    }


@app.get("/api/city-profile")
def city_profile(day_type: str = Query("WEEKDAY")) -> dict:
    """The city's shape of the day, from the 2019 study.

    This is the ONE thing the historical dataset legitimately supports. It was
    sampled as random origin-destination pairs across Siliguri, so it describes
    city-level structure well and says nothing reliable about any individual
    junction — only 11.8% of its observations fall on a named corridor even at a
    1 km catchment. It is offered as context for reading today's numbers, never
    as a baseline for a specific corridor.
    """
    import polars as pl

    path = CURATED / "patterns_hourly.parquet"
    if not path.exists():
        raise HTTPException(404, "city profile has not been built")
    frame = (
        pl.read_parquet(path)
        .filter(pl.col("day_type") == day_type.upper())
        .sort("hour")
    )
    return {
        "day_type": day_type.upper(),
        "hours": [
            {
                "hour": int(r["hour"]),
                "index": round(r["median_tti"], 3),
                "speed_kmh": round(r["median_speed_kmh"], 1),
                "sample_size": int(r["sample_size"]),
                "congested": bool(r["congested"]),
            }
            for r in frame.iter_rows(named=True)
        ],
        "source": (
            "Akbar, Couture, Duranton & Storeygard, American Economic Review 113(4), 2023. "
            "101,418 valid primary-route observations, 13 June to 5 November 2019."
        ),
        "limitation": (
            "City-wide structure, not corridor-specific. Seven years old. Useful for "
            "recognising the shape of a normal day, not for judging one junction."
        ),
    }


@app.get("/api/roster")
def roster() -> dict:
    """Units available for assignment.

    **Deployment status is deliberately withheld.** This endpoint has no
    authentication in front of it, and `on_duty` per named officer is a live,
    public map of which traffic guards are staffed and which are not — in a
    city on an international border and the only land corridor to the
    North-East. Names and duty state are operational security, not roster
    convenience.

    Until an identity provider sits in front of this API, the response carries
    only what the assignment control genuinely needs: a unit to send. Restoring
    names and duty state is gated on auth, not on a flag.
    """
    return {
        "officers": [
            {
                "officer_id": o["officer_id"],
                "name": o["unit"],
                "rank": o["rank"],
                "role": o["role"],
                "unit": o["unit"],
                "on_duty": True,
            }
            for o in ROSTER
            if o["role"] != "DUTY_OFFICER"
        ],
        "note": (
            "Officer names and duty status require authentication and are not "
            "served here. Assignment is to a unit."
        ),
    }


@app.get("/api/incidents")
def incidents(state: str | None = Query(None), include_closed: bool = Query(False)) -> dict:
    c = centre()
    moment = c.last_poll or now()
    items = list(c.incidents.values())
    if state:
        items = [i for i in items if i.state.value == state.upper()]
    elif not include_closed:
        items = [i for i in items if i.is_open]
    items.sort(key=lambda i: ({"P1": 0, "P2": 1, "P3": 2, "P4": 3}[i.priority.value], -i.age_minutes(moment)))
    return {"incidents": [i.as_dict(moment) for i in items], "count": len(items)}


@app.get("/api/incidents/{incident_id}")
def incident(incident_id: str) -> dict:
    c = centre()
    item = c.incidents.get(incident_id)
    if item is None:
        raise HTTPException(404, f"no incident {incident_id}")
    return item.as_dict(c.last_poll or now())


class Action(BaseModel):
    by: str = Field(min_length=2, max_length=80)
    to: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    text: str | None = Field(default=None, max_length=1000)
    kind: str | None = Field(default=None, max_length=20)


@app.post("/api/incidents/{incident_id}/{action}")
def act(incident_id: str, action: str, payload: Action = Body(...)) -> dict:
    """The officer's verbs. Every one records who did it and when."""
    c = centre()
    item = c.incidents.get(incident_id)
    if item is None:
        raise HTTPException(404, f"no incident {incident_id}")

    try:
        match action:
            case "acknowledge":
                item.acknowledge(payload.by)
            case "assign":
                if not payload.to:
                    raise HTTPException(400, "assign needs `to`")
                item.assign(payload.to, by=payload.by, unit=payload.unit)
            case "note":
                if not payload.text:
                    raise HTTPException(400, "note needs `text`")
                item.add_note(payload.by, payload.text, kind=payload.kind or "NOTE")
            case "on-scene":
                item.move(IncidentState.ON_SCENE, payload.by)
            case "clearing":
                item.move(IncidentState.CLEARING, payload.by, reason=payload.text)
            case "resolve":
                item.move(IncidentState.RESOLVED, payload.by, reason=payload.text)
            case "stand-down":
                if not payload.text:
                    raise HTTPException(400, "standing down needs a reason in `text`")
                item.stand_down(payload.by, payload.text)
            case "close":
                if not payload.text:
                    raise HTTPException(400, "closing needs an outcome in `text`")
                item.close(payload.by, payload.text)
            case _:
                raise HTTPException(404, f"no action {action}")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # IllegalTransition and anything else
        raise HTTPException(409, str(exc)) from exc

    return item.as_dict(c.last_poll or now())


@app.get("/api/shift/handover")
def handover(hours: float = Query(8.0, ge=1, le=24)) -> dict:
    """What the next shift inherits, and what this one did.

    Written as a record rather than a dashboard: it is meant to be read, saved
    and printed.
    """
    c = centre()
    moment = c.last_poll or now()
    since = moment - timedelta(hours=hours)
    touched = [i for i in c.incidents.values() if i.detected_at >= since or i.is_open]

    def summarise(item) -> dict:
        return {
            "incident_id": item.incident_id,
            "priority": item.priority.value,
            "state": item.state.value,
            "title": item.title,
            "location_name": item.location_name,
            "owner": item.owner,
            "age_minutes": round(item.age_minutes(moment), 1),
            "notes": [n.as_dict() for n in item.notes],
        }

    open_unowned = [i for i in touched if i.needs_attention]
    open_owned = [i for i in touched if i.is_open and not i.needs_attention]
    closed = [i for i in touched if i.state is IncidentState.CLOSED]
    stood_down = [i for i in touched if i.state is IncidentState.STOOD_DOWN]
    lapsed = [i for i in touched if i.state is IncidentState.LAPSED]

    raised = len(touched)
    return {
        "window_hours": hours,
        "from": since.isoformat(timespec="seconds"),
        "to": moment.isoformat(timespec="seconds"),
        "raised": raised,
        "handing_over": {
            "needs_an_owner": [summarise(i) for i in open_unowned],
            "in_hand": [summarise(i) for i in open_owned],
        },
        "this_shift": {
            "closed": [summarise(i) for i in closed],
            "stood_down": [summarise(i) for i in stood_down],
            "lapsed": [summarise(i) for i in lapsed],
        },
        "alerting_quality": {
            "lapse_rate": round(len(lapsed) / raised, 3) if raised else 0.0,
            "note": (
                "Lapsed means the condition cleared before anyone acted. A high rate "
                "means the system is raising things that do not need an officer, and "
                "the thresholds should be reviewed."
            ),
        },
    }


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=32)
    STATE["subscribers"].add(queue)

    async def events():
        try:
            yield f"data: {json.dumps({'type': 'hello', 'poll_seconds': POLL_SECONDS})}\n\n"
            while True:
                try:
                    yield f"data: {await asyncio.wait_for(queue.get(), timeout=25)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            STATE["subscribers"].discard(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
