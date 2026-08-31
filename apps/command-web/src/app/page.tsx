"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Chrome } from "@/components/Chrome";
import { FlowMap } from "@/components/FlowMap";
import { NetworkPlan } from "@/components/NetworkPlan";
import { CorridorTable } from "@/components/CorridorTable";
import { Advice } from "@/components/Advice";
import { Empty } from "@/components/Bits";
import { IncidentCard } from "@/components/IncidentCard";
import {
  getAdvice, getNetwork, getRoster, useBoard,
  type Incident, type NetworkPayload, type Officer, type Recommendation,
} from "@/lib/api";

const OFFICER = "DO-1";

export default function Board() {
  const { board, connected, error, refresh } = useBoard();
  const [animate, setAnimate] = useState(true);
  // "plan" is not a downgrade. Without a basemap the only lines on screen are
  // roads we actually measure, which is the better rendering on a projector,
  // in a briefing pack, and on any machine where the map will not paint.
  // Plan, not Map, is the default. It needs no API key, it prints, it costs no
  // GPU or animation loop, and the only lines on it are roads we actually
  // measure. A control-room screen should not open on something that can be a
  // vendor error dialog when a key expires. The basemap is the enhancement.
  const [view, setView] = useState<"map" | "plan">("plan");
  const [mapUsable, setMapUsable] = useState(true);
  const [network, setNetwork] = useState<NetworkPayload | null>(null);
  const [roster, setRoster] = useState<Officer[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, Incident>>({});
  const [advice, setAdvice] = useState<Recommendation[]>([]);

  useEffect(() => {
    getNetwork().then(setNetwork).catch(() => setNetwork(null));
    getRoster().then((r) => setRoster(r.officers)).catch(() => setRoster([]));
  }, []);

  // Advice is recomputed whenever the board moves, so a recommendation never
  // outlives the condition that produced it.
  useEffect(() => {
    if (!board) return;
    getAdvice().then((a) => setAdvice(a.recommendations)).catch(() => setAdvice([]));
  }, [board?.at]);

  // An action returns the updated incident. Showing it immediately, rather than
  // waiting up to three minutes for the next poll, is the difference between a
  // tool that feels responsive and one that feels broken.
  const onChanged = useCallback((updated: Incident) => {
    setOverrides((o) => ({ ...o, [updated.incident_id]: updated }));
    refresh();
  }, [refresh]);

  const incidents = useMemo(() => {
    if (!board) return [];
    return board.incidents
      .map((i) => overrides[i.incident_id] ?? i)
      .filter((i) => i.is_open);
  }, [board, overrides]);

  const needsAction = incidents.filter((i) => i.needs_attention);
  const inHand = incidents.filter((i) => !i.needs_attention);
  const bands = board?.bands ?? {};

  // An empty queue must explain itself. The previous text asserted that every
  // corridor was within its usual travel time, which the headline directly
  // contradicted whenever anything was elevated — a police screen claiming the
  // city is fine in a state it reaches most afternoons.
  const emptyState = useMemo(() => {
    const above = (bands.SEVERE ?? 0) + (bands.HIGH ?? 0) + (bands.ELEVATED ?? 0);
    const s = board?.suppressed;
    if (above === 0) {
      return {
        title: "Every corridor is within its usual travel time.",
        detail: "Nothing is above what this network normally takes at this hour. This is a result, not an empty screen.",
      };
    }
    const reasons: string[] = [];
    if (s?.holding) reasons.push(`${s.holding} still being confirmed`);
    if (s?.below_threshold) reasons.push(`${s.below_threshold} too small to act on`);
    if (s?.quiet_hours) reasons.push(`${s.quiet_hours} held until the morning shift`);
    if (s?.budget) reasons.push(`${s.budget} beyond the alert budget`);
    return {
      title: `${above} corridor${above === 1 ? " is" : "s are"} above typical, none needing a decision yet.`,
      detail: reasons.length
        ? `Located choke points: ${reasons.join(", ")}. A condition becomes an incident once it has held long enough to be worth sending someone to.`
        : "No located choke point has held long enough to be worth sending someone to. The corridor table below shows every reading.",
    };
  }, [bands, board?.suppressed]);

  return (
    <>
      <Chrome at={board?.at} connected={connected} cycle={board?.cycle} officer="Duty Officer" />

      <main id="main" className="mx-auto w-full max-w-[130rem] px-4 py-4 lg:px-6">
        {error && (
          <p className="mb-4 rounded-md border border-line bg-sev-tint px-4 py-2.5 text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>
            {error} — the API may not be running. Set NEXT_PUBLIC_API_URL if it is not on localhost:8099.
          </p>
        )}

        {/* The four questions, answered before any click. */}
        <section className="card mb-4 flex flex-wrap items-center gap-x-8 gap-y-3 px-5 py-4">
          <div className="min-w-[18rem] flex-1">
            <p className="label">Right now across Siliguri</p>
            <p className="mt-1 text-[length:var(--text-xl)] font-semibold leading-snug">
              {board?.headline ?? "Connecting…"}
            </p>
          </div>

          <dl className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {(
              [
                ["Severe", bands.SEVERE ?? 0, "var(--color-sev)"],
                ["High", bands.HIGH ?? 0, "var(--color-high)"],
                ["Elevated", bands.ELEVATED ?? 0, "var(--color-elev)"],
                ["Normal", bands.NORMAL ?? 0, "var(--color-ok)"],
              ] as const
            ).map(([label, n, colour]) => (
              <div key={label} className="text-center">
                <dd className="tnum text-[length:var(--text-2xl)] font-semibold leading-none" style={{ color: n ? colour : "var(--color-ink-3)" }}>
                  {n}
                </dd>
                <dt className="label mt-1">{label}</dt>
              </div>
            ))}
            <div className="border-l border-line pl-6 text-center">
              <dd className="tnum text-[length:var(--text-2xl)] font-semibold leading-none">
                {needsAction.length}
                <span className="text-[length:var(--text-md)] font-normal text-ink-3">/{board?.alert_budget ?? "—"}</span>
              </dd>
              <dt className="label mt-1">Awaiting an officer</dt>
            </div>
          </dl>
        </section>

        {/* Map first and large: the officer is looking at geography, and the
            incident list is the queue beside it. A narrow map column made the
            network unreadable and put the queue where the map belongs. */}
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(24rem,0.65fr)]">
          <div className="order-1 flex flex-col gap-4">
            <div className="relative h-[24rem] xl:h-[calc(100dvh-13rem)] xl:min-h-[30rem]">
              {view === "map" ? (
                <FlowMap
                  board={board}
                  network={network}
                  selected={selected}
                  onSelectIncident={setSelected}
                  animate={animate}
                  onUnavailable={() => {
                    setMapUsable(false);
                    setView("plan");
                  }}
                />
              ) : (
                <NetworkPlan
                  board={board}
                  network={network}
                  selected={selected}
                  onSelectIncident={setSelected}
                  className="h-full w-full"
                />
              )}
              <div className="absolute right-3 top-3 flex items-center gap-2 rounded-md border border-line bg-surface/95 px-2.5 py-1.5 shadow-[var(--shadow-card)] no-print">
                <div role="group" aria-label="View" className="flex items-center gap-0.5">
                  {(["plan", "map"] as const).map((v) => (
                    <button
                      key={v}
                      type="button"
                      disabled={v === "map" && !mapUsable}
                      onClick={() => setView(v)}
                      aria-pressed={view === v}
                      title={v === "map" && !mapUsable ? "The basemap is unavailable" : undefined}
                      className={`rounded px-2 py-0.5 text-[length:var(--text-2xs)] font-medium transition-colors ${
                        view === v ? "bg-navy text-white" : "text-ink-2 hover:bg-sunken"
                      }`}
                    >
                      {v === "map" ? "Basemap" : "Network"}
                    </button>
                  ))}
                </div>
                {view === "map" && (
                <label className="flex cursor-pointer items-center gap-2 border-l border-line pl-2 text-[length:var(--text-2xs)] text-ink-2">
                  <input
                    type="checkbox"
                    checked={animate}
                    onChange={(e) => setAnimate(e.target.checked)}
                    className="h-3.5 w-3.5 accent-[var(--color-navy)]"
                  />
                  Show flow
                </label>
                )}
                <span className="border-l border-line pl-2 tnum text-[length:var(--text-2xs)] text-ink-3">
                  {board?.corridors.reduce((n, c) => n + c.runs.length, 0) ?? 0} stretches measured
                </span>
                {!mapUsable && (
                  <span className="border-l border-line pl-2 text-[length:var(--text-2xs)]" style={{ color: "var(--color-high)" }}>
                    basemap unavailable
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="order-2 flex max-h-none flex-col gap-4 xl:max-h-[calc(100dvh-13rem)] xl:overflow-y-auto xl:pr-1">
            <Advice items={advice} />

            <section>
              <h2 className="mb-2.5 flex items-baseline gap-2 text-[length:var(--text-md)] font-semibold">
                Needs an officer
                <span className="tnum text-[length:var(--text-sm)] font-normal text-ink-3">
                  {needsAction.length}
                </span>
              </h2>
              {needsAction.length === 0 ? (
                <Empty title={emptyState.title} detail={emptyState.detail} />
              ) : (
                <div className="flex flex-col gap-3">
                  {needsAction.map((i) => (
                    <IncidentCard
                      key={i.incident_id}
                      incident={i}
                      roster={roster}
                      officer={OFFICER}
                      onChanged={onChanged}
                      selected={selected === i.incident_id}
                      onSelect={() => setSelected(i.incident_id)}
                    />
                  ))}
                </div>
              )}
            </section>

            {inHand.length > 0 && (
              <section>
                <h2 className="mb-2.5 flex items-baseline gap-2 text-[length:var(--text-md)] font-semibold">
                  With an officer
                  <span className="tnum text-[length:var(--text-sm)] font-normal text-ink-3">{inHand.length}</span>
                </h2>
                <div className="flex flex-col gap-3">
                  {inHand.map((i) => (
                    <IncidentCard
                      key={i.incident_id}
                      incident={i}
                      roster={roster}
                      officer={OFFICER}
                      onChanged={onChanged}
                      selected={selected === i.incident_id}
                      onSelect={() => setSelected(i.incident_id)}
                      compact
                    />
                  ))}
                </div>
              </section>
            )}

          </div>
        </div>

        {board && (
          <div className="mt-4">
            <CorridorTable corridors={board.corridors} />
          </div>
        )}
      </main>
    </>
  );
}
