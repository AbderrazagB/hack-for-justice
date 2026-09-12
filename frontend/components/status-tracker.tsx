import type { SubmissionStatus } from "@/lib/types";

/**
 * Submitted -> Pre-Validated -> Under Institutional Review -> outcome.
 *
 * The three outcomes share the final step: whichever one a submission reached
 * is shown there, so the tracker stays a straight line rather than branching.
 */
const STEPS: { key: string; fr: string; ar: string }[] = [
  { key: "SUBMITTED", fr: "Déposé", ar: "تم الإيداع" },
  { key: "PRE_VALIDATED", fr: "Pré-validé", ar: "تحقق أولي" },
  { key: "UNDER_INSTITUTIONAL_REVIEW", fr: "Examen RNE", ar: "قيد الدرس" },
  { key: "OUTCOME", fr: "Décision", ar: "القرار" },
];

const OUTCOMES: Record<string, { fr: string; ar: string; tone: string }> = {
  APPROVED: { fr: "Approuvé", ar: "مقبول", tone: "var(--success)" },
  REJECTED: { fr: "Rejeté", ar: "مرفوض", tone: "var(--danger)" },
  NEEDS_CORRECTION: { fr: "À corriger", ar: "يتطلب تصحيحاً", tone: "var(--accent)" },
};

function reachedIndex(status: SubmissionStatus): number {
  if (status in OUTCOMES) return 3;
  return STEPS.findIndex((step) => step.key === status);
}

export function StatusTracker({ status }: { status: SubmissionStatus }) {
  const reached = reachedIndex(status);
  const outcome = OUTCOMES[status];

  return (
    <ol className="flex flex-wrap items-stretch gap-2">
      {STEPS.map((step, index) => {
        const done = index <= reached;
        const current = index === reached;
        const isOutcome = step.key === "OUTCOME";
        const tone = isOutcome && outcome ? outcome.tone : "var(--brand)";

        return (
          <li
            key={step.key}
            className="min-w-[7.5rem] flex-1 rounded-lg border px-3 py-2.5"
            style={{
              borderColor: done ? tone : "var(--border)",
              background: current ? "var(--brand-soft)" : "transparent",
              opacity: done ? 1 : 0.45,
            }}
            aria-current={current ? "step" : undefined}
          >
            <div className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="inline-block size-1.5 rounded-full"
                style={{ background: done ? tone : "var(--border)" }}
              />
              <span className="text-xs font-semibold">
                {isOutcome && outcome ? outcome.fr : step.fr}
              </span>
            </div>
            <span className="ar mt-0.5 block text-[11px] opacity-60">
              {isOutcome && outcome ? outcome.ar : step.ar}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
