"""The Mobility Copilot.

    question → plan → deterministic tools → structured results → explanation + view

The model does two jobs and no others: choose which tools answer the question,
and put what the tools returned into English. It never computes a traffic
figure, because it has no access to anything that would let it. Every number in
an answer came out of a tool call, and the tool trace is returned with the
answer so that can be checked rather than trusted.

The answer is an `AnswerContract`, which refuses to construct without a
limitation. A copilot that cannot say what the data fails to establish does not
get to speak to an officer.

The `view` it returns is how the interface reorganises itself — the copilot
controls the application, not just a chat panel.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from packages.contracts.response import AnswerContract
from packages.copilot.tools.analytics import SCHEMAS, Toolbox

MODEL = os.environ.get("COPILOT_MODEL", "gemini-2.5-flash")
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "sargvision-traffic-intel")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MAX_STEPS = 5

SYSTEM = """You are the Mobility Copilot for SARGVISION Traffic Intelligence, Siliguri.

Your role is narrow and you must not exceed it:

- You do NOT calculate traffic figures. Deterministic engines do that.
- Every number you state must have come from a tool result in this conversation.
  If a tool did not return it, you do not know it, and you say so.
- You never assert a cause. The data can establish that something changed and by
  how much; it cannot establish why. Offer a cause only as an explicitly labelled
  hypothesis, or not at all.
- You distinguish live conditions from historical analysis. Anything from
  get_anomalies, get_reliability, get_time_pattern or get_movement_summary is 2019
  historical analysis. Only get_current_state and get_recent_changes describe now.
- When the system is in HISTORICAL_REPLAY mode, say so rather than implying live
  monitoring.
- Confidence and sample size travel with every claim. A figure resting on 40
  observations is not the same claim as one resting on 4,000.

Call the tools you need, then answer in five parts:

  observation     what the data shows, as fact
  comparison      how it sits against baseline or against other movements
  interpretation  why it matters operationally, labelled as inference
  limitation      what this does NOT establish — mandatory, never empty
  next_step       what a traffic officer could usefully do or look at next

Also choose how the interface should reorganise to show your answer, as `view`:
  layout: one of map+detail, map+timeline, compare, timeline, coverage, feed
  focus_movements: movement IDS (the movement_id field, like SIL_Z00__SIL_Z03),
                   never the display name
  focus_zones: zone ids (like SIL_Z00)
  encode: what the map arcs should mean — deviation, reliability, delay, coverage

Write plainly, in British English. No preamble, no filler, no restating the
question."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "observation": {"type": "string"},
        "comparison": {"type": "string"},
        "interpretation": {"type": "string"},
        "limitation": {"type": "string"},
        "next_step": {"type": "string"},
        "view": {
            "type": "object",
            "properties": {
                "layout": {"type": "string"},
                "focus_movements": {"type": "array", "items": {"type": "string"}},
                "focus_zones": {"type": "array", "items": {"type": "string"}},
                "encode": {"type": "string"},
            },
            "required": ["layout", "encode"],
        },
    },
    "required": ["observation", "comparison", "interpretation", "limitation", "next_step", "view"],
}


@dataclass
class CopilotAnswer:
    answer: AnswerContract
    view: dict
    tool_trace: list[dict]
    model: str
    degraded: bool = False

    def as_dict(self) -> dict:
        return {
            **self.answer.as_dict(),
            "view": self.view,
            "tool_trace": self.tool_trace,
            "model": self.model,
            "degraded": self.degraded,
        }


class Copilot:
    def __init__(self, toolbox: Toolbox):
        self.tools = toolbox
        self._client = None

    def _genai(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
        return self._client

    def _normalise_view(self, view: dict) -> dict:
        """Resolve any display names the model returned back to movement ids.

        The prompt asks for ids and the tools now return them, but a view
        directive that silently addresses nothing is a failure the user cannot
        see — the map simply does not change. So the names are mapped back here
        rather than trusted.
        """
        focus = view.get("focus_movements") or []
        if not focus:
            return view
        known = self.tools.movement_ids()
        ids = set(known.values())
        resolved: list[str] = []
        for item in focus:
            if item in ids:
                resolved.append(item)
            elif item in known:
                resolved.append(known[item])
        view["focus_movements"] = resolved
        return view

    def _call(self, name: str, args: dict) -> Any:
        fn = getattr(self.tools, name, None)
        if fn is None:
            return {"error": f"unknown tool {name}"}
        try:
            return fn(**args)
        except TypeError as exc:
            return {"error": f"bad arguments for {name}: {exc}"}

    def ask(self, question: str) -> CopilotAnswer:
        try:
            return self._ask_model(question)
        except Exception as exc:
            return self._ask_deterministic(question, reason=str(exc))

    # ── model path ───────────────────────────────────────────────────────────
    def _ask_model(self, question: str) -> CopilotAnswer:
        from google.genai import types

        client = self._genai()
        declarations = [types.FunctionDeclaration(**s) for s in SCHEMAS]
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
                    system_instruction=SYSTEM, tools=tools, temperature=0.2
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
                            text="Now answer in the required structure, using only figures "
                            "returned by the tools above."
                        )
                    ],
                ),
            ],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM,
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=ANSWER_SCHEMA,
            ),
        )
        payload = json.loads(final.text)
        payload["view"] = self._normalise_view(payload.get("view") or {})

        return CopilotAnswer(
            answer=AnswerContract(
                observation=payload["observation"],
                comparison=payload["comparison"],
                interpretation=payload["interpretation"],
                limitation=payload["limitation"],
                next_step=payload["next_step"],
                tools_called=[t["tool"] for t in trace] or ["none"],
            ),
            view=payload["view"],
            tool_trace=trace,
            model=MODEL,
        )

    # ── deterministic fallback ───────────────────────────────────────────────
    def _ask_deterministic(self, question: str, reason: str) -> CopilotAnswer:
        """Answer without the model when it is unavailable.

        Keyword routing to one tool, and the tool's own numbers reported plainly.
        The answer is worse. It is not wrong, and it does not invent anything,
        which is the property that has to survive the model being down.
        """
        q = question.lower()
        if any(w in q for w in ("now", "current", "right now", "live", "state")):
            result, tool = self.tools.get_current_state(), "get_current_state"
        elif any(w in q for w in ("chang", "wrong", "happen", "alert", "priorit")):
            result, tool = self.tools.get_recent_changes(), "get_recent_changes"
        elif any(w in q for w in ("reliab", "unpredict", "depend", "variab", "buffer")):
            result, tool = self.tools.get_reliability(), "get_reliability"
        elif any(w in q for w in ("hour", "time of day", "evening", "morning", "pattern")):
            result, tool = self.tools.get_time_pattern(), "get_time_pattern"
        elif any(w in q for w in ("anomal", "unusual", "deviat")):
            result, tool = self.tools.get_anomalies(), "get_anomalies"
        elif any(w in q for w in ("confid", "evidence", "sample", "coverage")):
            result, tool = self.tools.get_data_confidence(), "get_data_confidence"
        else:
            result, tool = self.tools.get_movement_summary(), "get_movement_summary"

        rows = result.get("rows") or result.get("findings") or result.get("movements") or []
        head = rows[:3]

        return CopilotAnswer(
            answer=AnswerContract(
                observation=f"{tool} returned {len(rows)} rows. Top: {json.dumps(head, default=str)[:600]}",
                comparison="Comparison against baseline is in the returned fields; no narrative was generated.",
                interpretation=(
                    "The language model is unavailable, so this is the raw tool result "
                    "rather than an explanation. The figures are unaffected — they come "
                    "from the same deterministic engines either way."
                ),
                limitation=(
                    f"Answer generated without the model ({reason[:160]}). Tool routing was "
                    "by keyword, so the tool chosen may not be the best one for this question."
                ),
                next_step="Retry once the model is reachable, or query the tool directly.",
                tools_called=[tool],
            ),
            view={"layout": "feed", "encode": "deviation", "focus_movements": [], "focus_zones": []},
            tool_trace=[{"tool": tool, "args": {}}],
            model="deterministic-fallback",
            degraded=True,
        )
