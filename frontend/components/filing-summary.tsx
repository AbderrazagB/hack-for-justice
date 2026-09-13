"use client";

import { Check, Lock } from "lucide-react";

export type SummaryRow = {
  key: string;
  label_fr: string;
  label_ar: string;
  done: number;
  total: number;
};

/**
 * The running state of the filing, beside the form.
 *
 * The form itself is one column, because a form to be filled top to bottom
 * should be; that leaves horizontal room on a wide screen. This is what the
 * room is for -- not a second column of questions, but the thing a person
 * filling a long form actually wants to see: how much of it is left, without
 * scrolling back to count.
 *
 * Counts are derived from the same state the check is built from, so the rail
 * can never claim progress the submission would not.
 */
export function FilingSummary({ rows }: { rows: SummaryRow[] }) {
  return (
    <div className="rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-5">
      <h2 className="t-label text-[var(--ink-muted)]">Votre dossier</h2>

      <ul className="mt-3 space-y-3">
        {rows.map((row) => {
          const complete = row.total > 0 && row.done >= row.total;
          return (
            <li key={row.key} className="flex items-start gap-2.5">
              <span
                aria-hidden
                className={`mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full text-[0.625rem] font-semibold ${
                  complete
                    ? "bg-[var(--teal-wash)] text-[var(--teal-ink)]"
                    : "border border-[var(--line-strong)] text-[var(--ink-faint)]"
                }`}
              >
                {complete ? <Check size={12} strokeWidth={2.8} /> : row.done}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[0.8125rem] text-[var(--ink)]">
                  {row.label_fr}
                </span>
                <span className="ar ar-left block text-[0.6875rem] text-[var(--ink-faint)]">
                  {row.label_ar}
                </span>
              </span>
              <span className="t-data shrink-0 text-[0.75rem] text-[var(--ink-muted)]">
                {row.done}/{row.total}
              </span>
            </li>
          );
        })}
      </ul>

      <p className="mt-4 flex items-start gap-2 border-t border-[var(--line)] pt-3.5 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
        <Lock size={12} strokeWidth={1.9} className="mt-0.5 shrink-0" aria-hidden />
        Rien n&apos;est transmis au registre à cette étape. La vérification a
        lieu chez vous, avant le dépôt.
      </p>
    </div>
  );
}
