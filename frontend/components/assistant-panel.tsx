"use client";

import { type FormEvent, useState } from "react";

import { Button, Card, ErrorNote } from "@/components/ui";
import { explainSubmission } from "@/lib/api";
import type { ExplainResponse } from "@/lib/types";

type Turn = { question: string; response: ExplainResponse };

const SUGGESTIONS = [
  "Qu'est-ce qui manque dans mon dossier ?",
  "Quel est le délai légal pour déposer ?",
  "Que risque-je si je dépose en retard ?",
];

/**
 * Chat panel over POST /assistant/explain. Answers are grounded in retrieved
 * RNE text; when the backend reports grounded=false we say so rather than
 * presenting an ungrounded answer as authoritative.
 */
export function AssistantPanel({ submissionId }: { submissionId: string }) {
  const [question, setQuestion] = useState("");
  const [lang, setLang] = useState<"fr" | "ar">("fr");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(asked: string) {
    setLoading(true);
    setError("");
    try {
      const response = await explainSubmission(submissionId, asked, lang);
      setTurns((current) => [...current, { question: asked, response }]);
      setQuestion("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "La demande a échoué.");
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(question.trim() || SUGGESTIONS[0]);
  }

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1.5">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => void ask(suggestion)}
              disabled={loading}
              className="rounded-full border border-[var(--border)] px-3 py-1 text-xs transition hover:bg-[var(--surface-muted)] disabled:opacity-50"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <div className="flex gap-1" role="group" aria-label="Langue">
          {(["fr", "ar"] as const).map((code) => (
            <button
              key={code}
              type="button"
              onClick={() => setLang(code)}
              className={`rounded-md px-2.5 py-1 text-xs font-semibold uppercase transition ${
                lang === code
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--border)]"
              }`}
            >
              {code}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 space-y-5">
        {turns.map((turn, index) => (
          <div key={index} className="space-y-2">
            <p className="text-sm font-semibold opacity-80">{turn.question}</p>
            <div
              className={`rounded-lg bg-[var(--surface-muted)] px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                turn.response.lang === "ar" ? "ar" : ""
              }`}
            >
              {turn.response.answer}
            </div>

            {turn.response.citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {turn.response.citations.map((citation) => (
                  <span
                    key={citation.entry_id}
                    title={citation.title}
                    className="rounded-full bg-[var(--brand-soft)] px-2.5 py-0.5 text-[11px] font-medium text-[var(--brand-strong)]"
                  >
                    {citation.official_reference}
                  </span>
                ))}
              </div>
            )}

            {!turn.response.grounded && (
              <p className="text-xs text-[var(--accent)]">
                Réponse non sourcée : les textes de référence du RNE
                n&apos;ont pas pu être consultés. Seul le résultat de la
                vérification est affiché.
              </p>
            )}
          </div>
        ))}

        {!turns.length && !loading && (
          <p className="text-sm opacity-60">
            Posez une question sur votre dossier. Les réponses s&apos;appuient
            uniquement sur les textes officiels du RNE.
          </p>
        )}
        {loading && <p className="text-sm opacity-60">Recherche en cours…</p>}
      </div>

      {error && (
        <div className="mt-4">
          <ErrorNote>{error}</ErrorNote>
        </div>
      )}

      <form className="mt-5 flex gap-2" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="assistant-question">
          Votre question
        </label>
        <input
          id="assistant-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Posez votre question…"
          className="min-w-0 flex-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
        />
        <Button type="submit" disabled={loading}>
          {loading ? "…" : "Envoyer"}
        </Button>
      </form>
    </Card>
  );
}
