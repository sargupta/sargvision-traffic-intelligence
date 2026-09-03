"use client";

import { useEffect } from "react";

/** What the room sees if the board itself fails.
 *
 *  Without this, an exception anywhere in the tree unmounts everything and
 *  leaves a white screen — no incidents, no map, and nothing saying whether
 *  the failure is here or in the city. A duty officer cannot tell those apart
 *  from a blank page, and the honest instruction in that moment is "the
 *  screen is down, the road is not; work the wireless."
 *
 *  Recovering matters as much as explaining. Incidents live on the server, so
 *  reset() re-renders against the real record and loses nothing an officer
 *  did.
 */
export default function BoardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Goes to the browser console and, on Cloud Run, into the request log.
    console.error("board render failed", error);
  }, [error]);

  return (
    <main className="mx-auto flex w-full max-w-[42rem] flex-col gap-4 px-4 py-16">
      <div className="card border-l-[3px] p-6" style={{ borderLeftColor: "var(--color-sev)" }}>
        <p className="label">The board stopped drawing</p>
        <h1 className="mt-2 text-[length:var(--text-xl)] font-semibold leading-snug">
          This screen failed. Traffic is unaffected.
        </h1>
        <p className="mt-3 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          Nothing recorded has been lost — incidents, assignments and notes are held by
          the command centre, not by this page. Reloading shows the current state.
        </p>
        <p className="mt-2 text-[length:var(--text-sm)] leading-relaxed text-ink-2">
          Until it comes back, work the wireless. Do not treat a blank board as a quiet city.
        </p>

        {/* eslint-disable @next/next/no-html-link-for-pages --
            These are deliberately plain anchors. <Link> navigates on the
            client, which keeps the very JavaScript state that just failed;
            a full document load is what actually recovers the console. */}
        <div className="mt-5 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={reset}
            className="rounded bg-navy px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-white transition-colors hover:bg-navy-2"
          >
            Try again
          </button>
          <a
            href="/"
            className="rounded border border-line-firm bg-surface px-3 py-1.5 text-[length:var(--text-sm)] font-medium text-ink-2 transition-colors hover:bg-sunken"
          >
            Reload the board
          </a>
        </div>

        {/* This boundary replaces the page, and the page is what renders the
            navigation — so without these the officer is stranded on the one
            view that is broken while the others may be working. */}
        <div className="mt-5 border-t border-line pt-4">
          <p className="label">Other views, which may still be working</p>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-2">
            {[
              ["/field", "Field", "what a sergeant at a junction needs"],
              ["/handover", "Handover", "the shift record"],
              ["/network", "Network", "junctions and corridors"],
            ].map(([href, label, hint]) => (
              <a
                key={href}
                href={href}
                className="text-[length:var(--text-sm)] text-ink-2 underline decoration-line-firm underline-offset-2 hover:text-ink"
              >
                {label}
                <span className="ml-1.5 text-[length:var(--text-2xs)] text-ink-3">{hint}</span>
              </a>
            ))}
          </div>
        </div>

        {error.digest && (
          <p className="mt-5 border-t border-line pt-3 text-[length:var(--text-2xs)] text-ink-3">
            Reference for the log: <span className="tnum">{error.digest}</span>
          </p>
        )}
      </div>
      {/* eslint-enable @next/next/no-html-link-for-pages */}
    </main>
  );
}
