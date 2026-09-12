"use client";

import type { ReactNode } from "react";

import GradientText from "@/components/GradientText";
import { useReducedMotion } from "@/components/motion";

/**
 * The accent half of the hero headline.
 *
 * React Bits `GradientText` drifts a teal gradient across the phrase, so the
 * one coloured element on the page carries the movement rather than a separate
 * decorative widget. Falls back to flat teal under reduced motion.
 */
export function HeroAccent({ children }: { children: ReactNode }) {
  if (useReducedMotion()) {
    return <span className="text-[var(--teal)]">{children}</span>;
  }

  return (
    <GradientText
      // inline-block keeps the phrase as one unit: background-clip:text on a
      // wrapped inline box renders the gradient per line-fragment, which looks
      // broken mid-headline.
      className="inline-block align-baseline"
      colors={["#15ADA2", "#7FE9DF", "#15ADA2", "#4FD1C5", "#15ADA2"]}
      animationSpeed={7}
      direction="horizontal"
    >
      {children}
    </GradientText>
  );
}
