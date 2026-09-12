"use client";

import StrokeText from "@/components/StrokeText";

/**
 * The accent half of the hero headline.
 *
 * React Bits' `StrokeText` draws the phrase outline-first, then floods the
 * teal in with a left-to-right wipe -- so the one coloured element on the page
 * is also the one that animates, rather than a separate decorative widget.
 *
 * It renders measured SVG glyphs rather than live text, which has two
 * consequences worth knowing: the phrase becomes its own block line (it cannot
 * sit inline after "Vérifiez votre dossier"), and its size is driven by the
 * SVG's height rather than a font-size, so `.hero-accent` in globals.css ties
 * that height to the same clamp the headline uses.
 *
 * The component handles prefers-reduced-motion itself -- the only React Bits
 * piece here that does -- settling straight to the drawn-and-filled state.
 */
export function HeroAccent({ children }: { children: string }) {
  return (
    <StrokeText
      className="hero-accent"
      text={children}
      // Bright teal outline, brand teal flood: the draw reads on navy and the
      // settled state matches every other accent in the product.
      strokeColor="#7FE9DF"
      fillColor="#15ADA2"
      strokeWidth={1.1}
      drawDuration={1.1}
      fillDelay={0.15}
      stagger={0.035}
      ease="power2.out"
      trigger="mount"
      fillMode="wipe"
      // Measurement resolution only; the viewBox scales the result. Weight and
      // tracking mirror .hero-title so the two lines read as one headline.
      fontSize={128}
      fontWeight={600}
      letterSpacing={-6}
    />
  );
}
