"""The Mobility Copilot, re-grounded on the live command board.

    question → the model chooses tools → deterministic tools read the LIVE centre
    → the model explains, in a structure that cannot omit its own limitation

The model does two jobs and no others: pick which tools answer the question, and
turn what the tools returned into English. It never computes a traffic figure —
every number in an answer came out of a tool call against the running centre, and
the tool trace is returned so it can be checked rather than trusted.

This is the sibling of the command bar: the bar *executes* an officer's verbs;
the copilot *answers* their questions. Both refuse to invent — the bar through a
legality gate, the copilot through the AnswerContract, which will not construct
without a limitation.
"""

from __future__ import annotations

import json
import os
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from packages.command.centre import CommandCentre
from packages.contracts.response import AnswerContract

MODEL = os.environ.get("COPILOT_MODEL", "gemini-2.5-flash")
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "sargvision-traffic-intel")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MAX_STEPS = 5

# The accident record, held here rather than measured — the same evidence the
# network reference shows. The copilot must be able to answer "which junctions
# are dangerous", and that is a study finding, not something the live system
# observes.
SAFETY: dict[str, str] = {
    "J_VENUS_MORE": "Highest accident density in the city (14.21/km2), intensifying — and one of the LEAST congested (V/C 0.39). Danger, not delay.",
    "J_DARJEELING_MORE": "Evening accident leader, 16.13% of the evening period's incidents.",
    "J_CHAMPASARI_MORE": "Secondary accident hotspot.",
}


class LiveToolbox:
    """Read-only views over the running centre. Deterministic; every figure here
    is one the centre already computed. No tool writes anything."""

    def __init__(self, centre: CommandCentre, now_fn=None):
        self.centre = centre
        self._now = now_fn or datetime.now

    def _moment(self) -> datetime:
        return self.centre.last_poll or self._now()

    def get_current_state(self) -> dict:
        c = self.centre
        moment = self._moment()
        board = c.board(moment)
        open_all = [i for i in c.incidents.values() if i.is_open]
        overdue = [i for i in open_all if i.escalation(moment)["overdue"]]
        return {
            "at": board["at"],
            "headline": board["headline"],
            "bands": board["bands"],
            "open_incidents": len(open_all),
            "unowned": board["unowned"],
            "overdue": len(overdue),
            "corridors_above_typical": sum(
                1 for s in c.status.values() if s.band in ("SEVERE", "HIGH", "ELEVATED")
            ),
            "poll_age_minutes": round((self._now() - moment).total_seconds() / 60, 1),
        }

    def list_incidents(self, only_open: bool = True) -> dict:
        c = self.centre
        moment = self._moment()
        rows = []
        for i in sorted(
            c.incidents.values(),
            key=lambda x: (
                {"P1": 0, "P2": 1, "P3": 2, "P4": 3}[x.priority.value],
                -x.age_minutes(moment),
            ),
        ):
            if only_open and not i.is_open:
                continue
            esc = i.escalation(moment)
            rows.append(
                {
                    "incident_id": i.incident_id,
                    "title": i.title,
                    "location": i.location_name,
                    "priority": i.priority.value,
                    "state": i.state.value,
                    "owner": i.owner,
                    "kind": i.kind.value,
                    "age_minutes": round(i.age_minutes(moment), 1),
                    "overdue": esc["overdue"],
                    "minutes_over": esc["minutes_over"],
                }
            )
        return {"count": len(rows), "incidents": rows}

    def get_incident(self, incident_id: str) -> dict:
        i = self.centre.incidents.get(incident_id)
        if i is None:
            return {"error": f"no incident {incident_id}"}
        d = i.as_dict(self._moment())
        # Trim the heavy geometry the model does not need.
        d.pop("samples", None)
        return d

    def corridors_above_typical(self, limit: int = 8) -> dict:
        c = self.centre
        moment = self._moment()
        elevated = sorted(
            (s for s in c.status.values() if s.band in ("SEVERE", "HIGH", "ELEVATED")),
            key=lambda s: -(s.index or 0),
        )
        rows = [
            {
                "name": s.name,
                "band": s.band,
                "index": round(s.index, 3) if s.index is not None else None,
                "excess_minutes": round(s.latest.excess_minutes, 1) if s.latest else None,
                "roads": s.latest.roads if s.latest else "",
                "held_minutes": round(s.held_for(moment).total_seconds() / 60, 1),
                "choke_points": len(s.latest.choke_points) if s.latest else 0,
            }
            for s in elevated[:limit]
        ]
        return {"count": len(elevated), "shown": rows}

    def junction_reference(self, name: str | None = None) -> dict:
        rows = []
        for j in self.centre.network.junctions.values():
            if name and name.lower() not in j.name.lower():
                continue
            rows.append(
                {
                    "junction": j.name,
                    "control": j.control,
                    "vc_ratio_2011": j.vc_ratio,
                    "congestion_pressure": j.congestion_pressure,
                    "safety": SAFETY.get(j.junction_id),
                }
            )
        return {"count": len(rows), "junctions": rows}

    def recent_changes(self, minutes: int = 60) -> dict:
        cutoff = self._moment() - timedelta(minutes=minutes)
        rows = []
        for i in self.centre.incidents.values():
            for h in i.history:
                if h.at >= cutoff:
                    rows.append(
                        {
                            "incident_id": i.incident_id,
                            "location": i.location_name,
                            "from": h.frm.value,
                            "to": h.to.value,
                            "by": h.by,
                            "at": h.at.isoformat(timespec="seconds"),
                        }
                    )
        rows.sort(key=lambda r: r["at"], reverse=True)
        return {"window_minutes": minutes, "count": len(rows), "changes": rows[:20]}

    def verification_summary(self, hours: int = 24) -> dict:
        """Did our deployments move the road? The "we verify" question, over the
        incidents resolved in the window."""
        cutoff = self._moment() - timedelta(hours=hours)
        resolved = [
            i for i in self.centre.incidents.values() if i.resolved_at and i.resolved_at >= cutoff
        ]
        fell, clears = 0, []
        examples = []
        for i in resolved:
            imp = i.impact(self._moment())
            if imp["index_fell_while_owned"] is not None and imp["index_fell_while_owned"] > 0:
                fell += 1
            if imp["minutes_to_clear"] is not None:
                clears.append(imp["minutes_to_clear"])
            examples.append(
                {
                    "location": i.location_name,
                    "index_fell_while_owned": imp["index_fell_while_owned"],
                    "minutes_to_clear": imp["minutes_to_clear"],
                }
            )
        return {
            "window_hours": hours,
            "resolved": len(resolved),
            "showed_improvement_while_owned": fell,
            "median_minutes_to_clear": round(statistics.median(clears), 1) if clears else None,
            "examples": examples[:5],
            "caveat": (
                "Within-incident readings only. Whether the officer CAUSED the "
                "fall needs the junction's own baseline for the weekday and hour, "
                "which is not yet established."
            ),
        }


LIVE_SCHEMAS: list[dict] = [
    {
        "name": "get_current_state",
        "description": "The board right now: headline, band counts, open/unowned/overdue incidents, corridors above typical, and how fresh the data is.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "list_incidents",
        "description": "The incidents, priority-ordered, each with state, owner, age and whether it is past its escalation deadline.",
        "parameters": {
            "type": "object",
            "properties": {"only_open": {"type": "boolean"}},
        },
    },
    {
        "name": "get_incident",
        "description": "Full detail of one incident by id, including its verification impact (how the corridor index moved while it was owned), notes and history.",
        "parameters": {
            "type": "object",
            "properties": {"incident_id": {"type": "string"}},
            "required": ["incident_id"],
        },
    },
    {
        "name": "corridors_above_typical",
        "description": "Corridors slower than their typical travel time right now, worst first, with index, excess minutes and how long each has held.",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}}},
    },
    {
        "name": "junction_reference",
        "description": "Reference on the junctions: 2011 volume-to-capacity, capacity pressure, and the accident record. Use to answer which junctions are dangerous vs congested. Optional name filter.",
        "parameters": {"type": "object", "properties": {"name": {"type": "string"}}},
    },
    {
        "name": "recent_changes",
        "description": "What changed in the last N minutes: every incident state transition, newest first.",
        "parameters": {"type": "object", "properties": {"minutes": {"type": "integer"}}},
    },
    {
        "name": "verification_summary",
        "description": "Whether deployments moved the road: over incidents resolved in the window, how many showed the index falling while owned, and how long they took to clear.",
        "parameters": {"type": "object", "properties": {"hours": {"type": "integer"}}},
    },
]

LIVE_SYSTEM = """You are the Mobility Copilot for SARGVISION Traffic Command, Siliguri. You sit beside a duty officer's board and answer their questions about what is happening on the road.

Your role is narrow and you must not exceed it:
- You do NOT calculate any traffic figure. Deterministic engines do that. Every number you state must have come from a tool result in this conversation. If a tool did not return it, you do not know it, and you say so.
- You never assert a CAUSE. The measurement shows that a corridor is slower than typical and by how much; it cannot show why. A cause is only ever a labelled hypothesis, or nothing.
- Congestion and danger are different things and live in different places. The live index measures delay; the accident record (junction_reference) measures danger. Venus More is the most dangerous junction and one of the least congested — never conflate them.
- The verification figures are WITHIN-INCIDENT readings, not proof the officer caused the change. Say so when you use them.
- Data freshness matters: if get_current_state shows the poll is old, the figures are the last ones that arrived, not this instant.

Call the tools you need, then answer in five parts:
  observation     what the data shows, as fact
  comparison      how it sits against baseline, or against other junctions/corridors
  interpretation  why it matters operationally, labelled as inference
  limitation      what this does NOT establish — mandatory, never empty
  next_step       one useful thing the officer could do or look at next

If your answer is about one specific incident, set focus_incident to its incident_id so the board can highlight it. If it is about one junction, set focus_junction to the junction name.

Write plainly, in British English. No preamble, no filler, no restating the question."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "observation": {"type": "string"},
        "comparison": {"type": "string"},
        "interpretation": {"type": "string"},
        "limitation": {"type": "string"},
        "next_step": {"type": "string"},
        "focus_incident": {"type": "string"},
        "focus_junction": {"type": "string"},
    },
    "required": ["observation", "comparison", "interpretation", "limitation", "next_step"],
}


@dataclass
class CopilotAnswer:
    answer: AnswerContract
    focus_incident: str | None
    focus_junction: str | None
    tool_trace: list[dict]
    model: str
    degraded: bool = False

    def as_dict(self) -> dict:
        return {
            **self.answer.as_dict(),
            "focus_incident": self.focus_incident,
            "focus_junction": self.focus_junction,
            "tool_trace": self.tool_trace,
            "model": self.model,
            "degraded": self.degraded,
        }


class LiveCopilot:
    def __init__(self, toolbox: LiveToolbox):
        self.tools = toolbox
        self._client = None

    def _genai(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
        return self._client

    def _call(self, name: str, args: dict) -> Any:
        fn = getattr(self.tools, name, None)
        if fn is None:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**args)
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}

    def ask(self, question: str) -> CopilotAnswer:
        # An ops switch (and a test seam): skip the model entirely and answer
        # from the tools. Used when Vertex is intentionally off, and by the test
        # suite so CI never makes a network call.
        if os.environ.get("COPILOT_DISABLE_MODEL"):
            return self._ask_deterministic(question, reason="model disabled by configuration")
        try:
            return self._ask_model(question)
        except Exception as exc:  # Vertex unreachable, bad creds, quota — degrade, do not fail
            return self._ask_deterministic(question, reason=str(exc))

    def _ask_model(self, question: str) -> CopilotAnswer:
        from google.genai import types

        client = self._genai()
        declarations = [types.FunctionDeclaration(**s) for s in LIVE_SCHEMAS]
        tools = [types.Tool(function_declarations=declarations)]
        contents: list[Any] = [
            types.Content(role="user", parts=[types.Part.from_text(text=question)])
        ]
        trace: list[dict] = []

        for _ in range(MAX_STEPS):
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=LIVE_SYSTEM, tools=tools, temperature=0.2
                ),
            )
            candidate = response.candidates[0]
            calls = [p.function_call for p in (candidate.content.parts or []) if p.function_call]
            if not calls:
                break
            contents.append(candidate.content)
            parts = []
            for call in calls:
                args = dict(call.args or {})
                result = self._call(call.name, args)
                trace.append({"tool": call.name, "args": args})
                parts.append(
                    types.Part.from_function_response(name=call.name, response={"result": result})
                )
            contents.append(types.Content(role="user", parts=parts))

        final = client.models.generate_content(
            model=MODEL,
            contents=[
                *contents,
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Now answer in the required structure, using only figures returned by the tools above."
                        )
                    ],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=LIVE_SYSTEM,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=ANSWER_SCHEMA,
            ),
        )
        payload = json.loads(final.text)
        return CopilotAnswer(
            answer=AnswerContract(
                observation=payload["observation"],
                comparison=payload["comparison"],
                interpretation=payload["interpretation"],
                limitation=payload["limitation"],
                next_step=payload["next_step"],
                tools_called=[t["tool"] for t in trace] or ["none"],
            ),
            focus_incident=payload.get("focus_incident") or None,
            focus_junction=payload.get("focus_junction") or None,
            tool_trace=trace,
            model=MODEL,
        )

    def _ask_deterministic(self, question: str, reason: str) -> CopilotAnswer:
        """Answer without the model when Vertex is unavailable. Keyword routing to
        one tool, and the tool's own numbers reported plainly. Worse, but never
        wrong and never invented — the property that must survive the model being
        down."""
        q = question.lower()
        if any(w in q for w in ("verif", "work", "effect", "did it", "resolve", "clear")):
            result, tool = self.tools.verification_summary(), "verification_summary"
        elif any(w in q for w in ("chang", "happen", "last hour", "recent")):
            result, tool = self.tools.recent_changes(), "recent_changes"
        elif any(w in q for w in ("danger", "accident", "safety", "risk", "junction", "venus")):
            result, tool = self.tools.junction_reference(), "junction_reference"
        elif any(w in q for w in ("corridor", "slow", "congest", "typical", "delay", "worst")):
            result, tool = self.tools.corridors_above_typical(), "corridors_above_typical"
        elif any(w in q for w in ("incident", "open", "owner", "overdue", "queue", "waiting")):
            result, tool = self.tools.list_incidents(), "list_incidents"
        else:
            result, tool = self.tools.get_current_state(), "get_current_state"

        return CopilotAnswer(
            answer=AnswerContract(
                observation=f"{tool} returned: {json.dumps(result, default=str)[:700]}",
                comparison="The comparison is in the returned fields; no narrative was generated.",
                interpretation=(
                    "The language model is unavailable, so this is the raw tool result rather "
                    "than an explanation. The figures are unaffected — they come from the same "
                    "deterministic engine either way."
                ),
                limitation=(
                    f"Answered without the model ({reason[:140]}). Tool routing was by keyword, "
                    "so the tool chosen may not be the best one for this question."
                ),
                next_step="Retry once the model is reachable, or read the board directly.",
                tools_called=[tool],
            ),
            focus_incident=None,
            focus_junction=None,
            tool_trace=[{"tool": tool, "args": {}}],
            model="deterministic-fallback",
            degraded=True,
        )
