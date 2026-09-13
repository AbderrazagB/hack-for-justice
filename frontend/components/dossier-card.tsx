"use client";

import { AlertTriangle, ArrowRight, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";

import { StatusBadge } from "@/components/ui";
import { COMPLETENESS_STATUS } from "@/lib/status";
import type { SubmissionSummary } from "@/lib/types";

/**
 * One dossier, as a card in a grid.
 *
 * Both lists were a single column of full-width rows: six cards each repeating
 * the same procedure name across a whole screen, so telling them apart meant
 * reading every one. A dossier is identified by its reference, its state and
 * what is wrong with it -- three short things that fit side by side.
 *
 * The whole card is the link. A row whose only target is a small "ouvrir" is a
 * row you have to aim at.
 */
export function DossierCard({
  submission,
  href,
  showAge = false,
}: {
  submission: SubmissionSummary;
  href: string;
  /** The officer triages on how long a dossier has waited; the applicant does not. */
  showAge?: boolean;
}) {
  const completeness = submission.completeness_status
    ? COMPLETENESS_STATUS[submission.completeness_status]
    : null;
  const blocking = submission.error_flag_count;
  const total = submission.flag_count;

  return (
    <Link
      href={href}
      className="group flex h-full flex-col rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-4 transition-colors hover:border-[var(--teal)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="t-data text-[0.75rem] text-[var(--ink-faint)]">{submission.id}</p>
        <StatusBadge status={submission.status} size="sm" />
      </div>

      <p className="mt-2 text-[0.9375rem] leading-snug font-medium text-[var(--navy)]">
        {submission.display_name_fr}
      </p>
      <p className="ar ar-left text-[0.75rem] text-[var(--ink-faint)]">
        {submission.display_name_ar}
      </p>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[0.75rem]">
        {total === 0 ? (
          <span className="inline-flex items-center gap-1.5 text-[var(--st-approved-ink)]">
            <CheckCircle2 size={13} strokeWidth={2.1} aria-hidden />
            Aucune anomalie
          </span>
        ) : (
          <span
            className="inline-flex items-center gap-1.5 font-medium"
            style={{
              color: blocking
                ? "var(--st-rejected-ink)"
                : "var(--st-correction-ink)",
            }}
          >
            <AlertTriangle size={13} strokeWidth={2.1} aria-hidden />
            {total} relevé{total > 1 ? "s" : ""}
            {blocking > 0 && `, ${blocking} bloquant${blocking > 1 ? "s" : ""}`}
          </span>
        )}
        {completeness && (
          <span className="text-[var(--ink-muted)]">{completeness.fr}</span>
        )}
      </div>

      <div className="mt-auto flex flex-wrap items-center justify-between gap-2 pt-3">
        <span className="inline-flex items-center gap-1.5 text-[0.6875rem] text-[var(--ink-faint)]">
          <Clock size={11} strokeWidth={2} aria-hidden />
          {showAge
            ? waited(submission.created_at)
            : new Date(submission.created_at).toLocaleDateString("fr-FR")}
        </span>
        <span className="inline-flex items-center gap-1 text-[0.75rem] font-medium text-[var(--teal-ink)]">
          Ouvrir
          <ArrowRight
            size={13}
            strokeWidth={2}
            aria-hidden
            className="transition-transform group-hover:translate-x-0.5"
          />
        </span>
      </div>
    </Link>
  );
}

function waited(createdAt: string): string {
  const hours = (Date.now() - new Date(createdAt).getTime()) / 3_600_000;
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`;
  if (hours < 48) return `${Math.round(hours)} h`;
  return `${Math.round(hours / 24)} jours`;
}
