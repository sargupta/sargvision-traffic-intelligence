"use client";

import { useEffect, useState } from "react";

export type Confidence = "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT";
export type Reliability = "HIGHLY_RELIABLE" | "MODERATELY_RELIABLE" | "UNPREDICTABLE";
export type Severity = "EXPECTED" | "MODERATE" | "HIGH" | "CRITICAL";
export type DayType = "WEEKDAY" | "WEEKEND" | "ALL";

export interface Zone {
  zone_id: string;
  zone_name: string;
  name_distance_m: number;
  landmark_kind: string;
  lat: number;
  lon: number;
  endpoint_observations: number;
}

export interface Movement {
  movement_id: string;
  movement_name: string;
  origin_zone: string;
  origin_zone_name: string;
  dest_zone: string;
  dest_zone_name: string;
  sample_size: number;
  median_seconds: number;
  p90_seconds: number;
  median_delay_seconds: number;
  median_delay_pct: number;
  median_tti: number;
  median_speed_kmh: number;
  median_distance_m: number;
  origin_lat: number;
  origin_lon: number;
  dest_lat: number;
  dest_lon: number;
  confidence: Confidence;
  expected_minutes: number;
}

export interface ReliabilityRow {
  movement_id: string;
  movement_name: string;
  origin_zone_name: string;
  dest_zone_name: string;
  sample_size: number;
  buffer_pct: number;
  reliability: Reliability;
  confidence: Confidence;
  median_minutes: number;
  p90_minutes: number;
  extra_minutes: number;
  median_speed_kmh: number;
  median_distance_m: number;
}

export interface Baseline {
  movement_id: string;
  movement_name: string;
  day_type: DayType;
  hour: number;
  sample_size: number;
  confidence: Confidence;
  expected_minutes: number;
  normal_low_minutes: number;
  normal_high_minutes: number;
  median_pace: number;
  median_tti: number;
  median_speed_kmh: number;
  median_delay_pct: number;
  median_distance_m: number;
}

export interface HourlyPattern {
  hour: number;
  sample_size: number;
  median_tti: number;
  median_speed_kmh: number;
  median_delay_pct: number;
  median_seconds: number;
  congested: boolean;
  day_type: DayType;
}

export interface DailyPattern {
  day_of_week: number;
  day_name: string;
  sample_size: number;
  median_tti: number;
  median_speed_kmh: number;
  median_delay_pct: number;
}

export interface PeakWindow {
  movement_id: string;
  movement_name: string;
  peak_hour: number;
  peak_tti: number;
  peak_minutes: number;
  quietest_hour: number;
  quietest_tti: number;
  quietest_minutes: number;
}

export interface Anomaly {
  observation_id: string;
  movement_id: string;
  movement_name: string;
  observed_at: string;
  hour: number;
  day_type: DayType;
  expected_minutes: number;
  observed_minutes: number;
  deviation_pct: number;
  severity: Severity;
  baseline_confidence: Confidence;
  distance_m: number;
}

export interface AnomalyRate {
  movement_id: string;
  movement_name: string;
  scored: number;
  anomalies: number;
  anomaly_rate_pct: number;
  p95_deviation_pct: number;
  worst_deviation_pct: number;
  confidence: Confidence;
}

export interface Bundle {
  meta: {
    built_at: string;
    mode: string;
    is_live: boolean;
    window: { start: string; end: string; days: number };
    canonical_sample: string;
    source: string;
    anomaly_limit: number;
    anomalies_total: number;
    config: Record<string, unknown>;
    quality_gate: Record<string, number | boolean>;
    row_counts: Record<string, number>;
    zone_search: {
      k: number;
      viable: boolean;
      worst_name_distance_m: number;
      min_zone_endpoints: number;
      inertia: number;
    }[];
  };
  zones: Zone[];
  movements: Movement[];
  reliability: ReliabilityRow[];
  baselines: Baseline[];
  patterns_hourly: HourlyPattern[];
  patterns_daily: DailyPattern[];
  patterns_weekly: Record<string, number>[];
  peak_windows: PeakWindow[];
  anomaly_rates: AnomalyRate[];
  anomalies: Anomaly[];
}

let cache: Promise<Bundle> | null = null;

function load(): Promise<Bundle> {
  if (!cache) {
    cache = fetch("/data/analytics.json").then((r) => {
      if (!r.ok) throw new Error(`analytics.json ${r.status}`);
      return r.json() as Promise<Bundle>;
    });
  }
  return cache;
}

export function useAnalytics() {
  const [data, setData] = useState<Bundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    load()
      .then((b) => live && setData(b))
      .catch((e) => live && setError(String(e)));
    return () => {
      live = false;
    };
  }, []);

  return { data, error, loading: !data && !error };
}

export const RELIABILITY_LABEL: Record<Reliability, string> = {
  HIGHLY_RELIABLE: "Highly reliable",
  MODERATELY_RELIABLE: "Moderately reliable",
  UNPREDICTABLE: "Unpredictable",
};

export const RELIABILITY_COLOUR: Record<Reliability, string> = {
  HIGHLY_RELIABLE: "var(--color-sage)",
  MODERATELY_RELIABLE: "var(--color-gold)",
  UNPREDICTABLE: "var(--color-signal)",
};

export const SEVERITY_COLOUR: Record<Severity, string> = {
  EXPECTED: "var(--color-paper-40)",
  MODERATE: "var(--color-gold)",
  HIGH: "var(--color-copper)",
  CRITICAL: "var(--color-signal)",
};

/** Confidence is never a colour — it is a sample count and a word.
 *  See docs/design/ui-ux.md §2. */
export const CONFIDENCE_BARS: Record<Confidence, number> = {
  HIGH: 4,
  MODERATE: 3,
  LOW: 2,
  INSUFFICIENT: 0,
};

export const clock = (h: number) => `${String(h).padStart(2, "0")}:00`;
export const n = (v: number, d = 0) =>
  v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
