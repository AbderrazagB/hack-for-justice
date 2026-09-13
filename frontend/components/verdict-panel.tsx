"use client";

import {
  Check,
  ChevronDown,
  Download,
  FileWarning,
  HelpCircle,
  ScanSearch,
  X,
} from "lucide-react";
import { useState } from "react";

import BlurText from "@/components/BlurText";
import { useReducedMotion } from "@/components/motion";
import { EvidenceViewer } from "@/components/evidence-viewer";
import { FloatingPanel, SeverityTag } from "@/components/ui";
import { preparationSheetUrl } from "@/lib/api";
import { COMPLETENESS_STATUS, DOCUMENT_SHORT_FR } from "@/lib/status";
import type { SubmissionResult } from "@/lib/types";

/**
 * The verdict.
 *
 * This is the one orchestrated moment on the applicant side: the answer
 * arriving. React Bits `BlurText` settles the headline word by word, once; the
 * findings beneath it are static. No other animation on this screen.
 */
/**
 * How each verified rule is marked. INDETERMINATE is its own state and not a
 * failure: "we could not read enough to decide" is a different thing to say
 * than "this is wrong", and collapsing the two would accuse people of faults
 * the engine never found.
 */
const CHECK_MARKS: Record<
  string,
  { icon: typeof Check; color: string; label: string }
> = {
  PASS: { icon: Check, color: "var(--st-approved-ink)", label: "Conforme" },
  FAIL: { icon: X, color: "var(--st-rejected-ink)", label: "Non conforme" },
  INDETERMINATE: {
    icon: HelpCircle,
    color: "var(--st-correction-ink)",
    label: "Non vérifiable",
  },
};

export function VerdictPanel({ result }: { result: SubmissionResult }) {
  const reduced = useReducedMotion();
  const status = COMPLETENESS_STATUS[result.completeness.status];
  const Icon = status.icon;
  const { missing_documents: missing } = result.completeness;
  // Which finding the reader asked to see on the page, if any.
  const [shown, setShown] = useState<{ code: string; title: string } | null>(null);
  const [showChecks, setShowChecks] = useState(false);
  const passed = result.completeness.checks.filter(
    (check) => check.outcome === "PASS",
  ).length;

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

        {/* The preparation sheet, not a filing: since July 2026 the declaration
            itself is completed on the RNE portal and signed digitally. */}
        <a
          href={preparationSheetUrl(result.submission_id)}
          className="mt-4 inline-flex items-center gap-2 rounded-[var(--r-control)] border border-[var(--line-strong)] px-3.5 py-2.5 text-[0.875rem] font-medium text-[var(--navy)] transition-colors hover:bg-[var(--canvas)]"
        >
          <Download size={16} strokeWidth={2} aria-hidden />
          Télécharger la fiche de préparation
        </a>
        <p className="mt-1.5 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
          Récapitulatif de votre déclaration, à recopier sur le portail du RNE.
          Ce n&apos;est pas un dépôt officiel.
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
                {/* Only where there is a page to point at. A missing document
                    has none, and offering to show it would be a dead end. */}
                {(flag.documents?.length ?? 0) > 0 && (
                  <button
                    type="button"
                    onClick={() => setShown({ code: flag.code, title: flag.message_fr })}
                    className="mt-1.5 inline-flex items-center gap-1.5 text-[0.75rem] font-medium text-[var(--teal-ink)] underline-offset-2 hover:underline"
                  >
                    <ScanSearch size={13} strokeWidth={2} aria-hidden />
                    Voir sur la pièce
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Everything that was verified, not only what failed. A verdict that
          lists three problems and nothing else leaves the reader unable to
          tell what it actually looked at -- and a PASS is the part that says
          the check ran and found nothing, which is different from not having
          been checked. */}
      {/* A check we did not run is named, not omitted. Leaving it out reads
          as a check that passed -- the applicant who skipped the declaration
          screens was being told nothing at all about them. */}
      {(result.completeness.skipped_checks?.length ?? 0) > 0 && (
        <section className="border-t border-[var(--line)] bg-[var(--st-correction-wash)]/40 p-5 sm:p-6">
          <h3 className="t-label text-[var(--st-correction-ink)]">
            Non vérifié
          </h3>
          <ul className="mt-2 space-y-2">
            {result.completeness.skipped_checks.map((skipped) => (
              <li key={skipped.name}>
                <p className="text-[0.8125rem] leading-snug text-[var(--ink)]">
                  {skipped.label_fr}
                </p>
                <p className="mt-0.5 text-[0.75rem] leading-relaxed text-[var(--ink-muted)]">
                  {skipped.reason_fr}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.completeness.checks.length > 0 && (
        <section className="border-t border-[var(--line)] p-5 sm:p-6">
          <button
            type="button"
            onClick={() => setShowChecks((open) => !open)}
            aria-expanded={showChecks}
            className="flex w-full items-center justify-between gap-3 text-left"
          >
            <span className="t-h3">Ce que nous avons vérifié</span>
            <span className="flex shrink-0 items-center gap-1.5 text-[0.75rem] font-medium text-[var(--teal-ink)]">
              {passed} sur {result.completeness.checks.length} sans réserve
              <ChevronDown
                size={13}
                strokeWidth={2.2}
                aria-hidden
                className={`transition-transform ${showChecks ? "rotate-180" : ""}`}
              />
            </span>
          </button>

          <ul className="mt-3.5 space-y-3" hidden={!showChecks}>
            {result.completeness.checks.map((check) => {
              const mark = CHECK_MARKS[check.outcome];
              return (
                <li key={check.name} className="flex items-start gap-2.5">
                  <span
                    aria-hidden
                    className="mt-0.5 flex size-4 shrink-0 items-center justify-center"
                    style={{ color: mark.color }}
                  >
                    <mark.icon size={14} strokeWidth={2.4} />
                  </span>
                  <div className="min-w-0">
                    <p className="text-[0.8125rem] leading-snug text-[var(--ink)]">
                      {check.label_fr}
                    </p>
                    {check.reason_fr && (
                      <p className="mt-0.5 text-[0.75rem] leading-relaxed text-[var(--ink-muted)]">
                        {check.reason_fr}
                      </p>
                    )}
                  </div>
                  <span className="ms-auto shrink-0 text-[0.6875rem] font-medium" style={{ color: mark.color }}>
                    {mark.label}
                  </span>
                </li>
              );
            })}
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

      {shown && (
        <EvidenceViewer
          submissionId={result.submission_id}
          code={shown.code}
          title={shown.title}
          onClose={() => setShown(null)}
        />
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
