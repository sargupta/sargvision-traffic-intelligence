"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { hhmm } from "@/lib/api";
import { clearToken, getToken, onTokenChange, setToken } from "@/lib/auth";

const NAV = [
  { href: "/", label: "Board" },
  { href: "/network", label: "Network" },
  { href: "/handover", label: "Handover" },
  { href: "/field", label: "Field" },
];

/** Chrome carries three things an officer must never have to hunt for:
 *  whether the data is live, how old it is, and who they are signed in as. */
export function Chrome({
  at,
  connected,
  cycle,
  officer,
  pollSeconds,
}: {
  at?: string;
  connected: boolean;
  cycle?: number;
  officer: string;
  pollSeconds?: number;
}) {
  const path = usePathname();

  // The dot used to track the event stream alone. That stream stays open while
  // /api/board is failing, so the header could read LIVE over figures that had
  // stopped advancing. Age is measured from the reading itself, and the
  // threshold comes from the collector's own cadence.
  const [nowMs, setNowMs] = useState<number | null>(null);
  useEffect(() => {
    const tick = () => setNowMs(Date.now());
    tick();
    const id = setInterval(tick, 10_000);
    return () => clearInterval(id);
  }, []);

  const ageSeconds =
    at && nowMs !== null ? Math.max(0, (nowMs - new Date(at).getTime()) / 1000) : null;
  const staleAfter = (pollSeconds ?? 180) * 1.5;
  const stale = ageSeconds !== null && ageSeconds > staleAfter;
  const state = !connected ? "OFFLINE" : stale ? "STALE" : "LIVE";

  const ageLabel =
    ageSeconds === null
      ? null
      : ageSeconds < 90
        ? `${Math.round(ageSeconds)}s ago`
        : `${Math.round(ageSeconds / 60)} min ago`;

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-navy text-white no-print">
      <div className="mx-auto flex w-full max-w-[130rem] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 lg:px-6">
        <Link href="/" className="flex items-baseline gap-2.5">
          <span className="text-[length:var(--text-md)] font-semibold tracking-tight">
            Siliguri Traffic Command
          </span>
          <span className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] text-white/55">
            SARGVISION
          </span>
        </Link>

        <nav aria-label="Sections" className="flex items-center gap-0.5">
          {NAV.map((n) => {
            const active = n.href === "/" ? path === "/" : path.startsWith(n.href);
            return (
              <Link
                key={n.href}
                href={n.href}
                aria-current={active ? "page" : undefined}
                className={`rounded px-2.5 py-1 text-[length:var(--text-sm)] transition-colors ${
                  active ? "bg-white/15 text-white" : "text-white/70 hover:bg-white/10 hover:text-white"
                }`}
              >
                {n.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-5">
          <span
            className="flex items-center gap-2"
            title={
              state === "OFFLINE"
                ? "Not receiving updates — these figures are the last ones that arrived"
                : state === "STALE"
                  ? `The last reading is older than ${Math.round(staleAfter / 60)} minutes`
                  : "Receiving updates"
            }
          >
            <span
              aria-hidden
              className={`h-2 w-2 rounded-full ${
                state === "LIVE" ? "bg-emerald-400" : state === "STALE" ? "bg-amber-400" : "bg-red-400"
              }`}
            />
            <span className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] text-white/80">
              {state === "LIVE" ? "Live" : state === "STALE" ? "Stale" : "Not updating"}
            </span>
          </span>

          {/* The age never disappears, in any of the three states. */}
          <span className="tnum text-[length:var(--text-sm)] text-white/75">
            {at ? hhmm(at) : "—"}
            {ageLabel && (
              <span className={`ml-2 ${state === "LIVE" ? "text-white/45" : "text-amber-300"}`}>
                {ageLabel}
              </span>
            )}
            {cycle !== undefined && <span className="ml-2 text-white/45">cycle {cycle}</span>}
          </span>

          <RecordingLock />

          <span className="hidden text-[length:var(--text-sm)] text-white/75 sm:inline">{officer}</span>
        </div>
      </div>
    </header>
  );
}

/** Whether this console may record, and how to change that.
 *
 *  It sits in the bar rather than behind a menu because an officer must never
 *  discover that recording was locked by having an action fail at the moment
 *  they needed it. Locked is a state of the room, so it belongs next to the
 *  live indicator.
 */
function RecordingLock() {
  const [token, setTokenState] = useState("");
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const box = useRef<HTMLSpanElement | null>(null);
  const field = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const read = () => setTokenState(getToken());
    read();
    return onTokenChange(read);
  }, []);

  // A panel sitting over the board has to be dismissible without hunting for
  // the button that opened it, and the caret should already be in the field.
  useEffect(() => {
    if (!open) return;
    field.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onDown = (e: PointerEvent) => {
      if (!box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onDown);
    };
  }, [open]);

  const unlocked = token.length > 0;

  return (
    <span ref={box} className="relative flex items-center no-print">
      <button
        type="button"
        onClick={() => {
          setDraft("");
          setOpen((o) => !o);
        }}
        aria-expanded={open}
        title={
          unlocked
            ? "This console can record actions. Click to lock or replace the token."
            : "This console cannot record actions until it is unlocked."
        }
        className={`rounded px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] transition-colors ${
          unlocked
            ? "text-white/60 hover:bg-white/10 hover:text-white/85"
            : "bg-amber-400/15 text-amber-300 hover:bg-amber-400/25"
        }`}
      >
        {unlocked ? "Recording on" : "Recording locked"}
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-[22rem] rounded-lg border border-line bg-surface p-3.5 text-ink shadow-[var(--shadow-float)]">
          <p className="label">Officer token</p>
          <p className="mt-1.5 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
            Needed to acknowledge, assign, stand down or close. Issued to the control
            room; reading the board never requires it.
          </p>
          <input
            ref={field}
            type="password"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && draft.trim()) {
                setToken(draft);
                setOpen(false);
              }
            }}
            placeholder="Paste the token"
            aria-label="Officer token"
            autoComplete="off"
            className="mt-2.5 w-full rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)]"
          />
          <div className="mt-2.5 flex items-center gap-2">
            <button
              type="button"
              disabled={!draft.trim()}
              onClick={() => {
                setToken(draft);
                setOpen(false);
              }}
              className="rounded bg-navy px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-white disabled:opacity-40"
            >
              Unlock
            </button>
            {unlocked && (
              <button
                type="button"
                onClick={() => {
                  clearToken();
                  setOpen(false);
                }}
                className="text-[length:var(--text-sm)] text-ink-2 underline"
              >
                Lock this console
              </button>
            )}
          </div>
        </div>
      )}
    </span>
  );
}
