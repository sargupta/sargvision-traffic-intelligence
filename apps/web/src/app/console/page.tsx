"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { Copilot } from "@/components/console/Copilot";
import { Feed } from "@/components/console/Feed";
import { LiveMap } from "@/components/console/LiveMap";
import { MovementDetail } from "@/components/console/MovementDetail";
import { hhmm, useLive, type Finding, type View } from "@/lib/live";

export default function Console() {
  const { state, findings, connected, error } = useLive();
  const [view, setView] = useState<View | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [activeFinding, setActiveFinding] = useState<string | null>(null);

  const investigate = useCallback((f: Finding) => {
    setView(f.view);
    setActiveFinding(f.id);
    setSelected(f.movements[0] ?? null);
  }, []);

  const onSelect = useCallback((id: string) => {
    setSelected(id);
    setActiveFinding(null);
  }, []);

  const selectedMovement = useMemo(
    () => state?.movements.find((m) => m.movement_id === selected) ?? null,
    [state, selected],
  );

  const counts = state?.counts;
  const live = state?.is_live ?? false;

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      {/* Mode is the first thing on screen and never scrolls away. This system
          is designed to run on replayed 2019 data, and a viewer who cannot tell
          replay from live would be misled about the city. */}
      <div
        className={`flex flex-wrap items-center gap-x-4 gap-y-1 border-b px-5 py-2 ${
          live ? "border-sage/40 bg-abyss" : "border-copper/40 bg-abyss"
        }`}
      >
        <span className="flex items-center gap-2">
          <span
            aria-hidden
            className={`h-1.5 w-1.5 rounded-full ${connected ? "animate-pulse" : ""}`}
            style={{ backgroundColor: live ? "var(--color-sage)" : "var(--color-copper)" }}
          />
          <span
            className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.16em]"
            style={{ color: live ? "var(--color-sage)" : "var(--color-copper-lit)" }}
          >
            {live ? "Live" : "Historical replay"}
          </span>
        </span>
        <span className="font-mono text-[length:var(--text-micro)] tnum text-paper-40">
          {state?.clock ? `${state.clock.slice(0, 10)} ${hhmm(state.clock)}` : "starting…"}
        </span>
        {!live && (
          <span className="font-mono text-[length:var(--text-micro)] text-paper-40">
            replaying 2019 observations · nothing here is current
          </span>
        )}
        <span className="ml-auto font-mono text-[length:var(--text-micro)] text-paper-40">
          {connected ? "stream connected" : "stream offline"}
        </span>
      </div>

      <header className="flex flex-wrap items-center justify-between gap-x-8 gap-y-3 border-b border-rule px-5 py-3">
        <div className="flex items-baseline gap-3">
          <h1 className="font-display text-[length:var(--text-lead)] font-light text-paper">
            SARGVISION Traffic Intelligence
          </h1>
          <span className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
            Siliguri
          </span>
        </div>

        <p className="order-last w-full text-[length:var(--text-caption)] text-paper-70 md:order-none md:w-auto">
          {state?.headline ?? "Connecting to the intelligence loop…"}
        </p>

        <div className="flex items-center gap-5">
          {counts &&
            (
              [
                ["CRITICAL", "var(--color-signal)"],
                ["HIGH", "var(--color-copper)"],
                ["MODERATE", "var(--color-gold)"],
                ["NORMAL", "var(--color-sage)"],
              ] as const
            ).map(([k, colour]) => (
              <span key={k} className="flex items-center gap-1.5">
                <span aria-hidden className="h-2 w-2 rounded-full" style={{ backgroundColor: colour }} />
                <span className="font-mono text-[length:var(--text-micro)] tnum text-paper-70">
                  {counts[k as keyof typeof counts] ?? 0}
                </span>
              </span>
            ))}
          <Link
            href="/"
            className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40 transition-colors hover:text-copper-lit"
          >
            How Siliguri moves →
          </Link>
        </div>
      </header>

      {error && (
        <div className="border-b border-signal/40 bg-abyss px-5 py-2">
          <p className="font-mono text-[length:var(--text-micro)] text-signal">
            {error} — is the API running? Set NEXT_PUBLIC_API_URL if it is not on localhost:8099.
          </p>
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_26rem]">
        <div className="flex min-h-0 flex-col">
          <div className="min-h-[18rem] flex-1">
            <LiveMap
              movements={state?.movements ?? []}
              view={view}
              onSelect={onSelect}
              selected={selected}
            />
          </div>

          {selectedMovement && (
            <div className="max-h-[46%] shrink-0 overflow-y-auto border-t border-rule bg-ink-700">
              <MovementDetail movement={selectedMovement} />
            </div>
          )}
        </div>

        <aside className="flex min-h-0 flex-col border-t border-rule lg:border-l lg:border-t-0">
          <div className="flex min-h-0 flex-1 flex-col">
            <div className="flex items-center justify-between border-b border-rule px-5 py-3">
              <h2 className="eyebrow">Intelligence feed</h2>
              <span className="font-mono text-[length:var(--text-micro)] tnum text-paper-40">
                {findings.length} active
              </span>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">
              <Feed findings={findings} onInvestigate={investigate} activeId={activeFinding} />
            </div>
          </div>

          <div className="h-[52%] min-h-0 shrink-0 border-t border-rule">
            <Copilot onView={setView} />
          </div>
        </aside>
      </div>
    </div>
  );
}
