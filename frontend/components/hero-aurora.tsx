"use client";

import Image from "next/image";

import Aurora from "@/components/Aurora";
import { useReducedMotion } from "@/components/motion";

/**
 * Generated editorial artwork provides the static, meaningful atmosphere.
 * Aurora and the light sweep add a restrained video-like layer when motion is
 * allowed; reduced-motion visitors still receive the complete visual.
 */
export function HeroAurora() {
  const reduced = useReducedMotion();

  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <Image
        src="/brand/sahilli-hero-documents.png"
        alt=""
        fill
        preload
        sizes="100vw"
        className="hero-cinematic-image object-cover object-[64%_center]"
      />
      <div className="hero-cinematic-scrim absolute inset-0" />
      <div className="hero-cinematic-grid absolute inset-0" />

      {!reduced && (
        <>
          <div className="absolute inset-x-0 -top-1/2 h-full opacity-25 mix-blend-screen">
            <Aurora
              colorStops={["#0E2747", "#15ADA2", "#0E2747"]}
              amplitude={0.6}
              blend={0.7}
              speed={0.22}
            />
          </div>
          <div className="hero-light-sweep absolute inset-y-0 w-1/3" />
        </>
      )}

      <div className="hero-cinematic-vignette absolute inset-0" />
    </div>
  );
}
