"use client";

import DotGrid from "@/components/DotGrid";
import { useReducedMotion } from "@/components/motion";

/**
 * React Bits `DotGrid` behind the service grid: a quiet registry-paper texture
 * that reacts to the cursor. Static (rendered as nothing) under reduced motion.
 */
export function DotField() {
  if (useReducedMotion()) return null;

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0">
      <DotGrid
        dotSize={3.5}
        gap={30}
        baseColor="#CBD6E2"
        activeColor="#15ADA2"
        proximity={110}
        shockRadius={200}
        shockStrength={4}
        returnDuration={1.4}
      />
    </div>
  );
}
