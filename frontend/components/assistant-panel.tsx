"use client";

import { BookOpen, CornerDownLeft, Info } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";

import { Notice, Panel } from "@/components/ui";
import { explainSubmission } from "@/lib/api";
import type { ExplainResponse } from "@/lib/types";

type Turn = { question: string; response: ExplainResponse };

const FILE_SUGGESTIONS = [
  "Qu'est-ce qui manque dans mon dossier ?",
  "Quel est le délai légal pour déposer ?",
  "Que se passe-t-il si je dépose en retard ?",
];

// Asked before anything is uploaded, so nothing here presumes a dossier.
const GENERAL_SUGGESTIONS = [
  "Quelles pièces dois-je fournir ?",
  "Quel est le délai légal pour déposer ?",
  "Que se passe-t-il si je dépose en retard ?",
];

/**
 * Grounded assistant. Every answer carries the official references it was built
 * from; when the backend reports grounded=false we say the answer is unsourced
 * rather than presenting it as authoritative.
 *
 * `submissionId` is null when the assistant is opened with no filing in hand --
 * the floating case. The distinction is not cosmetic: with a filing, an
 * unsourced answer can still fall back on the rules engine's verdict; without
 * one there is nothing left to stand on, and the backend declines instead.
 */
export function AssistantPanel({
  submissionId,
  floating = false,
}: {
  submissionId: string | null;
  floating?: boolean;
}) {
  const [question, setQuestion] = useState("");
  const [lang, setLang] = useState<"fr" | "ar">("fr");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const suggestions = submissionId ? FILE_SUGGESTIONS : GENERAL_SUGGESTIONS;

  useEffect(() => {
    if (floating && (turns.length || loading)) {
      endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [floating, turns, loading]);

  async function ask(asked: string) {
    setLoading(true);
    setError("");
    try {
      const response = await explainSubmission(submissionId, asked, lang);
      setTurns((current) => [...current, { question: asked, response }]);
      setQuestion("");
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "La réponse n'a pas pu être générée. Réessayez dans un instant.",
      );
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(question.trim() || suggestions[0]);
  }

  const Shell = floating ? FloatingShell : Panel;

  return (
    <Shell className={floating ? "" : "overflow-hidden"}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--line)] px-5 py-3">
        {/* In the narrow floating panel the chips wrap to three lines, so they
            step aside once the conversation has actually started. */}
        <div className={`flex flex-wrap gap-1.5 ${floating && turns.length ? "hidden" : ""}`}>
          {suggestions.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => void ask(suggestion)}
              disabled={loading}
              className="rounded-[var(--r-control)] border border-[var(--line)] px-2.5 py-1 text-[0.75rem] text-[var(--ink-muted)] transition-colors hover:border-[var(--line-strong)] hover:text-[var(--ink)] disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <div className="flex gap-0.5 rounded-[var(--r-control)] bg-[var(--canvas)] p-0.5" role="group" aria-label="Langue de la réponse">
          {(["fr", "ar"] as const).map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => setLang(code)}
              aria-pressed={lang === code}
              className={`rounded-[4px] px-2.5 py-1 text-[0.75rem] font-medium uppercase transition-colors ${
                lang === code
                  ? "bg-[var(--navy)] text-white"
                  : "text-[var(--ink-muted)] hover:text-[var(--ink)]"
              }`}
            >
              {code}
            </button>
          ))}
        </div>
      </div>

      <div
        className={`space-y-6 px-5 py-5 ${floating ? "min-h-0 flex-1 overflow-y-auto" : ""}`}
      >
        {turns.map((turn, index) => (
          <div key={index}>
            <p className="t-label text-[var(--ink-muted)]">{turn.question}</p>
            <div
              className={`mt-2 text-[0.9375rem] leading-relaxed whitespace-pre-wrap ${
                turn.response.lang === "ar" ? "ar" : ""
              }`}
            >
              {turn.response.answer}
            </div>

            {turn.response.citations.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-1.5">
                <BookOpen
                  size={13}
                  strokeWidth={1.75}
                  className="text-[var(--ink-faint)]"
                  aria-hidden
                />
                {turn.response.citations.map((citation) => (
                  <span
                    key={citation.entry_id}
                    title={citation.title}
                    className="rounded-[var(--r-control)] bg-[var(--teal-wash)] px-2 py-0.5 text-[0.6875rem] font-medium text-[var(--teal-ink)]"
                  >
                    {citation.official_reference}
                  </span>
                ))}
              </div>
            )}

            {!turn.response.grounded && (
              <p className="mt-2 flex items-start gap-1.5 text-[0.75rem] text-[var(--st-correction-ink)]">
                <Info size={13} strokeWidth={2} className="mt-0.5 shrink-0" aria-hidden />
                {turn.response.submission_id
                  ? "Les textes de référence du RNE n'ont pas pu être consultés. Seul le résultat de la vérification est affiché ci-dessus."
                  : "Les textes de référence du RNE n'ont pas pu être consultés. Aucune réponse n'est donnée sans source."}
              </p>
            )}
          </div>
        ))}

        {!turns.length && !loading && (
          <p className="text-[0.875rem] leading-relaxed text-[var(--ink-muted)]">
            {submissionId
              ? "Posez une question sur votre dossier. Chaque réponse s'appuie uniquement sur les textes officiels du RNE, et cite lesquels."
              : "Posez une question sur la démarche. Chaque réponse s'appuie uniquement sur les textes officiels du RNE, et cite lesquels."}
          </p>
        )}
        {loading && (
          <p className="text-[0.875rem] text-[var(--ink-muted)]">
            Recherche dans les textes du RNE
          </p>
        )}
        <div ref={endRef} />
      </div>

      {error && (
        <div className="px-5 pb-4">
          <Notice>{error}</Notice>
        </div>
      )}

      <form
        className="flex gap-2 border-t border-[var(--line)] bg-[var(--canvas)] px-5 py-3"
        onSubmit={onSubmit}
      >
        <label className="sr-only" htmlFor="assistant-question">
          Votre question
        </label>
        <input
          id="assistant-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Posez votre question"
          className="min-w-0 flex-1 rounded-[var(--r-control)] border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-[0.875rem] outline-none focus:border-[var(--teal)]"
        />
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-[var(--r-control)] bg-[var(--navy)] px-3.5 py-2 text-[0.8125rem] font-medium text-white transition-colors hover:bg-[var(--navy-deep)] disabled:opacity-50"
        >
          <CornerDownLeft size={14} strokeWidth={2} aria-hidden />
          <span className={floating ? "sr-only" : ""}>Envoyer</span>
        </button>
      </form>
    </Shell>
  );
}

/**
 * Inside the floating widget the surrounding popover already draws the border
 * and shadow, so the panel contributes only the column that lets the turn list
 * scroll while the composer stays put.
 */
function FloatingShell({ children }: { children: React.ReactNode; className?: string }) {
  return <div className="flex min-h-0 flex-1 flex-col">{children}</div>;
}
