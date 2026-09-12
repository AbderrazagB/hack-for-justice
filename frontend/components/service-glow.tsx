"use client";

import type { ReactNode } from "react";

import BorderGlow from "@/components/BorderGlow";
import { useReducedMotion } from "@/components/motion";

/**
 * The glow on an available service card.
 *
 * React Bits' `BorderGlow` in Sahilli's palette: the default ships a
 * purple/pink/sky mesh on a near-black surface, which belongs to nothing else
 * in this product. Retuned to teal and navy on white, and dialled down --
 * `glowIntensity` and `fillOpacity` below their defaults, because an effect
 * calibrated for a dark showcase page is far too strong on a light one.
 *
 * Replaces the hover-lift these cards used to do, so the movement is now the
 * light following the cursor rather than the card jumping.
 */
export function ServiceGlow({ children }: { children: ReactNode }) {
  const reduced = useReducedMotion();

  // Pointer-driven, so it has no meaning without a pointer and no place under
  // reduced motion. The fallback keeps the card's own border and surface.
  if (reduced) {
    return (
      <div className="h-full rounded-[22px] border border-[var(--teal)]/25 bg-[var(--surface)] shadow-[0_18px_45px_-38px_rgba(8,26,49,0.5)]">
        {children}
      </div>
    );
  }

  return (
    <BorderGlow
      className="h-full sahilli-glow-card"
      backgroundColor="#FFFFFF"
      // Our teal, hsl(176 78% 38%), lifted a little so the glow reads on white.
      glowColor="176 72% 45%"
      colors={["#15ADA2", "#0E2747", "#4FD1C5"]}
      borderRadius={22}
      edgeSensitivity={28}
      glowRadius={30}
      glowIntensity={0.65}
      fillOpacity={0.3}
      coneSpread={25}
      animated={false}
    >
      {children}
    </BorderGlow>
  );
}
