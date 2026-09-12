"use client";

import CountUp from "@/components/CountUp";
import { useReducedMotion } from "@/components/motion";

/**
 * The officer dashboard's figures, set directly on the navy masthead — no cards,
 * hairline rules only. Glanceable data, which is a different job from the queue
 * below it and therefore a different object.
 *
 * This is /admin's single orchestrated moment: React Bits `CountUp` runs once on
 * load, so live figures announce themselves as live. Static when the user
 * prefers reduced motion.
 */

export type Figure = {
  label: string;
  value: number;
  /** Rendered after the counted number, e.g. "%" or " s". */
  suffix?: string;
  /** Shown instead of the number when there is nothing to count yet. */
  placeholder?: string;
  hint?: string;
  decimals?: number;
};

export function StatBand({ figures }: { figures: Figure[] }) {
  return (
    <dl className="grid grid-cols-2 gap-px bg-white/10 lg:grid-cols-4">
      {figures.map((figure) => (
        <div key={figure.label} className="bg-[var(--navy)] px-4 py-5 sm:px-5">
          <dd className="t-stat text-white">
            <FigureValue figure={figure} />
          </dd>
          <dt className="mt-1.5 text-[0.75rem] font-medium text-white/70">
            {figure.label}
          </dt>
          {figure.hint && (
            <p className="mt-0.5 text-[0.6875rem] text-white/45">{figure.hint}</p>
          )}
        </div>
      ))}
    </dl>
  );
}

function FigureValue({ figure }: { figure: Figure }) {
  const reduced = useReducedMotion();

  if (figure.placeholder) {
    return <span className="text-white/35">{figure.placeholder}</span>;
  }

  const rendered = figure.decimals
    ? figure.value.toFixed(figure.decimals)
    : String(figure.value);

  if (reduced) {
    return (
      <>
        {rendered}
        {figure.suffix}
      </>
    );
  }

  return (
    <>
      <CountUp to={figure.value} duration={1.1} separator=" " />
      {figure.suffix}
    </>
  );
}
