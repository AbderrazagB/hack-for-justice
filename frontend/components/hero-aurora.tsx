"use client";

import Aurora from "@/components/Aurora";
import { useReducedMotion } from "@/components/motion";

/**
 * React Bits `Aurora`, running behind the navy masthead in the product's own
 * teal. WebGL, so it only mounts on the client and never when the visitor has
 * asked for reduced motion — the navy behind it is the static fallback.
 */
export function HeroAurora() {
  if (useReducedMotion()) return null;

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 opacity-70">
      <Aurora colorStops={["#0E2747", "#15ADA2", "#0E2747"]} amplitude={0.9} blend={0.6} speed={0.4} />
    </div>
  );
}
