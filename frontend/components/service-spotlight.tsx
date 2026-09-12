"use client";

import type { ReactNode } from "react";

import SpotlightCard from "@/components/SpotlightCard";
import { useReducedMotion } from "@/components/motion";

/**
 * React Bits `SpotlightCard`, used exactly once: on the single live procedure.
 *
 * This is the hierarchy device for /msme — the one available service is the only
 * object on the page that responds to the cursor, which is why the "coming soon"
 * rows below do not get it. Falls back to a plain bordered panel when the user
 * prefers reduced motion.
 */
export function ServiceSpotlight({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();

  const shell =
    "mt-8 overflow-hidden rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)]";

  if (reduced) {
    return <div className={shell}>{children}</div>;
  }

  return (
    <SpotlightCard
      className={shell}
      spotlightColor="rgba(21, 173, 162, 0.16)"
    >
      {children}
    </SpotlightCard>
  );
}
