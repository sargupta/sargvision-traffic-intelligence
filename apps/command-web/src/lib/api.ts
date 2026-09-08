"use client";

import { getToken } from "./auth";

import { useCallback, useEffect, useRef, useState } from "react";

export const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8099";

export type Band = "SEVERE" | "HIGH" | "ELEVATED" | "NORMAL" | "UNKNOWN";
export type Priority = "P1" | "P2" | "P3" | "P4";
export type IncidentState =
  | "DETECTED" | "ACKNOWLEDGED" | "ASSIGNED" | "ON_SCENE"
  | "CLEARING" | "RESOLVED" | "CLOSED" | "STOOD_DOWN" | "LAPSED";

export interface ChokePoint {
  severity: "SLOW" | "TRAFFIC_JAM";
  start: [number, number];
  end: [number, number];
  midpoint: [number, number];
  length_m: number;
  share_of_corridor: number;
}

/** One stretch of carriageway at a single traffic classification.
 *  `path` is [lon, lat] — GeoJSON and deck.gl order. */
export interface SpeedRun {
  speed: "NORMAL" | "SLOW" | "TRAFFIC_JAM";
  path: [number, number][];
  length_m: number;
}

/** Absolute level of service, from measured speed — how slow the road is in real
 *  terms, independent of whether that is unusual. */
export type Los = "FREE" | "MODERATE" | "HEAVY" | "STANDSTILL" | "UNKNOWN";
/** The absolute grade crossed with the deviation band: what to actually do. */
export type Condition = "ACUTE" | "CHRONIC" | "WATCH" | "CLEAR" | "UNKNOWN";

export interface CorridorRow {
  corridor_id: string;
  name: string;
  band: Band;
  /** Absolute severity (speed-based) — a chronic jam reads HEAVY/STANDSTILL even
   *  when its index sits near 1.0. */
  los?: Los;
  /** ACUTE (deploy now) / CHRONIC (structural) / WATCH / CLEAR. */
  condition?: Condition;
  index: number | null;
  excess_minutes: number | null;
  duration_minutes: number | null;
  typical_minutes: number | null;
  speed_kmh: number | null;
  roads: string;
  trend_per_10min: number | null;
  held_minutes: number;
  choke_points: ChokePoint[];
  runs: SpeedRun[];
  observed_at: string | null;
  approximate_location: boolean;
}

/** What the traffic classification means on the road.
 *
 *  Deliberately NOT the text tokens. Slow and stopped were --color-high and
 *  --color-sev, which sit 18 degrees apart in hue with a lightness gap of 5 —
 *  fine as text where a word carries the meaning, indistinguishable as two 4px
 *  lines on a map. Measured: deltaE 17.6.
 *
 *  These are chosen for lines instead. Slow moves lighter and more yellow,
 *  stopped moves darker: deltaE 45.3 with a lightness gap of 27. The lightness
 *  gap is the part that survives a thin stroke, a colour-vision deficiency, and
 *  a monochrome laser — under which the old three collapsed onto each other.
 *
 *  Contrast on white, against the 3:1 floor for a graphical object:
 *  moving 5.87:1, slow 3.19:1, stopped 8.31:1.
 */
export const RUN_COLOUR: Record<SpeedRun["speed"], [number, number, number]> = {
  NORMAL: [21, 115, 71],       // #157347
  SLOW: [217, 119, 6],         // #D97706 — lighter, more yellow
  TRAFFIC_JAM: [153, 27, 27],  // #991B1B — darker
};

/** Colour is never the only channel. Weight and dash carry the same meaning,
 *  so the map reads when printed in grey and when the reader cannot separate
 *  red from orange. Dashed reads as impeded; solid as blocked. */
export const RUN_STYLE: Record<
  SpeedRun["speed"],
  { width: number; dash: string | undefined; opacity: number }
> = {
  NORMAL: { width: 1.5, dash: undefined, opacity: 0.3 },
  SLOW: { width: 4, dash: "9 5", opacity: 0.95 },
  TRAFFIC_JAM: { width: 6, dash: undefined, opacity: 1 },
};

export interface Note {
  at: string;
  author: string;
  text: string;
  kind: "NOTE" | "CAUSE" | "ACTION" | "OUTCOME";
}

export interface Incident {
  incident_id: string;
  kind: string;
  priority: Priority;
  state: IncidentState;
  title: string;
  detail: string;
  location_name: string;
  lat: number;
  lon: number;
  corridors: string[];
  junctions: string[];
  detected_at: string;
  age_minutes: number;
  owner: string | null;
  is_open: boolean;
  needs_attention: boolean;
  evidence: Record<string, unknown>;
  limitation: string;
  assignments: { at: string; assigned_to: string; assigned_by: string; unit: string | null }[];
  notes: Note[];
  history: { at: string; from: string; to: string; by: string; reason: string | null }[];
  samples?: { at: string; index: number; band: string }[];
  impact?: IncidentImpact;
  escalation?: Escalation;
  next_actions: string[];
}
export interface Escalation {
  clock: "owner" | "on_scene" | null;
  level: "ok" | "due_soon" | "overdue" | "none";
  overdue: boolean;
  waiting_minutes: number;
  limit_minutes: number | null;
  minutes_over: number;
  due_by: string | null;
}

/** The within-incident verification reading. Not a counterfactual — see `basis`. */
export interface IncidentImpact {
  index_at_detection: number | null;
  index_on_scene: number | null;
  index_resolved: number | null;
  peak_index: number | null;
  minutes_to_scene: number | null;
  minutes_to_clear: number | null;
  index_fell_while_owned: number | null;
  samples: number;
  basis: string;
}

export interface Board {
  at: string;
  cycle: number;
  is_live: boolean;
  /** Server-authoritative freshness: LIVE / STALE / WARMING, from when data last
   *  arrived — not when the poll loop last ran. */
  data_state?: "LIVE" | "STALE" | "WARMING";
  feed?: {
    state: string;
    is_live: boolean;
    last_read_ok: string | null;
    read_age_seconds: number | null;
    reads_last_cycle: number;
    consecutive_read_failures: number;
    corridors_observed: number;
    corridors_total: number;
  };
  bands: Partial<Record<Band, number>>;
  /** How many corridors are acutely slow (deploy), chronically slow (structural),
   *  building, or clear — the absolute count the index-only board could not give. */
  conditions?: Partial<Record<Condition, number>>;
  headline: string;
  alert_budget: number;
  over_budget: boolean;
  suppressed: { holding: number; below_threshold: number; quiet_hours: number; budget: number };
  candidates_holding: number;
  unowned: number;
  incidents: Incident[];
  corridors: CorridorRow[];
  /** Cadence the collector is running at, so the screen can date its own
   *  figures rather than assume a threshold. */
  poll_seconds?: number;
}

export interface Junction {
  junction_id: string;
  name: string;
  lat: number;
  lon: number;
  control: string;
  vc_ratio: number | null;
  congestion_pressure: "OVER_CAPACITY" | "NEAR_CAPACITY" | "WITHIN_CAPACITY" | null;
  pin_approximate: boolean;
  pin_note: string;
}

export interface NetworkPayload {
  junctions: Junction[];
  corridors: {
    corridor_id: string; name: string;
    from_junction: string; to_junction: string; approximate: boolean;
  }[];
}

export interface Officer {
  officer_id: string; name: string; rank: string;
  role: string; unit: string;
  /** Optional: the roster endpoint omits off-duty units rather than flagging
   *  them, so a served officer is assignable. Undefined means available. */
  on_duty?: boolean;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json() as Promise<T>;
}

/** A refused action, carrying the status so a caller can tell the cases apart.
 *
 *  409 is the one that matters in a control room: it means the incident moved
 *  under the officer's feet — usually another officer got there first, or a
 *  slow network let the same click through twice. The API's reason is exact
 *  and belongs in the record, but it is written in the state machine's
 *  vocabulary ("cannot go ACKNOWLEDGED → ACKNOWLEDGED. Allowed: ..."), which
 *  is not what to put in front of someone holding a wireless.
 */
export class ActionError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(detail);
    this.name = "ActionError";
  }

  /** What to show the officer. */
  get human(): string {
    if (this.status === 409) return "Someone else has already moved this on — refreshed.";
    if (this.status === 401)
      return "Recording is locked. Unlock it from the top bar, then try again.";
    if (this.status === 503)
      return "Recording is disabled on this deployment. Nothing was saved — use the wireless.";
    if (this.status === 422 || this.status === 400) return this.detail;
    if (this.status >= 500) return "The command centre did not accept that. Try again.";
    return this.detail;
  }

  /** Whether the officer needs to supply a credential before retrying. */
  get needsToken(): boolean {
    return this.status === 401;
  }

  /** Whether the officer's copy of this incident is now known to be stale. */
  get stale(): boolean {
    return this.status === 409;
  }
}

export async function act(
  incidentId: string,
  action: string,
  body: { by: string; to?: string; unit?: string; text?: string; kind?: string },
): Promise<Incident> {
  const token = getToken();
  const r = await fetch(`${API}/api/incidents/${incidentId}/${action}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  const payload = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new ActionError(r.status, payload?.detail ?? `${action} failed (${r.status})`);
  }
  return payload as Incident;
}

/** The measured effect of one deployment — the product's core answer: did the
 *  posting move the road, and by how much. */
export interface DeploymentEffect {
  deployment_id: string;
  location: string;
  unit: string;
  purpose: string;
  active: boolean;
  minutes_posted: number;
  before_speed_kmh: number | null;
  during_speed_kmh: number | null;
  delta_speed_kmh: number | null;
  before_index: number | null;
  during_index: number | null;
  delta_index: number | null;
  typical_index: number | null;
  vs_typical: string | null;
  verdict: string;
  confidence: "good" | "fair" | "low";
  samples: { before: number; during: number };
  limitation: string;
}

export interface Deployment {
  deployment_id: string;
  corridor_ids: string[];
  primary_corridor_id: string;
  location_name: string;
  by: string;
  unit: string;
  purpose: string;
  started_at: string;
  ended_at: string | null;
  incident_id: string | null;
  note: string | null;
  effect: DeploymentEffect;
}

/** What the console watches, what it does not, and — now — the slow roads with
 *  no officer on them. The honest expression of "surface the roads police don't
 *  cover". */
export interface Coverage {
  summary: {
    corridors_instrumented: number;
    junctions_instrumented: number;
    known_gaps: number;
    note: string;
  };
  unwatched_slow: {
    count: number;
    acute: number;
    chronic: number;
    corridors: {
      corridor_id: string;
      name: string;
      condition: Condition;
      speed_kmh: number | null;
      band: Band;
      held_minutes: number | null;
    }[];
    note: string;
  };
  gaps: {
    name: string;
    kind: string;
    significance: string;
    evidence: string;
    grade: string;
    why_not_watched: string;
  }[];
}

export const getCoverage = () => get<Coverage>("/api/coverage");

export const getDeployments = (active?: boolean) =>
  get<{ count: number; deployments: Deployment[]; store: Record<string, unknown> }>(
    `/api/deployments${active === undefined ? "" : `?active=${active}`}`,
  );

/** Log an officer posted to a road and begin measuring the effect. Write-gated. */
export async function startDeployment(body: {
  corridor_ids?: string[];
  junction_id?: string;
  unit: string;
  purpose: string;
  note?: string;
  incident_id?: string;
  by?: string;
}): Promise<Deployment> {
  const token = getToken();
  const r = await fetch(`${API}/api/deployments`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  const payload = await r.json().catch(() => ({}));
  if (!r.ok) throw new ActionError(r.status, payload?.detail ?? `posting failed (${r.status})`);
  return payload as Deployment;
}

export async function endDeployment(deploymentId: string): Promise<Deployment> {
  const token = getToken();
  const r = await fetch(`${API}/api/deployments/${deploymentId}/end`, {
    method: "POST",
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  const payload = await r.json().catch(() => ({}));
  if (!r.ok) throw new ActionError(r.status, payload?.detail ?? `end failed (${r.status})`);
  return payload as Deployment;
}

/** A field officer raises an incident the system cannot see. Same write gate as
 *  any action — a report is a police record. */
export async function raiseFieldReport(body: {
  by: string;
  junction_id?: string;
  lat?: number;
  lon?: number;
  cause: string;
  note?: string;
  priority?: Priority;
}): Promise<Incident> {
  const token = getToken();
  const r = await fetch(`${API}/api/incidents`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  const payload = await r.json().catch(() => ({}));
  if (!r.ok) {
    throw new ActionError(r.status, payload?.detail ?? `report failed (${r.status})`);
  }
  return payload as Incident;
}

/** A copilot answer — the five-part contract that cannot omit its limitation,
 *  plus what it wants the board to focus on and how it was produced. */
export interface CopilotAnswer {
  observation: string;
  comparison: string;
  interpretation: string;
  limitation: string;
  next_step: string;
  focus_incident: string | null;
  focus_junction: string | null;
  tools_called: string[];
  /** The figures behind the prose — one entry per tool the copilot ran, for the
   *  interface to render as widgets rather than leave the answer as text only. */
  data: { tool: string; result: Record<string, unknown> }[];
  /** Real citations for the data used — computed from which tools ran, so the
   *  reference is a fact, not something the model wrote. */
  sources: string[];
  model: string;
  degraded: boolean;
}

/** Ask the copilot a question about the live board. A read — no token. */
export async function askCopilot(question: string): Promise<CopilotAnswer> {
  const r = await fetch(`${API}/api/copilot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  const payload = await r.json().catch(() => ({}));
  if (!r.ok) throw new ActionError(r.status, payload?.detail ?? `copilot failed (${r.status})`);
  return payload as CopilotAnswer;
}

export interface Recommendation {
  kind: "POST" | "DIVERT" | "ESCALATE" | "WATCH" | "STAND_DOWN";
  urgency: "NOW" | "THIS_SHIFT" | "ADVISORY";
  headline: string;
  detail: string;
  because: string[];
  cannot_know: string;
  junctions: string[];
  corridors: string[];
}

export const getAdvice = () =>
  get<{ at: string; recommendations: Recommendation[] }>("/api/advice");

export const getNetwork = () => get<NetworkPayload>("/api/network");
export const getRoster = () => get<{ officers: Officer[] }>("/api/roster");
export const getIncident = (id: string) => get<Incident>(`/api/incidents/${id}`);
export const getHandover = (hours = 8) =>
  get<HandoverPayload>(`/api/shift/handover?hours=${hours}`);
export const getCorridor = (id: string) => get<CorridorDetail>(`/api/corridors/${id}`);
export const getCorridorHistory = (id: string, days = 30) =>
  get<CorridorHistory>(`/api/corridors/${id}/history?days=${days}`);
export const getCityProfile = (dayType = "WEEKDAY") =>
  get<CityProfile>(`/api/city-profile?day_type=${dayType}`);

/** This corridor's OWN learned history — derived aggregates only, never raw
 *  readings. The per-corridor baseline the 2019 city study could not give. */
export interface CorridorHistory {
  corridor_id: string;
  name: string;
  live_index: number | null;
  live_band: Band;
  vs_baseline: {
    verdict: string;
    z_score?: number;
    confidence?: string;
    caveat?: string;
    when?: { weekday: string; hour: number };
    baseline?: { n: number; p50: number | null; p85: number | null; mean: number | null } | null;
  } | null;
  typical_today: {
    weekday: string;
    hours: { hour: number; p50: number | null; p85: number | null; n: number }[];
    worst_hours: { hour: number; p85: number | null }[];
    observations: number;
    caveat: string;
  } | null;
  trend: {
    direction: string;
    drift: number | null;
    days_observed: number;
    series: { date: string; mean: number | null; peak: number | null; hours_congested: number }[];
    caveat: string;
  } | null;
  forecast: {
    from_hour: number;
    trend_nudge: number;
    steps: { hour: number; weekday: string; expected: number | null; band?: (number | null)[]; n: number }[];
    caveat: string;
  } | null;
  timeline: {
    days: { date: string; n: number; mean: number | null; peak: number | null; hours_congested: number }[];
  } | null;
  source: string;
}

export interface CityProfile {
  day_type: string;
  hours: { hour: number; index: number; speed_kmh: number; sample_size: number; congested: boolean }[];
  source: string;
  limitation: string;
}

export interface CorridorDetail {
  corridor_id: string; name: string; from_name: string; to_name: string;
  band: Band; index: number | null; trend_per_10min: number | null;
  approximate_location: boolean;
  readings: { at: string; index: number; duration_minutes: number; typical_minutes: number; chokes: number }[];
  latest: Record<string, unknown> | null;
  note: string;
}

export interface HandoverSummary {
  incident_id: string; priority: Priority; state: IncidentState;
  title: string; location_name: string; owner: string | null;
  age_minutes: number; notes: Note[];
  escalation?: Escalation; next_actions?: string[];
}

export interface HandoverPayload {
  window_hours: number; from: string; to: string; raised: number;
  situation: {
    open: number; unowned: number; overdue: number;
    by_priority: Record<string, number>;
    raised_in_window: number; elevated_now: number; assessment: string;
  };
  watch: { name: string; band: Band; index: number | null }[];
  handing_over: { needs_an_owner: HandoverSummary[]; in_hand: HandoverSummary[] };
  this_shift: { closed: HandoverSummary[]; stood_down: HandoverSummary[]; lapsed: HandoverSummary[] };
  alerting_quality: { lapse_rate: number; note: string };
}

/** The board, refreshed when the server says a cycle completed.
 *  The stream carries the signal only; payloads are fetched, so a dropped
 *  connection leaves the officer with stale data rather than wrong data —
 *  and the header says which. */
export function useBoard() {
  const [board, setBoard] = useState<Board | null>(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fetchedAt, setFetchedAt] = useState<Date | null>(null);
  const busy = useRef(false);

  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      setBoard(await get<Board>("/api/board"));
      setFetchedAt(new Date());
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      busy.current = false;
    }
  }, []);

  useEffect(() => {
    refresh();
    const source = new EventSource(`${API}/api/stream`);
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.onmessage = (event) => {
      try {
        if (JSON.parse(event.data).type === "cycle") refresh();
      } catch {
        /* keep-alives are not JSON */
      }
    };
    return () => source.close();
  }, [refresh]);

  return { board, connected, error, fetchedAt, refresh };
}

// ── presentation vocabulary ────────────────────────────────────────────────
// Colour is never the only signal: every band carries a word and a shape so it
// survives a monochrome print and colour vision deficiency.

export const BAND: Record<Band, { label: string; fg: string; tint: string; mark: string }> = {
  SEVERE:   { label: "Severe",   fg: "var(--color-sev)",  tint: "var(--color-sev-tint)",  mark: "■" },
  HIGH:     { label: "High",     fg: "var(--color-high)", tint: "var(--color-high-tint)", mark: "▲" },
  ELEVATED: { label: "Elevated", fg: "var(--color-elev)", tint: "var(--color-elev-tint)", mark: "●" },
  NORMAL:   { label: "Normal",   fg: "var(--color-ok)",   tint: "var(--color-ok-tint)",   mark: "–" },
  UNKNOWN:  { label: "No data",  fg: "var(--color-none)", tint: "var(--color-none-tint)", mark: "?" },
};

/** Condition colours as RGB, for the map underlay (deck.gl cannot read CSS vars).
 *  Consistent with the incident markers already on the map. CLEAR/UNKNOWN get no
 *  underlay — the halo exists only to reveal slow roads, so a clear road stays
 *  the plain carriageway. */
export const CONDITION_RGB: Record<Condition, [number, number, number] | null> = {
  ACUTE: [179, 35, 24], // red — deploy now
  CHRONIC: [181, 71, 8], // amber/copper — structural
  WATCH: [193, 146, 42], // muted gold — early warning
  CLEAR: null,
  UNKNOWN: null,
};

/** The absolute condition, shown as the primary state now. ACUTE pops (a fresh
 *  jam to deploy to); CHRONIC is calmer amber (a standing problem — structural,
 *  not a dispatch); WATCH is early-warning; CLEAR is genuinely moving. This is
 *  what stops a 10 km/h crawl reading as green. */
export const CONDITION: Record<Condition, { label: string; note: string; fg: string; tint: string; mark: string }> = {
  ACUTE:    { label: "Acute",    note: "slow and worse than usual — deploy now",  fg: "var(--color-sev)",  tint: "var(--color-sev-tint)",  mark: "▲" },
  CHRONIC:  { label: "Chronic",  note: "always slow here — structural, not a dispatch", fg: "var(--color-high)", tint: "var(--color-high-tint)", mark: "▣" },
  WATCH:    { label: "Building",  note: "moving, but slower than usual — watch",   fg: "var(--color-elev)", tint: "var(--color-elev-tint)", mark: "●" },
  CLEAR:    { label: "Clear",    note: "moving, and normal",                       fg: "var(--color-ok)",   tint: "var(--color-ok-tint)",   mark: "–" },
  UNKNOWN:  { label: "No data",  note: "not observed yet",                         fg: "var(--color-none)", tint: "var(--color-none-tint)", mark: "?" },
};

export const PRIORITY: Record<Priority, { label: string; fg: string; tint: string }> = {
  P1: { label: "Act now",        fg: "var(--color-sev)",  tint: "var(--color-sev-tint)" },
  P2: { label: "This shift",     fg: "var(--color-high)", tint: "var(--color-high-tint)" },
  P3: { label: "Watch",          fg: "var(--color-elev)", tint: "var(--color-elev-tint)" },
  P4: { label: "Record only",    fg: "var(--color-none)", tint: "var(--color-none-tint)" },
};

export const STATE_LABEL: Record<IncidentState, string> = {
  DETECTED: "New", ACKNOWLEDGED: "Seen", ASSIGNED: "Assigned", ON_SCENE: "On scene",
  CLEARING: "Clearing", RESOLVED: "Resolved", CLOSED: "Closed",
  STOOD_DOWN: "No action needed", LAPSED: "Cleared on its own",
};

export const ACTION_LABEL: Record<string, string> = {
  ACKNOWLEDGED: "Acknowledge", ASSIGNED: "Assign", ON_SCENE: "Mark on scene",
  CLEARING: "Mark clearing", RESOLVED: "Mark resolved", CLOSED: "Close",
  STOOD_DOWN: "No action needed", LAPSED: "Cleared on its own",
};

export const ACTION_PATH: Record<string, string> = {
  ACKNOWLEDGED: "acknowledge", ASSIGNED: "assign", ON_SCENE: "on-scene",
  CLEARING: "clearing", RESOLVED: "resolve", CLOSED: "close", STOOD_DOWN: "stand-down",
};

export const hhmm = (iso: string | null | undefined) => (iso ? iso.slice(11, 16) : "—");

export function minutes(m: number): string {
  if (m < 60) return `${Math.round(m)} min`;
  const h = Math.floor(m / 60);
  const r = Math.round(m % 60);
  return r ? `${h} h ${r} min` : `${h} h`;
}
