"use client";

import { FileWarning } from "lucide-react";

import BlurText from "@/components/BlurText";
import { useReducedMotion } from "@/components/motion";
import { FloatingPanel, SeverityTag } from "@/components/ui";
import { COMPLETENESS_STATUS, DOCUMENT_SHORT_FR } from "@/lib/status";
import type { SubmissionResult } from "@/lib/types";

/**
 * The verdict.
 *
 * This is the one orchestrated moment on the applicant side: the answer
 * arriving. React Bits `BlurText` settles the headline word by word, once; the
 * findings beneath it are static. No other animation on this screen.
 */
export function VerdictPanel({ result }: { result: SubmissionResult }) {
  const reduced = useReducedMotion();
  const status = COMPLETENESS_STATUS[result.completeness.status];
  const Icon = status.icon;
  const { missing_documents: missing } = result.completeness;

  return (
    <FloatingPanel accent={status.ink}>
      <div className="p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full"
            style={{ background: status.wash, color: status.ink }}
          >
            <Icon size={19} strokeWidth={2} />
          </span>
          <div className="min-w-0">
            {reduced ? (
              <h2 className="t-h2" style={{ color: status.ink }}>
                {status.fr}
              </h2>
            ) : (
              <BlurText
                key={result.submission_id}
                text={status.fr}
                delay={70}
                animateBy="words"
                direction="top"
                stepDuration={0.32}
                className="t-h2"
              />
            )}
            <p className="ar text-[0.875rem] text-[var(--ink-muted)]">
              {status.ar}
            </p>
          </div>
        </div>

        <dl className="mt-5 grid grid-cols-3 gap-px overflow-hidden rounded-[var(--r-control)] bg-[var(--line)]">
          <Figure label="Anomalies" value={result.flag_summary.total} />
          <Figure
            label="Bloquantes"
            value={result.flag_summary.errors}
            tone="var(--st-rejected-ink)"
          />
          <Figure
            label="À vérifier"
            value={result.flag_summary.warnings}
            tone="var(--st-correction-ink)"
          />
        </dl>

        <p className="mt-4 text-[0.75rem] text-[var(--ink-faint)]">
          Référence du dossier{" "}
          <span className="t-data text-[var(--ink-muted)]">
            {result.submission_id}
          </span>
        </p>
      </div>

      {missing.length > 0 && (
        <section className="border-t border-[var(--line)] p-5 sm:p-6">
          <h3 className="t-h3">Pièces à ajouter</h3>
          <ul className="mt-3 space-y-2">
            {missing.map((document) => (
              <li key={document.key} className="flex items-start gap-2.5">
                <FileWarning
                  size={15}
                  strokeWidth={1.75}
                  className="mt-0.5 shrink-0 text-[var(--st-rejected-ink)]"
                  aria-hidden
                />
                <span className="min-w-0">
                  <span className="block text-[0.875rem]">
                    {DOCUMENT_SHORT_FR[document.key] ?? document.label_fr}
                  </span>
                  <span className="ar block text-[0.75rem] text-[var(--ink-faint)]">
                    {document.label_ar}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.flags.length > 0 && (
        <section className="border-t border-[var(--line)] p-5 sm:p-6">
          <h3 className="t-h3">Ce qu&apos;il faut corriger</h3>
          <ul className="mt-3 space-y-3.5">
            {result.flags.map((flag, index) => (
              <li key={`${flag.code}-${index}`}>
                <div className="flex items-start gap-2">
                  <SeverityTag severity={flag.severity} />
                  <p className="min-w-0 text-[0.875rem] leading-relaxed">
                    {flag.message_fr}
                  </p>
                </div>
                <p className="ar mt-1 pl-1 text-[0.8125rem] text-[var(--ink-muted)]">
                  {flag.message_ar}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.flags.length === 0 && result.completeness.status === "COMPLETE" && (
        <section
          className="border-t border-[var(--line)] p-5 text-[0.875rem] leading-relaxed sm:p-6"
          style={{ background: status.wash, color: status.ink }}
        >
          Les cinq pièces sont présentes et concordent. Vous pouvez déposer ce
          dossier sur le portail du RNE.
        </section>
      )}
    </FloatingPanel>
  );
}

function Figure({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: string;
}) {
  return (
    <div className="bg-[var(--surface)] px-3 py-3 text-center">
      <dd
        className="font-[family-name:var(--font-space-grotesk)] text-[1.5rem] leading-none font-semibold tabular-nums"
        style={{ color: value > 0 && tone ? tone : "var(--ink)" }}
      >
        {value}
      </dd>
      <dt className="mt-1 text-[0.6875rem] text-[var(--ink-muted)]">{label}</dt>
    </div>
  );
}
