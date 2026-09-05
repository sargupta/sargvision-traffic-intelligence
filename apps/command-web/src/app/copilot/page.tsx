"use client";

import { useRef, useState } from "react";
import { Chrome } from "@/components/Chrome";
import { CopilotResult, SUGGESTIONS } from "@/components/Copilot";
import { askCopilot, useBoard, type CopilotAnswer } from "@/lib/api";

// ── minimal push-to-talk (Web Speech), so the page is multimodal like the bar ──
interface RecEvent {
  results: { length: number; [i: number]: { 0: { transcript: string } } };
}
interface Rec {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((e: RecEvent) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}
type RecCtor = new () => Rec;
function recCtor(): RecCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: RecCtor; webkitSpeechRecognition?: RecCtor };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

type Turn = {
  id: number;
  q: string;
  answer: CopilotAnswer | null;
  error: string | null;
  pending: boolean;
};

let seq = 0;

export default function CopilotPage() {
  const { board, connected } = useBoard();
  const [text, setText] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [listening, setListening] = useState(false);
  const rec = useRef<Rec | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function ask(question: string) {
    const q = question.trim();
    if (!q) return;
    const id = ++seq;
    setTurns((t) => [{ id, q, answer: null, error: null, pending: true }, ...t]);
    setText("");
    try {
      const answer = await askCopilot(q);
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, answer, pending: false } : x)));
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setTurns((t) => t.map((x) => (x.id === id ? { ...x, error: msg, pending: false } : x)));
    }
  }

  function startVoice() {
    const Ctor = recCtor();
    if (!Ctor || listening) return;
    const r = new Ctor();
    r.lang = "en-IN";
    r.continuous = false;
    r.interimResults = false;
    r.onresult = (e) => {
      const said = e.results[0]?.[0]?.transcript ?? "";
      if (said.trim()) ask(said);
    };
    r.onerror = () => setListening(false);
    r.onend = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  }
  function stopVoice() {
    rec.current?.stop();
    setListening(false);
  }

  const voiceAvailable = typeof window !== "undefined" && recCtor() !== null;

  return (
    <>
      <Chrome
        at={board?.at}
        connected={connected}
        cycle={board?.cycle}
        officer="Duty Officer"
        pollSeconds={board?.poll_seconds}
      />

      <main id="main" className="mx-auto w-full max-w-[56rem] px-4 py-5 lg:px-6">
        <header className="mb-4">
          <h1 className="text-[length:var(--text-xl)] font-semibold">Copilot</h1>
          <p className="mt-1 max-w-[72ch] text-[length:var(--text-sm)] leading-relaxed text-ink-2">
            Ask about the city — what is happening now, what changed, what is typical for the hour,
            and whether a deployment worked. Every figure comes from the same engines the board
            reads; the copilot explains them and states what it cannot tell you.
          </p>
        </header>

        {/* Ask bar — sticky, so it stays reachable as answers stack below. */}
        <div className="sticky top-2 z-10 mb-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask(text);
            }}
            className="card flex items-center gap-2 px-3 py-2.5 shadow-[var(--shadow-card)]"
          >
            <span aria-hidden className="pl-1 text-[length:var(--text-sm)] text-ink-3">
              ?
            </span>
            <input
              ref={inputRef}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Ask a question — “when is travel usually worst?”, “did our deployments work today?”"
              aria-label="Ask the copilot"
              className="flex-1 bg-transparent text-[length:var(--text-md)] outline-none placeholder:text-ink-3"
            />
            <button
              type="submit"
              className="rounded bg-navy px-3 py-1.5 text-[length:var(--text-sm)] font-semibold text-white"
            >
              Ask
            </button>
            {voiceAvailable && (
              <button
                type="button"
                aria-label={listening ? "Listening — release to send" : "Hold to speak"}
                onPointerDown={startVoice}
                onPointerUp={stopVoice}
                onPointerLeave={stopVoice}
                className={`rounded-full px-3 py-1.5 text-[length:var(--text-sm)] font-medium transition-colors ${
                  listening ? "text-white" : "border border-line-firm text-ink-2 hover:bg-sunken"
                }`}
                style={listening ? { backgroundColor: "var(--color-sev)" } : undefined}
              >
                {listening ? "● Listening" : "🎙 Hold"}
              </button>
            )}
          </form>
        </div>

        {/* Empty state — the range of questions, prominent, past and present. */}
        {turns.length === 0 && (
          <div className="grid gap-3 sm:grid-cols-2">
            {SUGGESTIONS.map((g) => (
              <div key={g.group} className="card p-4">
                <p className="label mb-2">{g.group}</p>
                <ul className="flex flex-col gap-1.5">
                  {g.questions.map((q) => (
                    <li key={q}>
                      <button
                        type="button"
                        onClick={() => ask(q)}
                        className="text-left text-[length:var(--text-sm)] text-ink-2 underline decoration-line-firm underline-offset-2 hover:text-ink"
                      >
                        {q}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        )}

        {/* The conversation — newest first, so the latest answer needs no scroll. */}
        <ul className="flex flex-col gap-5">
          {turns.map((turn) => (
            <li key={turn.id}>
              <p className="mb-1.5 flex items-baseline gap-2 text-[length:var(--text-md)] font-semibold">
                <span aria-hidden className="text-ink-3">
                  ?
                </span>
                {turn.q}
              </p>
              {turn.pending ? (
                <p className="text-[length:var(--text-sm)] text-ink-2">Thinking…</p>
              ) : turn.error ? (
                <p className="text-[length:var(--text-sm)]" style={{ color: "var(--color-sev)" }}>
                  {turn.error}
                </p>
              ) : turn.answer ? (
                <CopilotResult
                  answer={turn.answer}
                  onDismiss={() => setTurns((t) => t.filter((x) => x.id !== turn.id))}
                />
              ) : null}
            </li>
          ))}
        </ul>
      </main>
    </>
  );
}
