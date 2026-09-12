"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import type { MouseEvent, ReactNode } from "react";

import SpecularButton from "@/components/SpecularButton";
import { useReducedMotion } from "@/components/motion";

/**
 * The primary action, everywhere.
 *
 * Wraps React Bits' `SpecularButton` so the whole product shares one button
 * treatment instead of each screen inventing its own hover transition. The
 * specular sheen replaces the translate-on-hover the buttons used to do.
 *
 * It is WebGL, so it never mounts under prefers-reduced-motion: the fallback is
 * the same button, same colours, same geometry, without the sheen. Navigation
 * actions render as a real anchor, not a button that pushes a route.
 */

type Variant = "primary" | "navy" | "ghost";

/**
 * SpecularButton's shader draws an edge stroke and a rim highlight only -- its
 * `base` term is non-zero just around the boundary. `baseColor` is therefore
 * the edge colour, NOT a fill, and the button's actual background comes from
 * `tint` x `tintOpacity`.
 *
 * The upstream example ships `tintOpacity: 0`, which is a transparent button
 * carrying only a rim. That reads on a dark showcase page and disappears on
 * our light surfaces, so every solid variant sets its own fill here.
 */
const VARIANTS: Record<
  Variant,
  { fill: string; fillOpacity: number; edge: string; text: string; line: string }
> = {
  primary: {
    fill: "#15ADA2",
    fillOpacity: 1,
    edge: "#0B6E68",
    text: "#ffffff",
    line: "#eafffb",
  },
  navy: {
    fill: "#0E2747",
    fillOpacity: 1,
    edge: "#081A31",
    text: "#ffffff",
    line: "#7fd0c6",
  },
  // Deliberately translucent: this one sits on the navy hero and is meant to
  // read as secondary.
  ghost: {
    fill: "#ffffff",
    fillOpacity: 0.1,
    edge: "#ffffff",
    text: "#ffffff",
    line: "#ffffff",
  },
};

const FALLBACK: Record<Variant, string> = {
  primary: "bg-[var(--teal)] text-white hover:bg-[var(--teal-ink)]",
  navy: "bg-[var(--navy)] text-white hover:bg-[var(--navy-deep)]",
  ghost: "border border-white/25 text-white hover:bg-white/10",
};

/**
 * Must match SpecularButton's own SIZES exactly. The server renders the
 * fallback and the specular version mounts after hydration, so any difference
 * here shows up as the button resizing on load.
 */
const PADDING: Record<"sm" | "md" | "lg", string> = {
  sm: "text-[0.85rem] px-[22px] py-[10px]",
  md: "text-[1rem] px-[30px] py-[14px]",
  lg: "text-[1.15rem] px-10 py-[18px]",
};

export function ActionButton({
  children,
  href,
  onClick,
  type = "button",
  variant = "primary",
  size = "md",
  disabled,
  className = "",
}: {
  children: ReactNode;
  href?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
  className?: string;
}) {
  const router = useRouter();
  const reduced = useReducedMotion();
  const tone = VARIANTS[variant];

  /**
   * The animated path renders a real <a>, which would otherwise trigger a full
   * page load. Intercept a plain left-click for client-side navigation while
   * leaving middle-click, ctrl-click and "open in new tab" to the browser.
   */
  function navigate(event: MouseEvent<HTMLElement>) {
    if (!href) return;
    if (
      event.defaultPrevented ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey ||
      event.button !== 0
    ) {
      return;
    }
    event.preventDefault();
    router.push(href);
  }

  // A disabled control must not look interactive, so the sheen is dropped too.
  if (reduced || disabled) {
    const shell = `inline-flex items-center justify-center gap-2 rounded-[14px] leading-none font-medium tracking-[0.01em] transition-colors ${PADDING[size]} ${
      disabled
        ? "cursor-not-allowed bg-[var(--line-strong)] text-[var(--ink-faint)]"
        : FALLBACK[variant]
    } ${className}`;

    if (href && !disabled) {
      return (
        <Link href={href} className={shell}>
          {children}
        </Link>
      );
    }
    return (
      <button type={type} onClick={onClick} disabled={disabled} className={shell}>
        {children}
      </button>
    );
  }

  return (
    <SpecularButton
      href={href}
      type={type}
      onClick={href ? navigate : onClick}
      size={size}
      radius={14}
      baseColor={tone.edge}
      textColor={tone.text}
      lineColor={tone.line}
      tint={tone.fill}
      tintOpacity={tone.fillOpacity}
      blur={0}
      intensity={1}
      shineSize={10}
      shineFade={40}
      thickness={1}
      speed={0.35}
      followMouse
      proximity={250}
      autoAnimate={false}
      className={`gap-2 font-semibold ${className}`}
    >
      {children}
    </SpecularButton>
  );
}
