"use client";

import { useId } from "react";
import type { HourPoint } from "@/lib/data";
import { clock } from "@/lib/data";

const W = 1000;
const H = 430;
const M = { top: 30, right: 26, bottom: 52, left: 54 };
const PW = W - M.left - M.right;
const PH = H - M.top - M.bottom;

const LO = 0.9;
const HI = 1.3;

export const xAt = (hour: number) => M.left + (hour / 23) * PW;
export const yAt = (tti: number) => M.top + PH - ((tti - LO) / (HI - LO)) * PH;

export interface Series {
  points: HourPoint[];
  colour: string;
  label: string;
  fill?: boolean;
  dashed?: boolean;
  /** Hour to anchor the on-line name at, and its vertical nudge. Only drawn
   *  when a chart carries more than one series — a lone line needs no name. */
  labelAt?: number;
  labelDy?: number;
}

export interface Annotation {
  hour: number;
  tti: number;
  title: string;
  detail: string;
  /** Which side of the point the label sits on, so callouts never collide. */
  side?: "left" | "right";
  dy?: number;
}

const path = (pts: HourPoint[]) =>
  pts.map((p, i) => `${i === 0 ? "M" : "L"}${xAt(p.hour).toFixed(1)},${yAt(p.tti).toFixed(1)}`).join(" ");

export function TtiChart({
  series,
  annotations = [],
  band,
  bandLabel,
  caption,
  ariaLabel,
}: {
  series: Series[];
  annotations?: Annotation[];
  band?: [number, number];
  bandLabel?: string;
  caption: string;
  ariaLabel: string;
}) {
  const uid = useId().replace(/:/g, "");

  return (
    <figure className="mt-14">
      <div className="-mx-6 overflow-x-auto px-6 sm:mx-0 sm:px-0">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-auto w-full min-w-[640px]"
          role="img"
          aria-label={ariaLabel}
        >
          <defs>
            {series
              .filter((s) => s.fill)
              .map((s, i) => (
                <linearGradient key={i} id={`${uid}-f${i}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={s.colour} stopOpacity="0.22" />
                  <stop offset="100%" stopColor={s.colour} stopOpacity="0.01" />
                </linearGradient>
              ))}
          </defs>

          {/* Congested window, shaded before anything is drawn over it. */}
          {band && (
            <g>
              <rect
                x={xAt(band[0])}
                y={M.top}
                width={xAt(band[1]) - xAt(band[0])}
                height={PH}
                fill="var(--color-copper)"
                opacity="0.055"
              />
              <line x1={xAt(band[0])} y1={M.top} x2={xAt(band[0])} y2={M.top + PH}
                stroke="var(--color-copper)" strokeOpacity="0.4" strokeDasharray="2 4" />
              <line x1={xAt(band[1])} y1={M.top} x2={xAt(band[1])} y2={M.top + PH}
                stroke="var(--color-copper)" strokeOpacity="0.4" strokeDasharray="2 4" />
              {bandLabel && (
                <text
                  x={(xAt(band[0]) + xAt(band[1])) / 2}
                  y={M.top - 11}
                  textAnchor="middle"
                  className="fill-copper-lit font-mono"
                  style={{ fontSize: 12, letterSpacing: "0.14em", textTransform: "uppercase" }}
                >
                  {bandLabel}
                </text>
              )}
            </g>
          )}

          {/* Horizontal grid. The 1.0 line is free-flow and is drawn differently. */}
          {[0.9, 1.0, 1.1, 1.2, 1.3].map((t) => {
            const free = t === 1.0;
            return (
              <g key={t}>
                <line
                  x1={M.left}
                  x2={M.left + PW}
                  y1={yAt(t)}
                  y2={yAt(t)}
                  stroke={free ? "var(--color-paper-40)" : "var(--color-rule)"}
                  strokeWidth={free ? 1 : 1}
                  strokeDasharray={free ? "4 4" : undefined}
                  opacity={free ? 0.7 : 1}
                />
                <text
                  x={M.left - 12}
                  y={yAt(t) + 4}
                  textAnchor="end"
                  className={free ? "fill-paper-40" : "fill-paper-40"}
                  style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}
                >
                  {t.toFixed(1)}
                </text>
              </g>
            );
          })}
          <text
            x={M.left + PW}
            y={yAt(1.0) - 10}
            textAnchor="end"
            className="fill-paper-40 font-mono"
            style={{ fontSize: 11.5, letterSpacing: "0.1em" }}
          >
            FREE-FLOW
          </text>

          {/* Hours. */}
          {[0, 3, 6, 9, 12, 15, 18, 21, 23].map((h) => (
            <text
              key={h}
              x={xAt(h)}
              y={M.top + PH + 26}
              textAnchor={h === 0 ? "start" : h === 23 ? "end" : "middle"}
              className="fill-paper-40"
              style={{ fontSize: 12, fontVariantNumeric: "tabular-nums" }}
            >
              {clock(h)}
            </text>
          ))}

          {series.map((s, i) => (
            <g key={s.label}>
              {s.fill && (
                <path
                  d={`${path(s.points)} L${xAt(23)},${M.top + PH} L${xAt(0)},${M.top + PH} Z`}
                  fill={`url(#${uid}-f${i})`}
                />
              )}
              <path
                d={path(s.points)}
                fill="none"
                stroke={s.colour}
                strokeWidth={2}
                strokeLinejoin="round"
                strokeLinecap="round"
                strokeDasharray={s.dashed ? "6 5" : undefined}
              />
            </g>
          ))}

          {/* Series are named on the line itself — no legend to decode. A single
              series needs no name, and labelling it only risks clipping. */}
          {series.length > 1 &&
            series.map((s) => {
              const anchor =
                s.points.find((p) => p.hour === (s.labelAt ?? 15)) ?? s.points[s.points.length - 1];
              return (
                <text
                  key={`lbl-${s.label}`}
                  x={xAt(anchor.hour)}
                  y={yAt(anchor.tti) + (s.labelDy ?? -14)}
                  textAnchor="middle"
                  className="font-mono"
                  fill={s.colour}
                  style={{ fontSize: 12.5, letterSpacing: "0.1em" }}
                >
                  {s.label}
                </text>
              );
            })}

          {annotations.map((a) => {
            const right = a.side !== "left";
            const lx = xAt(a.hour) + (right ? 14 : -14);
            const ly = yAt(a.tti) + (a.dy ?? -34);
            return (
              <g key={a.title}>
                <circle cx={xAt(a.hour)} cy={yAt(a.tti)} r="4" fill="var(--color-ink)" stroke="var(--color-gold)" strokeWidth="1.75" />
                <line
                  x1={xAt(a.hour)}
                  y1={yAt(a.tti)}
                  x2={lx}
                  y2={ly + 4}
                  stroke="var(--color-gold)"
                  strokeOpacity="0.45"
                  strokeWidth="1"
                />
                <text x={lx} y={ly} textAnchor={right ? "start" : "end"} className="fill-paper" style={{ fontSize: 14 }}>
                  {a.title}
                </text>
                <text x={lx} y={ly + 17} textAnchor={right ? "start" : "end"} className="fill-paper-40" style={{ fontSize: 12 }}>
                  {a.detail}
                </text>
              </g>
            );
          })}

          <text
            x={M.left - 12}
            y={M.top - 12}
            textAnchor="end"
            className="fill-paper-40 font-mono"
            style={{ fontSize: 11 }}
          >
            TTI
          </text>
        </svg>
      </div>
      <figcaption className="mt-5 measure text-[length:var(--text-caption)] leading-relaxed text-paper-40">
        {caption}
      </figcaption>
    </figure>
  );
}
