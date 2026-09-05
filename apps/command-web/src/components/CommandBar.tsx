"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ActionError, act, askCopilot, type CopilotAnswer, type Incident, type Officer } from "@/lib/api";
import {
  completeWithIncident,
  completeWithOfficer,
  completeWithText,
  matchIncidents,
  matchOfficers,
  parseCommand,
  startsWithVerb,
  type Intent,
  type ParseContext,
  type ParseOutcome,
} from "@/lib/intent";

/** The chat + voice front-end onto the intent layer.
 *
 *  Type or speak an action; it parses to an `Intent`, reads it back, and — for
 *  anything irreversible — waits for a confirm before it commits. Everything
 *  here is a thin skin over `act()`, the same POST the card buttons use. If the
 *  parse is wrong or the officer would rather click, the cards still work with
 *  no dependency on this bar.
 */

// ── minimal Web Speech typings (not in the DOM lib) ──────────────────────────
interface SpeechRecognitionResult {
  0: { transcript: string };
  isFinal: boolean;
}
interface SpeechRecognitionEvent {
  results: { length: number; [i: number]: SpeechRecognitionResult };
}
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((e: SpeechRecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
}
type SpeechCtor = new () => SpeechRecognitionLike;
function speechCtor(): SpeechCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: SpeechCtor; webkitSpeechRecognition?: SpeechCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

type Pending =
  | { kind: "confirm"; intent: Intent; readback: string }
  | { kind: "slot"; outcome: Extract<ParseOutcome, { kind: "need" | "disambiguate" }> }
  | null;

export function CommandBar({
  incidents,
  roster,
  officer,
  onChanged,
  onFocusIncident,
}: {
  incidents: Incident[];
  roster: Officer[];
  officer: string;
  onChanged: (updated: Incident) => void;
  onFocusIncident?: (id: string) => void;
}) {
  const [text, setText] = useState("");
  const [pending, setPending] = useState<Pending>(null);
  const [feedback, setFeedback] = useState<{ tone: "ok" | "warn" | "ask"; msg: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<CopilotAnswer | null>(null);
  const [listening, setListening] = useState(false);
  // Whether voice is available is a client-only fact. Deciding it during render
  // makes the server and the first client render disagree (the server has no
  // SpeechRecognition), which fails hydration and leaves the form's handlers in
  // a broken state. So it starts false — matching the server — and turns on
  // after mount.
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognition = useRef<SpeechRecognitionLike | null>(null);

  const mounted = useRef(true);
  useEffect(() => {
    setVoiceAvailable(speechCtor() !== null);
    return () => {
      // Stop any recognition in flight so a late onresult cannot submit a
      // phantom command against a screen that has navigated away.
      mounted.current = false;
      recognition.current?.stop();
      recognition.current = null;
    };
  }, []);

  const ctx = useCallback(
    (source: ParseContext["source"]): ParseContext => ({ incidents, roster, source }),
    [incidents, roster],
  );

  // "/" or ⌘K focuses the bar, the way a control-room operator expects.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "/" || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k")) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function commit(intent: Intent) {
    setBusy(true);
    setFeedback(null);
    try {
      const updated = await act(intent.incidentId, intent.action, {
        by: officer,
        to: intent.to,
        unit: intent.unit,
        text: intent.text,
        kind: intent.kind,
      });
      onChanged(updated);
      const place = updated.location_name || updated.title;
      setFeedback({ tone: "ok", msg: `Done — ${verbPast(intent.action)} ${place}.` });
      setPending(null);
      setText("");
    } catch (e) {
      if (e instanceof ActionError) setFeedback({ tone: "warn", msg: e.human });
      else setFeedback({ tone: "warn", msg: e instanceof Error ? e.message : String(e) });
    } finally {
      setBusy(false);
    }
  }

  /** Not a command — a question. The copilot answers from the live board. */
  async function ask(question: string) {
    setAsking(true);
    setFeedback(null);
    setAnswer(null);
    setPending(null);
    try {
      const a = await askCopilot(question);
      setAnswer(a);
      if (a.focus_incident) onFocusIncident?.(a.focus_incident);
    } catch (e) {
      setFeedback({
        tone: "warn",
        msg: e instanceof ActionError ? e.human : e instanceof Error ? e.message : String(e),
      });
    } finally {
      setAsking(false);
    }
  }

  function handleOutcome(outcome: ParseOutcome) {
    switch (outcome.kind) {
      case "ready":
        if (outcome.confirm) {
          // irreversible — read back and wait
          setPending({ kind: "confirm", intent: outcome.intent, readback: outcome.readback });
          setFeedback({ tone: "ask", msg: outcome.readback });
        } else {
          commit(outcome.intent);
        }
        break;
      case "need":
      case "disambiguate":
        setPending({ kind: "slot", outcome });
        setFeedback({ tone: "ask", msg: outcome.prompt });
        break;
      case "unknown":
        setPending(null);
        setFeedback({ tone: "warn", msg: outcome.reason });
        break;
    }
  }

  /** Submit either a fresh command, or a reply that fills a pending slot. */
  function submit(raw: string, source: ParseContext["source"]) {
    const utter = raw.trim();
    if (!utter) return;

    // A pending confirm: "yes"/"confirm" commits, anything else cancels.
    if (pending?.kind === "confirm") {
      // Whole-string affirmatives only, so "ok, cancel" cannot commit and a
      // trailing word cannot ride a bare "yes". Anything else cancels — the
      // safe side for an irreversible act.
      if (/^(yes|y|confirm|do it)\s*$/i.test(utter)) return commit(pending.intent);
      setPending(null);
      setFeedback({ tone: "warn", msg: "Cancelled." });
      setText("");
      return;
    }

    // A pending slot: resolve the reply against the missing field.
    if (pending?.kind === "slot") {
      const o = pending.outcome;
      const partial = o.partial;

      // For an officer or incident slot, a reply that opens with a verb is a
      // fresh command, not an answer — let it through to re-parse. NOT for a
      // free-text slot: a stand-down reason like "area cleared by field officer"
      // contains "cleared" and would otherwise hijack into a resolve.
      const escapeToFresh = o.field !== "text" && startsWithVerb(utter);

      if (!escapeToFresh) {
        if (o.field === "officer") {
          const matches = matchOfficers(utter, roster);
          if (matches.length === 1) {
            return handleOutcome(completeWithOfficer(partial, matches[0], incidents, source));
          }
          setFeedback({ tone: "ask", msg: matches.length ? "Which officer?" : "No such officer on the roster. Name the guard or unit." });
          setText("");
          return;
        }
        if (o.field === "incident") {
          // Reuse the parser's own matcher so the reply resolves the same way a
          // fresh command would — not a looser substring that binds differently.
          const found = matchIncidents(utter, incidents);
          if (found.length === 1) return handleOutcome(completeWithIncident(partial, found[0], ctx(source)));
          setFeedback({ tone: "ask", msg: found.length ? "More than one match — be specific." : "No open incident there." });
          setText("");
          return;
        }
        if (o.field === "text") {
          // Route through completeWithText so a destructive reason still gets
          // the readback+confirm gate instead of committing directly.
          return handleOutcome(completeWithText(partial, utter, incidents, source));
        }
      }
    }

    // Fresh command — or a question for the copilot. Commands win: only when
    // the text is not a recognised command AND reads like a question does it go
    // to the copilot. A leading "ask" or "?" forces the copilot outright.
    setAnswer(null);
    const forced = /^\s*(ask\b|\?)\s*/i.test(utter);
    const q = utter.replace(/^\s*(ask\b|\?)\s*/i, "").trim();
    if (forced && q) {
      ask(q);
      setText("");
      return;
    }
    const outcome = parseCommand(utter, ctx(source));
    if (outcome.kind === "unknown" && looksLikeQuestion(utter)) {
      ask(utter);
      setText("");
      return;
    }
    handleOutcome(outcome);
    setText("");
  }

  /** A disambiguation chip was clicked. */
  function pickOption(id: string) {
    if (pending?.kind !== "slot") return;
    const o = pending.outcome;
    if (o.field === "officer") {
      const off = roster.find((r) => r.officer_id === id);
      if (off) return handleOutcome(completeWithOfficer(o.partial, off, incidents, "click"));
    } else if (o.field === "incident") {
      const inc = incidents.find((i) => i.incident_id === id);
      if (inc) return handleOutcome(completeWithIncident(o.partial, inc, ctx("click")));
    }
    // The chosen entity is gone — a poll refreshed it out from under the click.
    setPending(null);
    setFeedback({ tone: "warn", msg: "That just changed — refreshed. Try again." });
  }

  // ── voice: push-to-talk ────────────────────────────────────────────────────
  function startVoice() {
    const Ctor = speechCtor();
    if (!Ctor || listening) return;
    const rec = new Ctor();
    rec.lang = "en-IN"; // stable session language; a stray Bengali word must not flip it mid-command
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (e) => {
      if (!mounted.current) return;
      const said = e.results[0]?.[0]?.transcript ?? "";
      if (!said.trim()) return; // a released-early or empty result submits nothing
      setText(said);
      submit(said, "voice");
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recognition.current = rec;
    setListening(true);
    rec.start();
  }
  function stopVoice() {
    recognition.current?.stop();
    setListening(false);
  }

  const disamb =
    pending?.kind === "slot" && pending.outcome.kind === "disambiguate" ? pending.outcome.options : null;

  return (
    <section aria-label="Command bar" className="card px-3 py-2.5 no-print">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(text, "chat");
        }}
        className="flex items-center gap-2"
      >
        <span aria-hidden className="pl-1 text-[length:var(--text-sm)] text-ink-3">
          {pending ? "↳" : "⌘K"}
        </span>
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={busy || asking}
          placeholder={
            pending?.kind === "slot"
              ? pending.outcome.prompt
              : pending?.kind === "confirm"
                ? "Type yes to confirm, or anything else to cancel"
                : "Command or question — “assign Venus More to guard 2”, “what changed in the last hour?”"
          }
          aria-label="Command input"
          className="flex-1 bg-transparent text-[length:var(--text-md)] outline-none placeholder:text-ink-3"
        />
        {/* Enables Enter-to-send: a form with only type=button controls does not
            submit implicitly. Visually hidden; the input carries the affordance. */}
        <button type="submit" className="sr-only">
          Send command
        </button>

        {pending?.kind === "confirm" && (
          <>
            <button
              type="button"
              onClick={() => commit(pending.intent)}
              disabled={busy}
              className="rounded bg-sev px-3 py-1.5 text-[length:var(--text-sm)] font-semibold text-white disabled:opacity-40"
              style={{ backgroundColor: "var(--color-sev)" }}
            >
              Confirm
            </button>
            <button
              type="button"
              onClick={() => {
                setPending(null);
                setFeedback(null);
                setText("");
              }}
              className="rounded border border-line-firm px-3 py-1.5 text-[length:var(--text-sm)] text-ink-2"
            >
              Cancel
            </button>
          </>
        )}

        {voiceAvailable && pending?.kind !== "confirm" && (
          <button
            type="button"
            aria-pressed={listening}
            aria-label={listening ? "Listening — release to send" : "Hold to speak a command"}
            onPointerDown={startVoice}
            onPointerUp={stopVoice}
            onPointerLeave={stopVoice}
            className={`rounded-full px-3 py-1.5 text-[length:var(--text-sm)] font-medium transition-colors ${
              listening ? "bg-sev text-white" : "border border-line-firm text-ink-2 hover:bg-sunken"
            }`}
            style={listening ? { backgroundColor: "var(--color-sev)" } : undefined}
          >
            {listening ? "● Listening" : "🎙 Hold"}
          </button>
        )}
      </form>

      {disamb && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {disamb.map((o) => (
            <button
              key={o.id}
              type="button"
              onClick={() => pickOption(o.id)}
              className="rounded-full border border-line-firm bg-surface px-2.5 py-1 text-[length:var(--text-sm)] text-ink-2 hover:bg-sunken"
            >
              {o.label}
            </button>
          ))}
        </div>
      )}

      {feedback && (
        <p
          className="mt-2 text-[length:var(--text-sm)]"
          style={{
            color:
              feedback.tone === "ok"
                ? "var(--color-ok)"
                : feedback.tone === "warn"
                  ? "var(--color-sev)"
                  : "var(--color-ink-2)",
          }}
        >
          {feedback.msg}
        </p>
      )}

      {asking && (
        <p className="mt-2 text-[length:var(--text-sm)] text-ink-2">Asking the copilot…</p>
      )}

      {answer && (
        <div className="mt-2.5 rounded-lg border border-line bg-raised p-3.5">
          <div className="flex items-center justify-between">
            <span className="label">Copilot</span>
            <button
              type="button"
              onClick={() => setAnswer(null)}
              className="text-[length:var(--text-2xs)] text-ink-3 underline"
            >
              Dismiss
            </button>
          </div>
          <dl className="mt-2 space-y-2">
            {(
              [
                ["Observation", answer.observation],
                ["Comparison", answer.comparison],
                ["Interpretation", answer.interpretation],
                ["Limitation", answer.limitation],
                ["Next step", answer.next_step],
              ] as const
            ).map(([k, v]) => (
              <div key={k}>
                <dt
                  className="label"
                  style={k === "Limitation" ? { color: "var(--color-copper)" } : undefined}
                >
                  {k}
                </dt>
                <dd className="text-[length:var(--text-sm)] leading-relaxed text-ink-2">{v}</dd>
              </div>
            ))}
          </dl>
          {answer.focus_incident && onFocusIncident && (
            <button
              type="button"
              onClick={() => onFocusIncident(answer.focus_incident!)}
              className="mt-2.5 rounded border border-line-firm bg-surface px-2.5 py-1.5 text-[length:var(--text-sm)] font-medium text-ink-2 hover:bg-sunken"
            >
              Show the incident
            </button>
          )}
          <p className="mt-2.5 border-t border-line pt-2 text-[length:var(--text-2xs)] text-ink-3">
            {answer.degraded ? "Answered from the board — the model is offline. " : ""}
            From: {answer.tools_called.join(", ")}
          </p>
        </div>
      )}
    </section>
  );
}

/** A heuristic for whether an unrecognised utterance is a question the copilot
 *  should answer, rather than a mistyped command. */
function looksLikeQuestion(t: string): boolean {
  const s = t.trim().toLowerCase();
  if (s.endsWith("?")) return true;
  return /^(what|whats|when|where|why|how|which|who|is|are|does|do|show|tell|list|any|should|can|could|give me)\b/.test(s);
}

function verbPast(action: string): string {
  return (
    {
      acknowledge: "acknowledged",
      assign: "assigned",
      "on-scene": "marked on scene",
      clearing: "marked clearing",
      resolve: "resolved",
      close: "closed",
      "stand-down": "stood down",
      note: "logged against",
    } as Record<string, string>
  )[action] ?? action;
}
