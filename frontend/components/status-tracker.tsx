import { SUBMISSION_STATUS } from "@/lib/status";
import type { SubmissionStatus } from "@/lib/types";

/**
 * Submitted -> Pre-Validated -> Under Institutional Review -> Decision.
 *
 * The three terminal states share the final step: whichever one a dossier
 * reached is shown there with its own colour, so the tracker stays a straight
 * line instead of branching.
 */
const STEPS = [
  { key: "SUBMITTED", fr: "Déposé", ar: "تم الإيداع" },
  { key: "PRE_VALIDATED", fr: "Pré-validé", ar: "تحقق أولي" },
  { key: "UNDER_INSTITUTIONAL_REVIEW", fr: "Examen RNE", ar: "قيد الدرس" },
  { key: "DECISION", fr: "Décision", ar: "القرار" },
] as const;

const TERMINAL = new Set(["APPROVED", "REJECTED", "NEEDS_CORRECTION"]);

export function StatusTracker({ status }: { status: SubmissionStatus }) {
  const reached = TERMINAL.has(status)
    ? STEPS.length - 1
    : STEPS.findIndex((step) => step.key === status);

  const terminal = TERMINAL.has(status) ? SUBMISSION_STATUS[status] : null;

  return (
    <ol
      className="grid grid-cols-2 gap-x-2 gap-y-4 sm:grid-cols-4 sm:gap-1.5"
      aria-label="Avancement du dossier"
    >
      {STEPS.map((step, index) => {
        const done = index <= reached;
        const current = index === reached;
        const isFinal = step.key === "DECISION";
        const tone = isFinal && terminal ? terminal.ink : "var(--teal-ink)";

        return (
          <li
            key={step.key}
            aria-current={current ? "step" : undefined}
            className="min-w-0 border-t-2 pt-2"
            style={{
              borderColor: done ? tone : "var(--line)",
            }}
          >
            <span
              className="block text-[0.8125rem] font-medium"
              style={{ color: done ? tone : "var(--ink-faint)" }}
            >
              {isFinal && terminal ? terminal.fr : step.fr}
            </span>
            <span
              className="ar block text-[0.6875rem]"
              style={{ color: done ? "var(--ink-muted)" : "var(--ink-faint)" }}
            >
              {isFinal && terminal ? terminal.ar : step.ar}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
