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
from pathlib import Path
from typing import Any

from packages.command.centre import CommandCentre
from packages.contracts.response import AnswerContract
from packages.copilot.grounding_safety import SAFETY

CURATED = Path("data/curated")
MODEL = os.environ.get("COPILOT_MODEL", "gemini-2.5-flash")
PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "sargvision-traffic-intel")
# Default to the Mumbai region, not a US one: the copilot's prompts carry live
# incident text and officer context, and Indian police data should not leave the
# country by default. Overridable, but the safe default is in-country.
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-south1")
MAX_STEPS = 5


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

    def historical_day_shape(self, day_type: str = "WEEKDAY") -> dict:
        """The typical shape of the day from the 2019 city study — the PAST layer.

        City-wide structure, seven years old, not corridor-specific. It is how to
        read whether today is normal for the hour, and nothing more; the copilot
        must present it as context, never as a live or per-junction figure.
        """
        import polars as pl

        path = CURATED / "patterns_hourly.parquet"
        if not path.exists():
            return {"error": "the historical city profile has not been built"}
        dt = day_type.upper()
        if dt not in ("WEEKDAY", "WEEKEND", "ALL"):
            dt = "WEEKDAY"
        frame = pl.read_parquet(path).filter(pl.col("day_type") == dt).sort("hour")
        hours = [
            {
                "hour": int(r["hour"]),
                "index": round(r["median_tti"], 3),
                "speed_kmh": round(r["median_speed_kmh"], 1),
                "sample_size": int(r["sample_size"]),
                "congested": bool(r["congested"]),
            }
            for r in frame.iter_rows(named=True)
        ]
        peak = sorted(hours, key=lambda h: -h["index"])[:3]
        return {
            "day_type": dt,
            "hours": hours,
            "worst_hours": [{"hour": h["hour"], "index": h["index"]} for h in peak],
            "vintage": "2019 study, city-wide",
            "caveat": (
                "City-wide structure only — 7 years old and not specific to any junction. "
                "Read it as 'is today normal for this hour', not as a live baseline."
            ),
        }

    def data_confidence(self) -> dict:
        """How much to trust the live picture: coverage and freshness now."""
        c = self.centre
        observed = sum(1 for s in c.status.values() if s.latest is not None)
        total = len(c.status)
        moment = self._moment()
        return {
            "corridors_total": total,
            "corridors_observed": observed,
            "coverage_pct": round(100 * observed / total, 1) if total else 0.0,
            "cycles_run": c.cycles,
            "poll_age_minutes": round((self._now() - moment).total_seconds() / 60, 1),
            "caveat": "A corridor not yet observed has no reading; unobserved corridors are not 'clear'.",
        }

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

    def deployment_effects(self, only_active: bool = False) -> dict:
        """Did the postings work? Each deployment's measured before/after — the
        one question a roster and a radio cannot answer. Uses the corridor's own
        baseline as the counterfactual and never claims cause it cannot show."""
        c = self.centre
        moment = self._moment()
        deps = sorted(c.deployments.values(), key=lambda d: d.started_at, reverse=True)
        if only_active:
            deps = [d for d in deps if d.is_active]
        return {
            "count": len(deps),
            "deployments": [d.effect(c.history, moment) for d in deps[:10]],
        }

    def _resolve_corridor(self, name: str) -> str | None:
        q = name.lower()
        for cid, st in self.centre.status.items():
            if q in st.name.lower():
                return cid
        return None

    def corridor_history(self, name: str) -> dict:
        """This corridor against ITS OWN past: is now unusual for this weekday and
        hour, what is typical here, and which way it has been drifting. The
        per-corridor baseline the 2019 city study could never give."""
        cid = self._resolve_corridor(name)
        if cid is None:
            return {"error": f"no corridor matching {name!r}"}
        st = self.centre.status[cid]
        moment = self._moment()
        hist = self.centre.history
        out: dict = {"corridor": st.name, "live_index": st.index, "live_band": st.band}
        if st.index is not None:
            out["vs_baseline"] = hist.now_vs_baseline(cid, moment, st.index)
        else:
            out["vs_baseline"] = {"verdict": "not observed this cycle"}
        prof = hist.day_profile(cid, moment.weekday())
        if prof:
            out["typical_today"] = {
                "weekday": prof["weekday"],
                "worst_hours": prof["worst_hours"],
                "observations": prof["observations"],
            }
        tr = hist.trend(cid)
        if tr:
            out["trend"] = {
                "direction": tr["direction"],
                "drift": tr["drift"],
                "days": tr["days_observed"],
            }
        return out

    def corridor_forecast(self, name: str, hours: int = 3) -> dict:
        """The corridor's own median for the next few hours, nudged by its recent
        drift. A transparent baseline expectation, never a claim about the future."""
        cid = self._resolve_corridor(name)
        if cid is None:
            return {"error": f"no corridor matching {name!r}"}
        fc = self.centre.history.forecast(cid, self._moment(), hours)
        if fc is None:
            return {"error": "no history for this corridor yet"}
        return fc

    def suggest_interventions(self, junction: str | None = None) -> dict:
        """Candidate actions to TEST at a junction, each with what to measure.

        The officer's follow-on question after "which junction is worst": what
        can we actually try? Each item is a hypothesis, not an asserted fix, and
        names the before/after figure that will decide whether it worked."""
        from packages.copilot.interventions import suggest

        return suggest(self.centre, junction, self._now())


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
    {
        "name": "historical_day_shape",
        "description": "The TYPICAL shape of the day from the 2019 city study — how travel time normally varies by hour, and the usual worst hours. Use for 'when is it usually worst', 'what does a normal weekday evening look like', or to judge whether now is normal for the hour. City-wide and 7 years old, not per-junction.",
        "parameters": {"type": "object", "properties": {"day_type": {"type": "string"}}},
    },
    {
        "name": "data_confidence",
        "description": "How much to trust the live picture: how many corridors have been observed this cycle, coverage percent, and how fresh the data is.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "deployment_effects",
        "description": "Whether officer postings actually moved the road: each deployment's measured before/after speed, how it compares to the corridor's own typical, and an honest verdict. Use for 'did the deployment work', 'did posting an officer help', 'did what we did at X work'. Pass only_active for postings still on the ground.",
        "parameters": {"type": "object", "properties": {"only_active": {"type": "boolean"}}},
    },
    {
        "name": "corridor_history",
        "description": "How one corridor sits against ITS OWN learned history: whether now is unusual for this weekday and hour, what is typical for it here, and which way it has been drifting over recent weeks. This is the per-corridor baseline — use it for 'is this normal for a Tuesday evening', 'is this corridor getting worse', or 'is now unusual here'. Names the corridor (a road/segment name).",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "corridor_forecast",
        "description": "The corridor's own typical index for the next few hours, nudged by its recent trend — a transparent baseline expectation, explicitly NOT a prediction of the future. Use for 'what should we expect on this corridor over the next couple of hours'. Names the corridor.",
        "parameters": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "hours": {"type": "integer"}},
            "required": ["name"],
        },
    },
    {
        "name": "suggest_interventions",
        "description": "Propose candidate traffic interventions to TEST on the ground for a junction — each a labelled hypothesis with what to measure, what to expect and its risk. Use when the officer asks what they can actually try, what would help, what to do about a slow junction, or how to fix it. Names the junction to profile it; omit for the worst live one. These are actions to trial and verify, never asserted fixes.",
        "parameters": {"type": "object", "properties": {"junction": {"type": "string"}}},
    },
]

LIVE_SYSTEM = """You are the Mobility Copilot for SARGVISION Traffic Command, Siliguri. You sit beside a duty officer's board and answer their questions about what is happening on the road.

Your role is narrow and you must not exceed it:
- You do NOT calculate any traffic figure. Deterministic engines do that. Every number you state must have come from a tool result in this conversation. If a tool did not return it, you do not know it, and you say so.
- You never assert a CAUSE. The measurement shows that a corridor is slower than typical and by how much; it cannot show why. A cause is only ever a labelled hypothesis, or nothing.
- Congestion and danger are different things and live in different places. The live index measures delay; the accident record (junction_reference) measures danger. Venus More is the most dangerous junction and one of the least congested — never conflate them.
- The verification figures are WITHIN-INCIDENT readings, not proof the officer caused the change. Say so when you use them.
- deployment_effects is the product's core question — did a posting move the road. Report its measured before/after (in km/h, which officers read) and its verdict, and carry its comparison to the corridor's own typical. A single posting is evidence, not proof; say so. Never upgrade "improved while posted" into "the officer fixed it".
- When an officer asks what to DO about a junction — what can we try, what would help, how to fix it — call suggest_interventions. Present its candidates as actions to TEST, each with what will be measured to decide if it worked; never promise one will work. If the officer already knows the junction is slow, that is precisely the moment for this tool: the value you add is the next testable step, not restating the congestion.
- Data freshness matters: if get_current_state shows the poll is old, the figures are the last ones that arrived, not this instant.
- Past and present are BOTH available and you should use both when the question spans them. There are now TWO pasts, and they are not equal. historical_day_shape is the 2019 study — city-wide, seven years old, only a rough shape. corridor_history is THIS corridor's OWN learned baseline for this weekday and hour, built live from our own readings; it is the better answer to "is now unusual here" whenever it has enough observations. Prefer corridor_history for a specific corridor; fall back to historical_day_shape for the city as a whole or when the corridor has little history. Always say which past a figure came from.
- corridor_forecast is the corridor's own typical index for the coming hours. It is a baseline expectation, not a prediction — present it as "typically around X at this hour", never as "it will be X".
- The interface lists the sources of the data separately, so you do not have to recite citations. But in your prose, name which source a figure came from when it is not obvious — "live", "the 2019 study", "the 2011 survey", "the accident record" — so no number floats without its provenance.

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


# Where each tool's figures actually come from. Attached deterministically from
# the tools the copilot ran, so the citation cannot be something the model
# invented — it is a fact about which data was read.
def _sources_for(tools: list[str], last_poll: datetime | None) -> list[str]:
    live = (
        "SARGVISION congestion index, computed from Google Maps Routes travel-time "
        "(our own statistic — current time against Google's modelled typical, not "
        "Google's raw traffic data)"
        + (f", polled {last_poll.isoformat(timespec='minutes')} IST." if last_poll else ".")
    )
    log = "SARGVISION incident record — officer actions logged on this system."
    study_2019 = (
        "Akbar, Couture, Duranton & Storeygard, American Economic Review 113(4), 2023 — "
        "101,418 travel-time observations across Siliguri, June–November 2019 (city-wide, "
        "seven years old)."
    )
    junction_ref = (
        "Volume-to-capacity: Comprehensive Mobility Plan 2011, published in the Siliguri "
        "CDP 2041. Accident record: Roy, Mohammadi & Roy, Geographies 6(2):55, 2026 (2021–23)."
    )
    learned = (
        "SARGVISION corridor baseline — this corridor's own congestion index aggregated by "
        "weekday and hour from our live observations (derived statistics; no raw Google "
        "travel-time is stored)."
    )
    deploy = (
        "SARGVISION deployment record — officer postings logged on this system, with the "
        "corridor's own before/after speed measured across the posting."
    )
    live_tools = {
        "get_current_state",
        "list_incidents",
        "corridors_above_typical",
        "recent_changes",
        "data_confidence",
        "get_incident",
        "verification_summary",
        "suggest_interventions",
        "corridor_history",
        "deployment_effects",
    }
    junction_ref_tools = {"junction_reference", "suggest_interventions"}
    log_tools = {"list_incidents", "recent_changes", "get_incident", "verification_summary"}
    learned_tools = {"corridor_history", "corridor_forecast", "deployment_effects"}
    out: list[str] = []
    for src, hit in (
        (live, any(t in live_tools for t in tools)),
        (log, any(t in log_tools for t in tools)),
        (deploy, "deployment_effects" in tools),
        (learned, any(t in learned_tools for t in tools)),
        (study_2019, "historical_day_shape" in tools),
        (junction_ref, any(t in junction_ref_tools for t in tools)),
    ):
        if hit and src not in out:
            out.append(src)
    return out


def _trim(result: Any, cap: int = 24) -> Any:
    """Cap list fields so the data returned to the interface stays a summary, not
    a firehose. The frontend renders these as small widgets, and the model has
    already read the full result — this is only what travels back for display."""
    if isinstance(result, dict):
        out = {}
        for k, v in result.items():
            if isinstance(v, list) and len(v) > cap:
                out[k] = [*v[:cap], {"…": f"{len(v) - cap} more"}]
            else:
                out[k] = v
        return out
    return result


@dataclass
class CopilotAnswer:
    answer: AnswerContract
    focus_incident: str | None
    focus_junction: str | None
    tool_trace: list[dict]
    data: list[dict]  # {tool, result} — the figures behind the prose, for the UI
    sources: list[str]  # real citations for the data used, not the tool names
    model: str
    degraded: bool = False

    def as_dict(self) -> dict:
        return {
            **self.answer.as_dict(),
            "focus_incident": self.focus_incident,
            "focus_junction": self.focus_junction,
            "tool_trace": self.tool_trace,
            "data": self.data,
            "sources": self.sources,
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
                trace.append({"tool": call.name, "args": args, "result": _trim(result)})
                parts.append(
                    types.Part.from_function_response(name=call.name, response={"result": result})
                )
            contents.append(types.Content(role="user", parts=parts))

        # A model answer that consulted NO tool has no ground under it — every
        # figure would be the model's own, which is exactly what this copilot
        # refuses to emit. Rather than let source-less prose through (tools_called
        # would read "none" and still pass the contract), fall back to the
        # deterministic path, which always answers from a real tool result.
        if not trace:
            return self._ask_deterministic(
                question, reason="the model answered without consulting any tool"
            )

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
            tool_trace=[{"tool": t["tool"], "args": t["args"]} for t in trace],
            data=[{"tool": t["tool"], "result": t["result"]} for t in trace],
            sources=_sources_for([t["tool"] for t in trace], self.tools.centre.last_poll),
            model=MODEL,
        )

    def _ask_deterministic(self, question: str, reason: str) -> CopilotAnswer:
        """Answer without the model when Vertex is unavailable. Keyword routing to
        one tool, and the tool's own numbers reported plainly. Worse, but never
        wrong and never invented — the property that must survive the model being
        down."""
        q = question.lower()
        # If a corridor is named and the question is about its own past or its
        # outlook, answer from that corridor's learned baseline — the better past.
        named_corridor = next(
            (
                st.name
                for st in self.tools.centre.status.values()
                if st.name and st.name.lower() in q
            ),
            None,
        )
        if named_corridor and any(
            w in q
            for w in ("forecast", "expect", "next hour", "next couple", "coming hour", "outlook")
        ):
            result, tool = self.tools.corridor_forecast(named_corridor), "corridor_forecast"
        elif named_corridor and any(
            w in q
            for w in (
                "trend",
                "getting worse",
                "worse than usual",
                "unusual",
                "drift",
                "baseline",
                "normal for",
                "usual for",
                "usually",
                "typical",
            )
        ):
            result, tool = self.tools.corridor_history(named_corridor), "corridor_history"
        elif any(
            w in q
            for w in (
                "intervention",
                "what can we try",
                "what can i try",
                "what should we do",
                "what should i do",
                "what to do",
                "how to fix",
                "how do we fix",
                "how do i fix",
                "how can we fix",
                "solution",
                "workable",
                "recommend",
                "what would help",
                "what helps",
            )
        ):
            # Name the junction if the officer did; else the worst live one.
            named = next(
                (
                    j.name
                    for j in self.tools.centre.network.junctions.values()
                    if j.name.lower() in q
                ),
                None,
            )
            result, tool = self.tools.suggest_interventions(named), "suggest_interventions"
        elif any(
            w in q
            for w in (
                "usually",
                "normally",
                "typical",
                "typically",
                "history",
                "historical",
                "past",
                "shape of the day",
                "which hour",
                "what hour",
            )
        ):
            result, tool = self.tools.historical_day_shape(), "historical_day_shape"
        elif any(
            w in q
            for w in (
                "confiden",
                "coverage",
                "trust",
                "how good",
                "how many corridors",
                "how fresh",
            )
        ):
            result, tool = self.tools.data_confidence(), "data_confidence"
        elif any(
            w in q for w in ("deployment", "posting", "posted", "did the officer", "did we help")
        ):
            result, tool = self.tools.deployment_effects(), "deployment_effects"
        elif any(w in q for w in ("verif", "work", "effect", "did it", "resolve", "clear")):
            result, tool = self.tools.verification_summary(), "verification_summary"
        elif any(w in q for w in ("chang", "happen", "last hour", "recent")):
            result, tool = self.tools.recent_changes(), "recent_changes"
        elif any(w in q for w in ("danger", "accident", "safety", "risk", "junction", "venus")):
            result, tool = self.tools.junction_reference(), "junction_reference"
        elif any(w in q for w in ("corridor", "slow", "congest", "delay", "worst")):
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
            data=[{"tool": tool, "result": _trim(result)}],
            sources=_sources_for([tool], self.tools.centre.last_poll),
            model="deterministic-fallback",
            degraded=True,
        )
