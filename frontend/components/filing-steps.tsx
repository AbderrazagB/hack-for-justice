"use client";

import { Check } from "lucide-react";

export type FilingStep = {
  key: string;
  label_fr: string;
  label_ar: string;
};

/**
 * The filing, broken into steps.
 *
 * It used to be one page: the context questions, then nine declaration
 * questions, then five upload slots, then the verdict -- roughly four screens
 * of scrolling before anything happened. Splitting it is not decoration; it is
 * what makes the order legible, since the steps genuinely depend on each other
 * (the legal form decides which documents are owed, the declaration is what the
 * documents are checked against).
 *
 * Steps already reached stay clickable, so going back to fix an answer never
 * means walking forward through the others again.
 */
export function FilingSteps({
  steps,
  current,
  furthest,
  onSelect,
}: {
  steps: FilingStep[];
  current: number;
  furthest: number;
  onSelect: (index: number) => void;
}) {
  return (
    <nav aria-label="Étapes de la démarche">
      <p className="t-label mb-2 text-[var(--ink-muted)] sm:hidden">
        Étape {current + 1} sur {steps.length}
        <span className="text-[var(--ink)]"> — {steps[current]?.label_fr}</span>
      </p>

      <ol className="flex items-center">
        {steps.map((step, index) => {
          const done = index < furthest;
          const active = index === current;
          const reachable = index <= furthest;

          return (
            <li key={step.key} className="flex min-w-0 flex-1 items-center last:flex-none">
              <button
                type="button"
                onClick={() => reachable && onSelect(index)}
                disabled={!reachable}
                aria-current={active ? "step" : undefined}
                className={`flex min-w-0 items-center gap-2 rounded-[var(--r-control)] px-1 py-1 text-left transition-colors ${
                  reachable ? "hover:bg-[var(--surface)]" : "cursor-default"
                }`}
              >
                <span
                  aria-hidden
                  className={`flex size-7 shrink-0 items-center justify-center rounded-full text-[0.75rem] font-semibold transition-colors ${
                    active
                      ? "bg-[var(--navy)] text-white ring-4 ring-[var(--teal-wash)]"
                      : done
                        ? "bg-[var(--navy)] text-white"
                        : "border border-[var(--line-strong)] bg-[var(--surface)] text-[var(--ink-faint)]"
                  }`}
                >
                  {done ? <Check size={14} strokeWidth={2.6} /> : index + 1}
                </span>
                <span className="hidden min-w-0 sm:block">
                  <span
                    className={`block truncate text-[0.8125rem] font-medium ${
                      active
                        ? "text-[var(--navy)]"
                        : done
                          ? "text-[var(--ink)]"
                          : "text-[var(--ink-faint)]"
                    }`}
                  >
                    {step.label_fr}
                  </span>
                  <span className="ar ar-left block truncate text-[0.6875rem] text-[var(--ink-faint)]">
                    {step.label_ar}
                  </span>
                </span>
              </button>

              {index < steps.length - 1 && (
                <span
                  aria-hidden
                  className={`mx-2 h-px min-w-4 flex-1 ${
                    done ? "bg-[var(--navy)]" : "bg-[var(--line)]"
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
