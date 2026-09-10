"""The AI review board — a multi-agent expert council on Google ADK (Vertex).

The deterministic board (packages.copilot.board) already issues the immediate,
canon-grounded move for every junction that warrants one. This layer makes it
SMARTER in the way a standing council of experts is smarter than a checklist:
it reads the whole board at once, and it can see across items — that the Jalpai
More structural finding and a Sevoke choke are on the same freight axis, that a
diversion would import one junction's problem into another, which of six moves
is the one to make this shift. That cross-item judgement is what a language
model adds; it is not something arithmetic can do.

Three disciplines hold seats — Operations, Road-safety, Network — composed by a
Duty-Officer reviewer, all on Google ADK with Gemini on Vertex (the GCP startup
credits). The guardrails are load-bearing and match the copilot's:

  * GROUNDED, NOT FREE. The agents reason only over the deterministic brief and
    the canon. They never invent a number, a citation or a cause; every figure
    an officer sees still traces to the arithmetic engine. The model re-orders,
    connects and explains — it does not measure.
  * THE ARITHMETIC IS THE SPINE. If ADK is disabled, unreachable, over budget or
    slow, the endpoint returns the deterministic board. The officer never gets a
    spinner or a blank; worse, but never wrong and never invented.
  * BUDGETED. Startup credits are finite and the console polls around the clock.
    The council runs on demand (an officer opening the board), caches its read
    per live situation, and stops at a hard daily budget.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime

from packages.copilot.board import DOCTRINE, live_board

MODEL = os.environ.get("COUNCIL_MODEL", os.environ.get("COPILOT_MODEL", "gemini-2.5-flash"))
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "sargvision-traffic-intel")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-south1")

# ADK is opt-in. Default OFF so CI, local runs and a fresh deploy always take the
# deterministic path; the credit-spending council is switched on by environment
# once the deploy is confirmed healthy.
ADK_ENABLED = os.environ.get("COUNCIL_ENABLE_ADK") == "1"
CACHE_TTL_S = int(os.environ.get("COUNCIL_CACHE_TTL_S", "180"))
DAILY_BUDGET = int(os.environ.get("COUNCIL_DAILY_BUDGET", "500"))

# Per-process cache (situation hash -> (expires_at, review)) and daily budget.
# In-process is the right scope: the council read is cheap to recompute per
# instance and must never be a shared write path.
_CACHE: dict[str, tuple[float, dict]] = {}
_SPENT: dict[str, int] = {}


# ── the council's seats, as instructions ──────────────────────────────────────
_CONTRACT = (
    "You reason ONLY over the situation brief you are given. Never invent a number, "
    "a road, a citation or a cause — if it is not in the brief, you do not know it. "
    "Every move in the brief is a hypothesis to TEST against a matched control, never "
    "an asserted fix. Carry its 'do_not_claim'. Signal retiming is routed to Google "
    "Green Light, never built here. Never propose a congestion remedy at a safety-only "
    "junction. Our speed comes from a car probe that under-samples the two- and "
    "three-wheelers that dominate Siliguri, so treat a probe slowdown as a prompt to "
    "confirm, not proof. Be terse and operational; a duty officer is reading."
)

_OPERATIONS = (
    "You hold the Operations & congestion seat on the Siliguri traffic review board — "
    "signalised-junction operations, incident management and side friction (HCM/TRB, "
    "IRC:93, the incident-delay result that clearance time is the lever). For the "
    "congestion items in the brief, give the one operational point that most sharpens "
    "the duty officer's move — sequencing, what to pre-position, what confounds the "
    "measurement. " + _CONTRACT
)
_SAFETY = (
    "You hold the Road-safety seat on the Siliguri traffic review board (Roy et al. "
    "2026 emerging-hotspot analysis; Sherman 1990 on deterrence decay; road-safety-audit "
    "doctrine). Danger and delay are different problems in different places and hours. "
    "For any safety item, say what to watch and why the congestion index cannot score it. "
    + _CONTRACT
)
_NETWORK = (
    "You hold the Network & induced-demand seat on the Siliguri traffic review board "
    "(Duranton & Turner 2011; Braess's paradox; cordon before/after). You see the board "
    "as a network: whether two items share an axis, whether a diversion merely moves a jam "
    "into another item, what must be cordon-measured. " + _CONTRACT
)
_REVIEWER = (
    "You are the Duty-Officer reviewer chairing the Siliguri traffic review board. You are "
    "given the live situation brief — the immediate, canon-grounded moves the board has "
    "issued across the network right now. Consult the specialist seats (operations, safety, "
    "network) as the items warrant, then deliver the board's read.\n\n"
    "Output ONLY a JSON object, no prose around it:\n"
    '{"synthesis": "<=3 sentences: what the duty officer should prioritise THIS shift and '
    'how the items relate — the cross-item judgement a checklist cannot give>", '
    '"notes": [{"junction": "<exact junction name from the brief>", "expert_note": "<=2 '
    'sentences from the relevant seat that sharpen THIS item\'s move>"}]}\n\n'
    "Only include a note where a seat genuinely adds something; do not pad. " + _CONTRACT
)


def _situation_key(base: dict) -> str:
    """A hash of the live SITUATION, not the wall clock — so the council is reused
    while the picture is unchanged, and recomputed the moment it shifts."""
    sig = [
        (
            i["junction"],
            i["urgency"],
            i["move"],
            i["live"].get("condition"),
            i["live"].get("band"),
            bool(i["live"].get("has_choke_point")),
        )
        for i in base.get("items", [])
    ]
    raw = json.dumps(sig, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _brief_for_agents(base: dict) -> str:
    """The grounded brief the agents reason over — the deterministic items only,
    trimmed to what the model needs to judge them. No wall-clock, no internals."""
    items = [
        {
            "junction": i["junction"],
            "urgency": i["urgency"],
            "seat": i["seat"],
            "grade": i["grade"],
            "move": i["move"],
            "where_when": i["where_when"],
            "live": i["live"],
            "rationale": i["rationale"],
            "measure": i["measure"],
            "do_not_claim": i["do_not_claim"],
        }
        for i in base.get("items", [])
    ]
    return json.dumps(
        {"doctrine": DOCTRINE, "probe_caveat": base.get("probe_caveat"), "items": items},
        ensure_ascii=False,
        indent=2,
    )


def _parse_json(text: str) -> dict | None:
    """Tolerant extraction of the reviewer's JSON object from its text."""
    if not text:
        return None
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


async def _run_council(brief: str) -> str:
    """Run the ADK reviewer (with the specialist seats as agent-tools) once, on
    Vertex, and return its final text. Imported lazily so nothing here loads
    unless the council is actually switched on."""
    from google.adk.agents import LlmAgent
    from google.adk.runners import InMemoryRunner
    from google.adk.tools.agent_tool import AgentTool
    from google.genai import types

    # ADK reads Vertex config from the environment.
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", PROJECT)
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", LOCATION)

    operations = LlmAgent(model=MODEL, name="operations_seat", instruction=_OPERATIONS)
    safety = LlmAgent(model=MODEL, name="safety_seat", instruction=_SAFETY)
    network = LlmAgent(model=MODEL, name="network_seat", instruction=_NETWORK)
    reviewer = LlmAgent(
        model=MODEL,
        name="duty_officer_reviewer",
        instruction=_REVIEWER,
        tools=[AgentTool(agent=operations), AgentTool(agent=safety), AgentTool(agent=network)],
    )

    runner = InMemoryRunner(agent=reviewer, app_name="traffic_council")
    session = await runner.session_service.create_session(
        app_name="traffic_council", user_id="duty_officer"
    )
    message = types.Content(role="user", parts=[types.Part.from_text(text=brief)])
    final = ""
    async for event in runner.run_async(
        user_id="duty_officer", session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final = "".join(p.text or "" for p in event.content.parts)
    return final


def _budget_left() -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    return _SPENT.get(today, 0) < DAILY_BUDGET


def _spend() -> None:
    today = datetime.now().strftime("%Y-%m-%d")
    _SPENT[today] = _SPENT.get(today, 0) + 1


def review(centre, now: datetime | None = None, force: bool = False) -> dict:
    """The board's live read. Deterministic brief always; the AI council layered
    on when it is enabled, in budget, and the situation is not already cached.
    Any failure degrades to the deterministic board — never raises."""
    base = live_board(centre, now)

    # Nothing to enrich, or the council is off: the deterministic board stands.
    if not ADK_ENABLED or not base.get("items"):
        return base

    key = _situation_key(base)
    if not force:
        hit = _CACHE.get(key)
        if hit and hit[0] > time.time():
            return hit[1]

    if not _budget_left():
        base["council_status"] = "deterministic — daily AI-council budget reached"
        return base

    try:
        import asyncio

        _spend()
        text = asyncio.run(_run_council(_brief_for_agents(base)))
        parsed = _parse_json(text)
        if not parsed:
            base["council_status"] = "deterministic — council returned no usable synthesis"
            return base

        notes = {n.get("junction"): n.get("expert_note") for n in parsed.get("notes", []) if n}
        for item in base["items"]:
            note = notes.get(item["junction"])
            if note:
                item["expert_note"] = note
        enriched = {
            **base,
            "synthesis": parsed.get("synthesis") or None,
            "generated_by": "adk-council",
            "model": MODEL,
            "seats": ["Operations & congestion", "Road-safety", "Network & induced demand"],
            "council_status": "AI council (Google ADK, Gemini on Vertex)",
        }
        _CACHE[key] = (time.time() + CACHE_TTL_S, enriched)
        return enriched
    except Exception as exc:  # ADK/Vertex/quota/parse — degrade, never fail
        base["council_status"] = f"deterministic — AI council unavailable ({str(exc)[:160]})"
        return base
