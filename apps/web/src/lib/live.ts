"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export const API =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8099";

export type Status = "NORMAL" | "MODERATE" | "HIGH" | "CRITICAL" | "UNKNOWN";
export type Signal = "DETERIORATION" | "PERSISTENCE" | "VARIABILITY" | "CLUSTER";

export interface MovementLive {
  movement_id: string;
  name: string;
  origin_zone: string;
  dest_zone: string;
  status: Status;
  deviation_pct: number | null;
  current_minutes: number | null;
  expected_minutes: number | null;
  persistence_minutes: number;
  readings: number;
}

export interface CityStateResponse {
  mode: string;
  is_live: boolean;
  clock: string | null;
  updated_at: string | null;
  headline: string;
  counts: Record<Status, number>;
  movements: MovementLive[];
  provenance: Record<string, unknown>;
}

export interface View {
  layout: string;
  focus_movements?: string[];
  focus_zones?: string[];
  encode?: string;
}

export interface Finding {
  id: string;
  signal: Signal;
  severity: Status;
  title: string;
  claim: string;
  evidence: Record<string, unknown>;
  movements: string[];
  zones: string[];
  detected_at: string;
  persistence_minutes: number;
  confidence: "HIGH" | "MODERATE" | "LOW";
  limitation: string;
  priority: number;
  view: View;
  first_seen: string;
  last_seen: string;
  state: "ACTIVE" | "RESOLVED";
  components: string[];
}

export interface CopilotAnswer {
  observation: string;
  comparison: string;
  interpretation: string;
  limitation: string;
  next_step: string;
  tools_called: string[];
  tool_trace: { tool: string; args: Record<string, unknown> }[];
  view: View;
  model: string;
  degraded: boolean;
  mode: string;
  is_live: boolean;
}

async function get<T>(path: string): Promise<T> {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json() as Promise<T>;
}

/** City state and feed, refreshed whenever the server says a tick happened.
 *  The stream carries the signal; the payloads are fetched, so a dropped
 *  connection degrades to stale data rather than to wrong data. */
export function useLive() {
  const [state, setState] = useState<CityStateResponse | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const busy = useRef(false);

  const refresh = useCallback(async () => {
    if (busy.current) return;
    busy.current = true;
    try {
      const [s, f] = await Promise.all([
        get<CityStateResponse>("/api/state"),
        get<{ findings: Finding[] }>("/api/feed"),
      ]);
      setState(s);
      setFindings(f.findings);
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
        const msg = JSON.parse(event.data);
        if (msg.type === "tick" || msg.type === "replay_wrapped") refresh();
      } catch {
        /* keep-alive comments are not JSON */
      }
    };
    return () => source.close();
  }, [refresh]);

  return { state, findings, connected, error, refresh };
}

export async function askCopilot(question: string): Promise<CopilotAnswer> {
  const r = await fetch(`${API}/api/copilot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!r.ok) throw new Error(`copilot → ${r.status}`);
  return r.json();
}

export async function movementHistory(id: string) {
  return get<{
    movement_id: string;
    name: string;
    status: Status;
    readings: { at: string; minutes: number; deviation_pct: number | null; status: Status }[];
  }>(`/api/movements/${id}/history`);
}

export async function movementContext(id: string, dayType = "WEEKDAY") {
  return get<{
    movement_id: string;
    hours: {
      hour: number;
      expected_minutes: number;
      normal_low_minutes: number;
      normal_high_minutes: number;
      sample_size: number;
      confidence: string;
    }[];
    reliability: { buffer_pct: number; reliability: string; sample_size: number } | null;
  }>(`/api/context/${id}?day_type=${dayType}`);
}

export const STATUS_COLOUR: Record<Status, string> = {
  CRITICAL: "var(--color-signal)",
  HIGH: "var(--color-copper)",
  MODERATE: "var(--color-gold)",
  NORMAL: "var(--color-sage)",
  UNKNOWN: "var(--color-rule-lit)",
};

export const STATUS_LABEL: Record<Status, string> = {
  CRITICAL: "Critical",
  HIGH: "High",
  MODERATE: "Moderate",
  NORMAL: "Normal",
  UNKNOWN: "No baseline",
};

export const SIGNAL_LABEL: Record<Signal, string> = {
  DETERIORATION: "Deteriorating",
  PERSISTENCE: "Sustained",
  VARIABILITY: "Unstable",
  CLUSTER: "Cluster",
};

export const hhmm = (iso: string | null) =>
  iso ? iso.slice(11, 16) : "—";
