"use client";

import { useState } from "react";
import { askCopilot, type CopilotAnswer, type View } from "@/lib/live";

const SUGGESTED = [
  "What changed in the last hour?",
  "What are the most unreliable movements in Siliguri?",
  "Show me the biggest mobility problems right now.",
  "When does travel between Siliguri Central and NJP become most variable?",
];

/** The copilot answers and then reorganises the application around the answer.
 *
 *  The five-part structure is not a prompt convention — it is the AnswerContract
 *  from packages/contracts/response.py, which refuses to construct without a
 *  limitation. What is rendered here is what the server was structurally unable
 *  to omit.
 */
export function Copilot({ onView }: { onView: (v: View) => void }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<CopilotAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      const a = await askCopilot(q);
      setAnswer(a);
      if (a.view) onView(a.view);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
        className="border-b border-rule p-4"
      >
        <label htmlFor="copilot-q" className="eyebrow">
          Ask the copilot
        </label>
        <div className="mt-3 flex gap-2">
          <input
            id="copilot-q"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What changed in the last hour?"
            className="min-w-0 flex-1 border border-rule bg-ink px-3 py-2.5 text-[length:var(--text-caption)] text-paper placeholder:text-paper-40 focus:border-copper focus:outline-none"
          />
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className="shrink-0 border border-copper bg-copper px-4 py-2.5 text-[length:var(--text-caption)] text-paper transition-opacity disabled:opacity-40"
          >
            {busy ? "Thinking…" : "Ask"}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {SUGGESTED.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setQuestion(s);
                ask(s);
              }}
              className="border border-rule px-2.5 py-1 text-[length:var(--text-micro)] text-paper-40 transition-colors hover:border-rule-lit hover:text-paper-70"
            >
              {s}
            </button>
          ))}
        </div>
      </form>

      <div className="min-h-0 flex-1 overflow-y-auto p-5">
        {error && (
          <p className="font-mono text-[length:var(--text-caption)] text-signal">{error}</p>
        )}

        {!answer && !error && (
          <p className="measure-tight text-[length:var(--text-caption)] leading-relaxed text-paper-40">
            The copilot calls the same deterministic engines the rest of this application
            reads. It cannot compute a traffic figure and has no access to anything that
            would let it — every number it gives you came out of a tool call, and the trace
            is shown beneath each answer.
          </p>
        )}

        {answer && (
          <article className="space-y-5">
            {answer.degraded && (
              <p className="border-l-2 border-signal pl-3 font-mono text-[length:var(--text-micro)] leading-relaxed text-paper-40">
                The language model was unreachable. This is the raw tool result. The figures
                are unaffected — they come from the same engines either way.
              </p>
            )}

            {(
              [
                ["Observation", answer.observation],
                ["Comparison", answer.comparison],
                ["Interpretation", answer.interpretation],
                ["Limitation", answer.limitation],
                ["Next step", answer.next_step],
              ] as const
            ).map(([label, body]) => (
              <div key={label}>
                <p
                  className={`font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] ${
                    label === "Limitation" ? "text-copper-lit" : "text-paper-40"
                  }`}
                >
                  {label}
                </p>
                <p
                  className={`mt-1.5 text-[length:var(--text-caption)] leading-relaxed ${
                    label === "Limitation" ? "text-copper-lit" : "text-paper-70"
                  }`}
                >
                  {body}
                </p>
              </div>
            ))}

            <div className="border-t border-rule pt-4">
              <p className="font-mono text-[length:var(--text-micro)] uppercase tracking-[0.14em] text-paper-40">
                Tools called
              </p>
              <ul className="mt-2 space-y-1">
                {(answer.tool_trace.length
                  ? answer.tool_trace
                  : answer.tools_called.map((t) => ({ tool: t, args: {} }))
                ).map((t, i) => (
                  <li key={i} className="font-mono text-[length:var(--text-micro)] text-copper-lit">
                    {t.tool}
                    {Object.keys(t.args ?? {}).length > 0 && (
                      <span className="text-paper-40">({JSON.stringify(t.args)})</span>
                    )}
                  </li>
                ))}
              </ul>
              <p className="mt-3 font-mono text-[length:var(--text-micro)] text-paper-40">
                {answer.model} · {answer.mode}
              </p>
            </div>
          </article>
        )}
      </div>
    </div>
  );
}
