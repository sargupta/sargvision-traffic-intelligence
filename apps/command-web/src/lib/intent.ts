/** The intent layer.
 *
 *  One vocabulary of officer actions, one parser, one commit path. Voice and
 *  chat are only parsers that produce an `Intent`; a click produces the same
 *  `Intent` directly. Nothing here talks to the network — `runIntent` in the
 *  UI routes a resolved intent to the existing `act()` POST. That separation is
 *  the whole point: the parser can be offline or wrong and the console still
 *  works by click, because click never passes through it.
 *
 *  Two rules carried from the research (CAD status engines, ATC readback,
 *  enterprise voice):
 *   1. Grounding is enum-constrained. The parser may only *select* a real
 *      incident or officer from the live lists it is given; it can never mint
 *      an id. Wrong-entity binding is the first way these interfaces fail.
 *   2. Only genuinely irreversible acts confirm. `resolve`, `stand down` and
 *      `close` read back and wait; everything else executes and offers undo.
 *      Confirming everything trains the officer to confirm without reading.
 */

import type { Incident, IncidentState, Officer } from "./api";

export type ActionPath =
  | "acknowledge"
  | "assign"
  | "on-scene"
  | "clearing"
  | "resolve"
  | "close"
  | "stand-down"
  | "note";

export type IntentSource = "click" | "chat" | "voice";

/** A fully-resolved, ready-to-commit action. */
export interface Intent {
  action: ActionPath;
  incidentId: string;
  /** assign only */
  to?: string;
  unit?: string;
  /** note / stand-down / close */
  text?: string;
  kind?: string;
  source: IntentSource;
  /** 0..1 — how sure the parse is. 1 for a click. */
  confidence: number;
  rawUtterance?: string;
}

/** Whether an action changes state in a way that cannot be casually undone.
 *  These read back and wait; the rest execute optimistically with undo. */
export function isDestructive(action: ActionPath): boolean {
  return action === "resolve" || action === "stand-down" || action === "close";
}

/** The target incident state an action moves to (for the legality check). */
const ACTION_TARGET: Record<ActionPath, IncidentState | null> = {
  acknowledge: "ACKNOWLEDGED",
  assign: "ASSIGNED",
  "on-scene": "ON_SCENE",
  clearing: "CLEARING",
  resolve: "RESOLVED",
  close: "CLOSED",
  "stand-down": "STOOD_DOWN",
  note: null, // a note is legal in any open state
};

/** Verb synonyms → action. Ordered so multi-word phrases match before the
 *  single words they contain ("no action" before "action"). */
const VERBS: [RegExp, ActionPath][] = [
  [/\b(stand[-\s]?down|no action|leave it|not needed)\b/, "stand-down"],
  [/\b(on[-\s]?scene|arrived|on site|i'?m there|reached)\b/, "on-scene"],
  [/\b(mark )?clearing\b/, "clearing"],
  [/\b(resolve[d]?|cleared|clear it|moving again|all clear|sorted|done)\b/, "resolve"],
  [/\b(close|closed)\b/, "close"],
  [/\b(assign|send|dispatch|deploy|give it to|put .* on)\b/, "assign"],
  [/\b(ack(nowledge)?|take it|got it|seen|noted as seen|pick up)\b/, "acknowledge"],
  [/\b(note|log|record|remark|comment)\b/, "note"],
];

/** Cause taxonomy for a captured note (shared with the field surface). */
export const CAUSES = [
  "Vehicle breakdown",
  "Road works",
  "Signal not working",
  "Encroachment / parking",
  "Procession or event",
  "Waterlogging",
  "Accident",
  "Heavy volume only",
] as const;

export interface ParseContext {
  incidents: Incident[];
  roster: Officer[];
  source: IntentSource;
}

export type ParseOutcome =
  | { kind: "ready"; intent: Intent; confirm: boolean; readback: string }
  | {
      kind: "disambiguate";
      field: "incident" | "officer";
      options: { id: string; label: string }[];
      partial: Partial<Intent> & { action: ActionPath };
      prompt: string;
    }
  | {
      kind: "need";
      field: "incident" | "officer" | "text";
      partial: Partial<Intent> & { action: ActionPath };
      prompt: string;
    }
  | { kind: "unknown"; reason: string };

function norm(s: string): string {
  return s.toLowerCase().replace(/[.,!?]/g, " ").replace(/\s+/g, " ").trim();
}

/** Whether an utterance opens with a recognised verb — i.e. it is a fresh
 *  command, not a reply to a pending question. Lets the officer abandon a
 *  half-finished command just by starting a new one. */
export function startsWithVerb(utterance: string): boolean {
  const t = norm(utterance);
  return VERBS.some(([re]) => re.test(t));
}

/** Generic words that appear in many junction names and would otherwise cause a
 *  false match ("resolve airport road" must not resolve "Sevoke Road"). The
 *  distinctive token in "Venus More" is "venus", not "more"; in "Siliguri
 *  Junction" it is "siliguri". So the common tail words are stopped and only the
 *  distinctive part scores. Multi-word place phrases still score via PHRASES. */
const STOP = new Set([
  "road", "near", "traffic", "slow", "more", "crossing", "station", "junction",
  "bypass", "nh10", "the", "and", "for", "moving", "again", "this", "that", "post",
]);

/** Distinctive multi-word place names, worth more than a single-token overlap. */
const PHRASES = [
  "venus more", "siliguri junction", "air view", "sevoke road", "sevoke more",
  "court more", "mahananda", "darjeeling more", "champasari", "hill cart",
  "pani tanki", "thana more", "jalpai", "naukaghat", "check post", "wall ford",
  "ashighar", "jhankaar", "njp",
];

/** Officers eligible to be dispatched to (not the duty officer at the desk). */
function dispatchable(roster: Officer[]): Officer[] {
  return roster.filter((o) => o.role !== "DUTY_OFFICER");
}

/** Resolve a phrase to at most a few real officers. Enum-constrained: only ever
 *  returns officers from the roster it was given. */
export function matchOfficers(text: string, roster: Officer[]): Officer[] {
  const t = norm(text);
  const pool = dispatchable(roster);
  const hits = new Set<Officer>();

  // "guard 2" / "traffic guard 2" → TG-2 ; "patrol 1" / "pcr 1" → PCR-1
  const guardN = t.match(/\b(?:traffic )?guard\s*(\d+)\b/);
  if (guardN) pool.filter((o) => o.officer_id === `TG-${guardN[1]}`).forEach((o) => hits.add(o));
  const patrolN = t.match(/\b(?:mobile )?(?:patrol|pcr)\s*(\d+)\b/);
  if (patrolN) pool.filter((o) => o.officer_id === `PCR-${patrolN[1]}`).forEach((o) => hits.add(o));

  for (const o of pool) {
    const id = o.officer_id.toLowerCase();
    const name = o.name.toLowerCase();
    const unit = o.unit.toLowerCase();
    if (t.includes(id) || t.includes(unit)) hits.add(o);
    // name: match on any distinctive token of the officer's name (>2 chars)
    const nameTokens = name.split(/\s+/).filter((w) => w.length > 2);
    if (nameTokens.some((w) => t.includes(w))) hits.add(o);
  }
  return [...hits];
}

/** Resolve a phrase to open incidents by junction, location or title.
 *  Enum-constrained to the incidents given; scored so an exact junction beats a
 *  loose word overlap. */
export function matchIncidents(text: string, incidents: Incident[]): Incident[] {
  const t = norm(text);
  const open = incidents.filter((i) => i.is_open);

  // Direct id, e.g. "INC-7CFAF27D". Word-boundary, not a loose substring, so a
  // short id can never match by accident inside an ordinary word.
  const idHit = open.filter((i) => {
    const id = i.incident_id.toLowerCase().replace(/[^a-z0-9]/g, "\\$&");
    return new RegExp(`\\b${id}\\b`).test(t);
  });
  if (idHit.length) return idHit;

  const scored = open
    .map((i) => {
      const hay = norm(`${i.location_name} ${i.title} ${i.junctions.join(" ")}`);
      const hayTokens = new Set(hay.split(" ").filter((w) => w.length > 2));
      const words = t.split(" ").filter((w) => w.length > 2 && !STOP.has(w));
      let score = 0;
      for (const w of words) if (hayTokens.has(w)) score += 1;
      // a contiguous place phrase ("venus more", "siliguri junction") is worth more
      for (const p of PHRASES) if (t.includes(p) && hay.includes(p)) score += 3;
      return { i, score };
    })
    .filter((s) => s.score > 0)
    .sort((a, b) => b.score - a.score);

  if (!scored.length) return [];
  // keep the top score band (ties are a real ambiguity to surface)
  const top = scored[0].score;
  return scored.filter((s) => s.score === top).map((s) => s.i);
}

function legalFor(incident: Incident, action: ActionPath): boolean {
  const target = ACTION_TARGET[action];
  if (target === null) return incident.is_open; // note
  if (incident.next_actions.includes(target)) return true;
  // Assign auto-acknowledges a freshly detected incident on the server, so it
  // is legal straight from DETECTED even though next_actions lists ACKNOWLEDGED
  // first. The board's own "assign" path relies on the same behaviour.
  if (action === "assign" && incident.state === "DETECTED") {
    return incident.next_actions.includes("ACKNOWLEDGED");
  }
  return false;
}

function legalActionsLabel(incident: Incident): string {
  const verbs: Record<string, string> = {
    ACKNOWLEDGED: "acknowledge",
    ASSIGNED: "assign",
    ON_SCENE: "mark on scene",
    CLEARING: "mark clearing",
    RESOLVED: "resolve",
    CLOSED: "close",
    STOOD_DOWN: "stand down",
  };
  const list = incident.next_actions.map((s) => verbs[s]).filter(Boolean);
  return list.length ? list.join(", ") : "no further action";
}

function readbackFor(intent: Intent, incident: Incident, officer?: Officer): string {
  const place = incident.location_name || incident.title;
  switch (intent.action) {
    case "assign":
      return `Assign ${place} to ${officer?.name ?? intent.to}.`;
    case "resolve":
      return `Resolve ${place} — traffic moving again?`;
    case "stand-down":
      return `Stand down ${place} — no officer needed${intent.text ? ` (${intent.text})` : ""}?`;
    case "close":
      return `Close ${place}${intent.text ? `: ${intent.text}` : ""}?`;
    case "on-scene":
      return `Mark on scene at ${place}.`;
    case "clearing":
      return `Mark ${place} clearing.`;
    case "acknowledge":
      return `Acknowledge ${place}.`;
    case "note":
      return `Log against ${place}: ${intent.text}.`;
  }
}

/** Parse a natural-language utterance into an outcome. Pure; deterministic;
 *  no network. The caller decides what to do with each outcome. */
export function parseCommand(utterance: string, ctx: ParseContext): ParseOutcome {
  const t = norm(utterance);
  if (!t) return { kind: "unknown", reason: "Say or type an action, e.g. “assign Venus More to guard 2”." };

  const verb = VERBS.find(([re]) => re.test(t));
  if (!verb) {
    return {
      kind: "unknown",
      reason: "No action recognised. Try: acknowledge, assign, on scene, clearing, resolve, stand down, note.",
    };
  }
  const action = verb[1];

  // ── resolve the incident ─────────────────────────────────────────────────
  const incidentMatches = matchIncidents(t, ctx.incidents);
  const openCount = ctx.incidents.filter((i) => i.is_open).length;

  if (incidentMatches.length === 0) {
    // If exactly one incident is open, a bare verb ("resolve it") is unambiguous.
    const open = ctx.incidents.filter((i) => i.is_open);
    if (open.length === 1) {
      return finish(action, open[0], t, ctx);
    }
    return {
      kind: "need",
      field: "incident",
      partial: { action },
      prompt:
        openCount === 0
          ? "There are no open incidents to act on."
          : "Which incident? Name the junction or location.",
    };
  }
  if (incidentMatches.length > 1) {
    return {
      kind: "disambiguate",
      field: "incident",
      options: incidentMatches.map((i) => ({ id: i.incident_id, label: i.location_name || i.title })),
      partial: { action },
      prompt: "Which one?",
    };
  }

  return finish(action, incidentMatches[0], t, ctx);
}

/** Complete the parse once the incident is known. */
function finish(action: ActionPath, incident: Incident, t: string, ctx: ParseContext): ParseOutcome {
  if (!legalFor(incident, action)) {
    return {
      kind: "unknown",
      reason: `${incident.location_name} is ${incident.state.toLowerCase().replace("_", " ")} — you can ${legalActionsLabel(incident)}.`,
    };
  }

  const base: Intent = {
    action,
    incidentId: incident.incident_id,
    source: ctx.source,
    confidence: ctx.source === "click" ? 1 : 0.85,
    rawUtterance: t,
  };

  // assign needs an officer
  if (action === "assign") {
    const officers = matchOfficers(t, ctx.roster);
    if (officers.length === 0) {
      return {
        kind: "need",
        field: "officer",
        partial: { ...base },
        prompt: "Assign to whom? Name the guard or unit.",
      };
    }
    if (officers.length > 1) {
      return {
        kind: "disambiguate",
        field: "officer",
        options: officers.map((o) => ({ id: o.officer_id, label: `${o.name} · ${o.unit}` })),
        partial: { ...base },
        prompt: "Which officer?",
      };
    }
    const o = officers[0];
    const intent: Intent = { ...base, to: o.name, unit: o.unit };
    return { kind: "ready", intent, confirm: false, readback: readbackFor(intent, incident, o) };
  }

  // stand-down needs a reason; close needs an outcome
  if (action === "stand-down" || action === "close") {
    const reason = extractReason(t, action, incident);
    if (!reason) {
      return {
        kind: "need",
        field: "text",
        partial: { ...base },
        prompt: action === "stand-down" ? "Reason no officer is needed?" : "Closing outcome?",
      };
    }
    const intent: Intent = { ...base, text: reason };
    return { kind: "ready", intent, confirm: true, readback: readbackFor(intent, incident) };
  }

  if (action === "note") {
    const text = extractReason(t, action, incident);
    if (!text) {
      return { kind: "need", field: "text", partial: { ...base }, prompt: "What should the note say?" };
    }
    const intent: Intent = { ...base, text, kind: "NOTE" };
    return { kind: "ready", intent, confirm: false, readback: readbackFor(intent, incident) };
  }

  return {
    kind: "ready",
    intent: base,
    confirm: isDestructive(action),
    readback: readbackFor(base, incident),
  };
}

/** Pull the free-text tail (the reason / outcome / note body) out of an
 *  utterance, after removing the verb and the incident's own place words — so
 *  "stand down venus more" yields no reason and asks for one, while "stand down
 *  venus more local officer says clear" yields "local officer says clear". */
function extractReason(t: string, _action: ActionPath, incident?: Incident): string | undefined {
  let s = t;
  if (incident) {
    const place = norm(`${incident.location_name} ${incident.junctions.join(" ")}`)
      .split(" ")
      .filter((w) => w.length > 2);
    for (const w of place) {
      s = s.replace(new RegExp(`\\b${w.replace(/[^a-z0-9]/g, "\\$&")}\\b`, "g"), " ");
    }
  }
  const cut = s
    .replace(/\b(stand[-\s]?down|no action|resolve[d]?|close[d]?|note|log|record|because|reason|as|it|for)\b/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return cut.length >= 3 ? cut : undefined;
}

/** Fill a pending slot from a follow-up reply (the chatbot loop). */
export function completeWithIncident(
  partial: Partial<Intent> & { action: ActionPath },
  incident: Incident,
  ctx: ParseContext,
): ParseOutcome {
  return finish(partial.action, incident, partial.rawUtterance ?? "", ctx);
}
