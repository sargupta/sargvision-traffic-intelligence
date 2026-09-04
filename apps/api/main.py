"""SARGVISION Traffic Command — API.

Serves the duty officer's board, the incident workflow, corridor detail and the
shift handover. A background task polls the corridor network and raises
incidents; every endpoint reads what that loop produced.

The polling cadence is the API bill and the compliance surface, so it lives in
one constant and the registry that drives it is one file.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Body, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from packages.command.advice import recommend
from packages.command.centre import CommandCentre
from packages.incidents.model import IncidentState
from packages.incidents.store import build_store
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

# ── who may record an action ───────────────────────────────────────────────
# Reads are open: the board's figures are aggregates, and /api/roster already
# withholds officer names and duty state. Writes are not, because every one of
# them is a police record. Before this gate, GET /api/incidents published real
# incident ids and POST /api/incidents/{id}/{action} reached application logic
# unauthenticated, so anyone who found the URL could stand down or close a live
# incident — and the Firestore store made it stick.
#
# Fail closed. With no WRITE_TOKEN configured the endpoint refuses rather than
# falling back to accepting anonymous writes; refusing to record is a safe
# failure, accepting an anonymous record is not. AUTH_MODE=open exists for
# local development and is never set in the deployed service.
WRITE_TOKEN = os.environ.get("WRITE_TOKEN", "").strip()
AUTH_MODE = os.environ.get("AUTH_MODE", "token").strip().lower()


def _load_officer_tokens() -> dict[str, str]:
    """token -> officer_id, from OFFICER_TOKENS as a JSON object.

    One token per officer is what makes the audit trail mean anything. With a
    single room token the server has to believe whatever `by` the console sends,
    so the record names a seat rather than a person and cannot be relied on
    afterwards. With these, the actor is derived from the credential and the
    client cannot assert an identity it does not hold.
    """
    raw = os.environ.get("OFFICER_TOKENS", "").strip()
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except ValueError as exc:
        raise RuntimeError(f"OFFICER_TOKENS is not valid JSON: {exc}") from exc
    if not isinstance(loaded, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and k and v for k, v in loaded.items()
    ):
        raise RuntimeError("OFFICER_TOKENS must be a JSON object of token -> officer id")
    return loaded


OFFICER_TOKENS = _load_officer_tokens()


def writes_are_gated() -> bool:
    return AUTH_MODE != "open"


def attribution() -> str:
    """How far the record can be trusted to name a person."""
    if not writes_are_gated():
        return "none"
    if OFFICER_TOKENS:
        return "per-officer"
    return "shared" if WRITE_TOKEN else "disabled"


def require_write_access(authorization: str | None) -> str | None:
    """Raise unless this caller may record an action.

    Returns the officer id the credential belongs to when it identifies one, so
    the handler can attribute the action to a person rather than to whatever the
    request body claimed.
    """
    if not writes_are_gated():
        return None
    if not OFFICER_TOKENS and not WRITE_TOKEN:
        raise HTTPException(
            503,
            "recording is disabled: this deployment has no officer tokens configured",
        )
    supplied = ""
    if authorization and authorization.lower().startswith("bearer "):
        supplied = authorization[7:].strip()
    if supplied:
        # Constant time, and over every token, so neither a wrong value nor the
        # number of officers configured can be narrowed by timing the reply.
        matched = None
        for token, officer_id in OFFICER_TOKENS.items():
            if secrets.compare_digest(supplied, token):
                matched = officer_id
        if matched is not None:
            return matched
        # The shared token is refused outright once per-officer tokens exist.
        # Accepting both would leave a credential that authorises a write while
        # producing no attribution — a bypass of the very guarantee /health
        # would then be advertising as "per-officer".
        if not OFFICER_TOKENS and WRITE_TOKEN and secrets.compare_digest(supplied, WRITE_TOKEN):
            return None  # authorised, but the record cannot name a person
    raise HTTPException(401, "an officer token is required to record an action")


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
        except Exception as exc:
            message = json.dumps({"type": "error", "detail": str(exc)[:200]})
        for q in list(STATE["subscribers"]):
            # A subscriber that cannot keep up is skipped, not disconnected:
            # the next cycle will reach them, and dropping a slow client would
            # black out a control room screen on one bad frame.
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(message)
        await asyncio.sleep(POLL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build the live centre, unless one has already been supplied.

    The guard is a test seam with a real cost behind it. Startup used to
    overwrite STATE["centre"] unconditionally, so a suite that injected a stub
    probe had it replaced by a RoutesProbe the moment TestClient entered, and
    then _drive() polled Google on every CI run. The Routes API is metered and
    is roughly 88% of this system's running cost; a test suite must not be able
    to spend it. In production STATE starts empty, so the key check and the
    poll loop below still run exactly as before.
    """
    task = None
    if STATE["centre"] is None:
        key = os.environ.get("ROUTES_API_KEY") or os.environ.get("GEO_API_KEY", "")
        if not key:
            raise RuntimeError("ROUTES_API_KEY is required — the board has no data without it")
        STATE["centre"] = CommandCentre(
            network=load_network(), probe=RoutesProbe(key), store=build_store()
        )
        STATE["started_at"] = now()
        task = asyncio.create_task(_drive())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(title="SARGVISION Traffic Command", version="2.0.0", lifespan=lifespan)
# Fail closed. A missing CORS_ORIGINS used to default to "*", so a
# misconfigured deployment silently served the command API to any origin on the
# internet. An empty allowlist is a visible outage; a wildcard is an invisible
# one.
_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
# ── keeping one instance available to the room ─────────────────────────────
# The service runs at --max-instances=1, because each instance keeps its own
# corridor state and its own poll loop. That makes availability a single point:
# one careless script, or one bored stranger with the public URL, can saturate
# the only instance and leave the duty officer with a board that will not load.
# /api/board alone is ~180 KB of corridor geometry per call.
#
# In-process counters are the right tool precisely because there is one
# instance. If that ever changes this has to move to a shared store, and the
# comment on max-instances explains why it should not change.
READ_BUDGET = int(os.environ.get("RATE_READS_PER_MIN", "240"))
WRITE_BUDGET = int(os.environ.get("RATE_WRITES_PER_MIN", "30"))
FAILED_AUTH_BUDGET = int(os.environ.get("RATE_FAILED_AUTH_PER_MIN", "10"))
_WINDOW = 60.0
_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """The caller, as seen from in front of Cloud Run's load balancer.

    request.client is the balancer, so every caller would share one bucket and
    the first busy console would rate-limit the whole city. The left-most entry
    of X-Forwarded-For is the original client.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _over_budget(ip: str, bucket: str, budget: int) -> bool:
    now_s = time.monotonic()
    seen = _hits[(ip, bucket)]
    while seen and now_s - seen[0] > _WINDOW:
        seen.popleft()
    if len(seen) >= budget:
        return True
    seen.append(now_s)
    return False


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    # The event stream is one long-lived connection per console, not traffic.
    # Counting it would throttle a control room that is doing nothing wrong.
    if request.url.path == "/api/stream":
        return await call_next(request)

    ip = client_ip(request)
    write = request.method == "POST"
    budget = WRITE_BUDGET if write else READ_BUDGET
    if _over_budget(ip, "write" if write else "read", budget):
        return JSONResponse(
            {"detail": "too many requests"},
            status_code=429,
            headers={"Retry-After": "60"},
        )

    response = await call_next(request)

    # A rejected credential is cheap to retry, so it gets its own much smaller
    # budget: without it the token is guessable at the write rate all day.
    if write and response.status_code == 401 and _over_budget(ip, "auth", FAILED_AUTH_BUDGET):
        return JSONResponse(
            {"detail": "too many failed attempts"},
            status_code=429,
            headers={"Retry-After": "60"},
        )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_methods=["GET", "POST"],
    # Authorization is load-bearing, not optional. An Authorization header makes
    # the browser preflight the request, and a preflight that does not list the
    # header is refused with "Disallowed CORS headers" — so every write from the
    # control room would fail while curl kept working, which is precisely how a
    # dropped CORS_ORIGINS went unnoticed once before.
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health() -> dict:
    c = STATE["centre"]
    return {
        "ok": c is not None,
        "store": c.store.describe() if c else None,
        "cycles": c.cycles if c else 0,
        "last_poll": c.last_poll.isoformat(timespec="seconds") if c and c.last_poll else None,
        "poll_seconds": POLL_SECONDS,
        "started_at": STATE["started_at"].isoformat(timespec="seconds")
        if STATE["started_at"]
        else None,
        # Says the posture out loud so an accidentally open deployment is
        # visible from outside instead of having to be inferred by trying it.
        "writes": (
            "OPEN — anyone can record an action"
            if not writes_are_gated()
            else "gated"
            if (OFFICER_TOKENS or WRITE_TOKEN)
            else "disabled — no officer tokens configured"
        ),
        # Whether an action in the record can be traced to a person or only to
        # a console. Stated rather than implied, because "gated" alone would
        # read as a stronger guarantee than a shared token can give.
        "attribution": attribution(),
    }


@app.get("/api/board")
def board() -> dict:
    """Everything the duty officer's main screen needs, in one request.

    `poll_seconds` travels with the payload so the screen can say when a
    reading has gone stale instead of guessing a threshold. The cadence is
    adaptive and set by deployment, so a number compiled into the web build
    would be wrong the first time it changed.
    """
    return {**centre().board(), "poll_seconds": POLL_SECONDS}


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
                "name_unconfirmed": j.name_unconfirmed,
                "caveat": j.caveat,
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
    frame = pl.read_parquet(path).filter(pl.col("day_type") == day_type.upper()).sort("hour")
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
    items.sort(
        key=lambda i: (
            {"P1": 0, "P2": 1, "P3": 2, "P4": 3}[i.priority.value],
            -i.age_minutes(moment),
        )
    )
    return {"incidents": [i.as_dict(moment) for i in items], "count": len(items)}


@app.get("/api/incidents/{incident_id}")
def incident(incident_id: str) -> dict:
    c = centre()
    item = c.incidents.get(incident_id)
    if item is None:
        raise HTTPException(404, f"no incident {incident_id}")
    return item.as_dict(c.last_poll or now())


class Action(BaseModel):
    # Optional because a per-officer token already names the actor, and the
    # server prefers its own answer to the client's. Still required, and still
    # validated, when the credential cannot identify anyone.
    by: str | None = Field(default=None, min_length=2, max_length=80)
    to: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, max_length=40)
    text: str | None = Field(default=None, max_length=1000)
    kind: str | None = Field(default=None, max_length=20)


@app.post("/api/incidents/{incident_id}/{action}")
def act(
    incident_id: str,
    action: str,
    payload: Action = Body(...),
    authorization: str | None = Header(default=None),
) -> dict:
    """The officer's verbs. Every one records who did it and when."""
    identified = require_write_access(authorization)
    # The credential wins. A console cannot record an action in another
    # officer's name, because the name is not taken from the request.
    actor = identified or payload.by
    if not actor:
        raise HTTPException(422, "who is recording this? `by` is required")
    c = centre()
    item = c.incidents.get(incident_id)
    if item is None:
        raise HTTPException(404, f"no incident {incident_id}")

    try:
        match action:
            case "acknowledge":
                item.acknowledge(actor)
            case "assign":
                if not payload.to:
                    raise HTTPException(400, "assign needs `to`")
                item.assign(payload.to, by=actor, unit=payload.unit)
            case "note":
                if not payload.text:
                    raise HTTPException(400, "note needs `text`")
                item.add_note(actor, payload.text, kind=payload.kind or "NOTE")
            case "on-scene":
                item.move(IncidentState.ON_SCENE, actor)
            case "clearing":
                item.move(IncidentState.CLEARING, actor, reason=payload.text)
            case "resolve":
                item.move(IncidentState.RESOLVED, actor, reason=payload.text)
            case "stand-down":
                if not payload.text:
                    raise HTTPException(400, "standing down needs a reason in `text`")
                item.stand_down(actor, payload.text)
            case "close":
                if not payload.text:
                    raise HTTPException(400, "closing needs an outcome in `text`")
                item.close(actor, payload.text)
            case _:
                raise HTTPException(404, f"no action {action}")
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # IllegalTransition and anything else
        raise HTTPException(409, str(exc)) from exc

    # Capture the live index at this transition, so "on scene" and "resolved"
    # carry an exact reading rather than the nearest poll. Actions land between
    # polls, so without this the verification series would miss the moments that
    # matter most.
    c.sample_incident(item, now())

    # Written before the response returns. An officer who sees "assigned" must
    # not lose it to an instance recycling a second later.
    c.remember(item)
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
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            STATE["subscribers"].discard(queue)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
