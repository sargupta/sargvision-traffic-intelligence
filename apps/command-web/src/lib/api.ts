"use client";

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

export interface CorridorRow {
  corridor_id: string;
  name: string;
  band: Band;
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
  next_actions: string[];
}

export interface Board {
  at: string;
  cycle: number;
  is_live: boolean;
  bands: Partial<Record<Band, number>>;
  headline: string;
  alert_budget: number;
  over_budget: boolean;
  suppressed: { holding: number; below_threshold: number; quiet_hours: number; budget: number };
  candidates_holding: number;
  unowned: number;
  incidents: Incident[];
  corridors: CorridorRow[];
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
  role: string; unit: string; on_duty: boolean;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json() as Promise<T>;
}

export async function act(
  incidentId: string,
  action: string,
  body: { by: string; to?: string; unit?: string; text?: string; kind?: string },
): Promise<Incident> {
  const r = await fetch(`${API}/api/incidents/${incidentId}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await r.json().catch(() => ({}));
  if (!r.ok) {
    // The API refuses illegal transitions with the reason and the allowed set.
    // Surfacing that verbatim is more useful than "something went wrong".
    throw new Error(payload?.detail ?? `${action} failed (${r.status})`);
  }
  return payload as Incident;
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
export const getCityProfile = (dayType = "WEEKDAY") =>
  get<CityProfile>(`/api/city-profile?day_type=${dayType}`);

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
}

export interface HandoverPayload {
  window_hours: number; from: string; to: string; raised: number;
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
