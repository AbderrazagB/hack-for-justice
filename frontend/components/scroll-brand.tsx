"use client";

import { useEffect, useState } from "react";

import { Logo } from "@/components/logo";

/**
 * The nav wordmark on the landing page.
 *
 * The hero already states the brand at full size directly beneath the bar, so
 * repeating the same lockup in the nav reads as a duplicate rather than as
 * navigation. This keeps the nav slot empty while the hero is on screen and
 * fades the wordmark in once you have scrolled past it — the point at which a
 * way back to the top actually becomes useful.
 *
 * The slot keeps its space at all times so revealing the wordmark never shifts
 * the nav links.
 */
export function ScrollRevealBrand({ watchId }: { watchId: string }) {
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const sentinel = document.getElementById(watchId);
    if (!sentinel) return;

    // IntersectionObserver fires once on observe, so the initial state settles
    // itself without a synchronous setState during the effect.
    const observer = new IntersectionObserver(
      ([entry]) => setRevealed(!entry.isIntersecting),
      { threshold: 0 },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [watchId]);

  return (
    <span
      className={`inline-flex transition-opacity duration-300 ${
        revealed ? "opacity-100" : "pointer-events-none opacity-0"
      }`}
      aria-hidden={!revealed}
    >
      <Logo size="md" tone="dark" />
    </span>
  );
}
