"use client";

import { CalendarClock, CalendarX2 } from "lucide-react";

import type { SubmissionResult } from "@/lib/types";

/**
 * The legal clock, in days and in dinars.
 *
 * "Dépôt hors délai" is accurate and abstract. What decides whether someone
 * acts this week is the date, the days left or lost, and what the delay costs
 * — all of which the rules engine already computed and was keeping to itself.
 *
 * The penalty is shown as an estimate and says so. Article 51 sets it at half
 * the fee due for the operation per month or part of a month, and the fee
 * depends on the operation; the per-month figure here is the published one for
 * this kind of filer.
 */
export function DeadlinePanel({ result }: { result: SubmissionResult }) {
  const deadline = result.completeness.deadline;
  if (!deadline) return null;

  const late = (deadline.days_overdue ?? 0) > 0;
  const date = new Date(deadline.date).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const ink = late ? "var(--st-rejected-ink)" : "var(--st-approved-ink)";
  const wash = late ? "var(--st-rejected-wash)" : "var(--st-approved-wash)";
  const Icon = late ? CalendarX2 : CalendarClock;

  return (
    <section
      className="border-t border-[var(--line)] p-5 sm:p-6"
      style={{ background: wash }}
    >
      <div className="flex items-start gap-3">
        <Icon size={18} strokeWidth={1.9} aria-hidden className="mt-0.5 shrink-0" style={{ color: ink }} />
        <div className="min-w-0">
          <p className="text-[0.9375rem] leading-snug font-medium" style={{ color: ink }}>
            {late
              ? `Échéance dépassée de ${deadline.days_overdue} jours`
              : deadline.days_remaining >= 0
                ? `Il vous reste ${deadline.days_remaining} jour${deadline.days_remaining === 1 ? "" : "s"}`
                : "Échéance dépassée"}
          </p>
          <p className="mt-1 text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
            Date limite&nbsp;: <strong className="font-medium text-[var(--ink)]">{date}</strong>{" "}
            ({deadline.article}).
          </p>

          {late && deadline.penalty_months ? (
            <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
              Pénalité estimée&nbsp;:{" "}
              <strong className="font-medium text-[var(--ink)]">
                {deadline.penalty_estimate_tnd} DT
              </strong>{" "}
              — {deadline.penalty_months} mois entamé
              {deadline.penalty_months === 1 ? "" : "s"} à{" "}
              {deadline.penalty_per_month_tnd} DT. L&apos;article 51 fixe la
              pénalité à la moitié de la redevance due par mois ou fraction de
              mois&nbsp;; le montant exact dépend de l&apos;opération.
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}
