import raw from "../../public/data/findings.json";

export type Band = "HIGH" | "MODERATE" | "LOW" | "INSUFFICIENT";

export interface HourPoint {
  hour: number;
  tti: number;
  speed: number;
  n: number;
}

export interface Corridor {
  id: string;
  buffer_pct: number;
  speed: number;
  tti: number;
  n: number;
  confidence: Band;
  origin: [number, number];
  dest: [number, number];
}

export interface CoverageCell {
  c: [number, number];
  n: number;
  b: Band;
}

export const findings = raw as unknown as {
  meta: {
    canonical_sample: string;
    n: number;
    window_start: string;
    window_end: string;
    days: number;
    trips: number;
    mode: string;
    is_live: boolean;
    source: string;
    bbox: [number, number, number, number];
    centre: [number, number];
    min_bin: number;
  };
  f1_ceiling: {
    observed_speed_kmh: number;
    freeflow_speed_kmh: number;
    reference_speed_kmh: number;
    congestion_gap_kmh: number;
    structural_gap_kmh: number;
    congestion_share_pct_low: number;
    congestion_share_pct_high: number;
    estimators: { method: string; observed: number; freeflow: number; share_pct: number }[];
    n: number;
  };
  f2_shape: {
    hours: HourPoint[];
    summary: {
      peak_hour: number;
      peak_tti: number;
      peak_speed: number;
      plateau_hours: number;
      plateau_start: number;
      plateau_end: number;
      n: number;
    };
    threshold_tti: number;
    morning_0900: HourPoint;
    evening_1900: HourPoint;
  };
  f3_weekend: {
    weekday: HourPoint[];
    weekend: HourPoint[];
    weekday_summary: { peak_hour: number; peak_tti: number; plateau_hours: number; n: number };
    weekend_summary: { peak_hour: number; peak_tti: number; plateau_hours: number; n: number };
    weekend_share_of_weekday_peak: number;
  };
  f4_reliability: {
    corridors: Corridor[];
    unit_count: number;
    min_sample: number;
    rho_buffer_speed: number;
    top_n: number;
    overlap: number;
    worst: number;
    best: number;
    median: number;
    spread_multiple: number;
  };
  coverage: {
    cells: CoverageCell[];
    summary: Record<Band, number>;
    cell_count: number;
  };
};

/** Indian digit grouping — 1,01,418 rather than 101,418 is *not* what we want
 *  here: the canonical sample string is fixed in docs/data-provenance.md and
 *  uses international grouping. This formats everything else to match it. */
export const num = (v: number, digits = 0) =>
  v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const clock = (h: number) => `${String(h).padStart(2, "0")}:00`;
