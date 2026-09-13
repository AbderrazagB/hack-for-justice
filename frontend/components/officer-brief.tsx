"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileMinus,
  Loader2,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";

import { Markdown } from "@/components/markdown";
import { submissionBrief } from "@/lib/api";
import type { Brief } from "@/lib/types";

/**
 * The dossier in one read, at the top of the officer's page.
 *
 * Opening a filing meant assembling the picture from five documents, their
 * extracted fields and a list of anomalies. This assembles it once: what
 * blocks, what merely needs looking at, which document each finding sits in,
 * and how long the dossier has waited.
 *
 * The figures are the rules engine's own findings rearranged, so they cannot
 * disagree with the verdict below them. Only the paragraph is written by a
 * model, and it is marked as such -- it is given the verdict and the retrieved
 * RNE text and is told in its prompt not to recommend a decision. The three
 * decision buttons are the officer's and stay that way.
 */
export function OfficerBrief({ submissionId }: { submissionId: string }) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    submissionBrief(submissionId)
      .then((found) => live && setBrief(found))
      .catch(
        (e) =>
          live && setError(e instanceof Error ? e.message : "Synthèse indisponible."),
      );
    return () => {
      live = false;
    };
  }, [submissionId]);

  if (error) return null;

  const glance = brief?.at_a_glance;

  return (
    <section className="rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h2 className="t-h3">Synthèse</h2>
        {glance?.waiting_hours != null && (
          <p className="flex items-center gap-1.5 text-[0.75rem] text-[var(--ink-faint)]">
            <Clock size={12} strokeWidth={2} aria-hidden />
            En attente depuis {formatWait(glance.waiting_hours)}
          </p>
        )}
      </div>

      {!brief && (
        <p className="mt-3 flex items-center gap-2 text-[0.875rem] text-[var(--ink-muted)]">
          <Loader2 size={15} strokeWidth={2} className="animate-spin" aria-hidden />
          Lecture du dossier
        </p>
      )}

      {glance && (
        <>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <Figure
              icon={AlertTriangle}
              value={glance.errors}
              label="bloquante(s)"
              tone={glance.errors ? "var(--st-rejected-ink)" : "var(--ink-faint)"}
            />
            <Figure
              icon={FileMinus}
              value={glance.documents_missing.length}
              label="pièce(s) manquante(s)"
              tone={
                glance.documents_missing.length
                  ? "var(--st-correction-ink)"
                  : "var(--ink-faint)"
              }
            />
            <Figure
              icon={CheckCircle2}
              value={`${glance.checks_passed}/${glance.checks_total}`}
              label="règles sans réserve"
              tone="var(--st-approved-ink)"
            />
          </div>

          {(glance.blocking_documents.length > 0 ||
            glance.documents_missing.length > 0) && (
            <div className="mt-4 flex flex-wrap items-center gap-x-2 gap-y-1.5 text-[0.8125rem]">
              <span className="text-[var(--ink-muted)]">À regarder&nbsp;:</span>
              {glance.documents_missing.map((document) => (
                <span
                  key={`missing-${document.key}`}
                  className="rounded-[var(--r-control)] bg-[var(--st-correction-wash)] px-2 py-0.5 text-[0.75rem] font-medium text-[var(--st-correction-ink)]"
                >
                  {document.label_fr} — absente
                </span>
              ))}
              {glance.blocking_documents.map((document) => (
                <span
                  key={`blocking-${document.key}`}
                  className="rounded-[var(--r-control)] bg-[var(--st-rejected-wash)] px-2 py-0.5 text-[0.75rem] font-medium text-[var(--st-rejected-ink)]"
                >
                  {document.label_fr}
                </span>
              ))}
            </div>
          )}

          <div className="mt-4 rounded-[var(--r-control)] border-l-2 border-[var(--teal)] bg-[var(--canvas)] px-3.5 py-3">
            <p className="flex items-center gap-1.5 text-[0.6875rem] font-semibold tracking-[0.1em] text-[var(--ink-faint)] uppercase">
              <Sparkles size={11} strokeWidth={2.2} aria-hidden />
              {brief.grounded
                ? "Résumé rédigé d'après les textes du RNE"
                : "Résumé issu des règles de vérification"}
            </p>
            {/* The model answers in Markdown here as it does in the assistant. */}
            <Markdown
              text={brief.summary}
              className="mt-1.5 text-[0.875rem] leading-relaxed text-[var(--ink)]"
            />
            <p className="mt-2 text-[0.6875rem] leading-relaxed text-[var(--ink-faint)]">
              Ce résumé ne recommande aucune décision et n&apos;en prend aucune.
              Les constats viennent des règles de vérification&nbsp;; la décision
              vous revient.
            </p>
          </div>
        </>
      )}
    </section>
  );
}

function Figure({
  icon: Icon,
  value,
  label,
  tone,
}: {
  icon: typeof AlertTriangle;
  value: number | string;
  label: string;
  tone: string;
}) {
  return (
    <div className="rounded-[var(--r-control)] bg-[var(--canvas)] px-3.5 py-3">
      <p className="flex items-center gap-2" style={{ color: tone }}>
        <Icon size={15} strokeWidth={2.1} aria-hidden />
        <span className="t-data text-[1.375rem] leading-none font-semibold">{value}</span>
      </p>
      <p className="mt-1.5 text-[0.75rem] text-[var(--ink-muted)]">{label}</p>
    </div>
  );
}

function formatWait(hours: number): string {
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 48) return `${Math.round(hours)} h`;
  return `${Math.round(hours / 24)} jours`;
}
