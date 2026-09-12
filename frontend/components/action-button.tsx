"use client";

import Link from "next/link";
import type { ReactNode } from "react";

/**
 * The primary action, everywhere.
 *
 * Deliberately a plain button. React Bits' SpecularButton was tried here and
 * removed: its effect is an edge rim designed for a transparent button on a
 * dark page, and on a filled button in a light palette it was never visible
 * enough to justify a WebGL context per button.
 *
 * What is left is a solid fill that deepens on press and hover. One treatment,
 * used on every screen, so the buttons stop looking slightly different in each
 * place.
 */

type Variant = "primary" | "teal" | "ghost";

const VARIANTS: Record<Variant, string> = {
  // Navy is the product's structural colour and the default for an action.
  primary:
    "bg-[var(--navy)] text-white hover:bg-[var(--navy-deep)] active:bg-[var(--navy-deep)]",
  // Teal is reserved for the one action on a navy surface, where navy would
  // disappear into the background.
  teal: "bg-[var(--teal)] text-white hover:bg-[var(--teal-ink)] active:bg-[var(--teal-ink)]",
  ghost:
    "border border-white/25 bg-white/8 text-white hover:border-white/45 hover:bg-white/14",
};

const SIZES: Record<"sm" | "md" | "lg", string> = {
  sm: "text-[0.875rem] px-4 py-2.5",
  md: "text-[0.9375rem] px-5 py-3",
  lg: "text-[1rem] px-6 py-3.5",
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
  const shell = [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-semibold",
    "transition-colors duration-150 active:translate-y-px",
    SIZES[size],
    disabled
      ? "cursor-not-allowed bg-[var(--line-strong)] text-[var(--ink-faint)]"
      : VARIANTS[variant],
    className,
  ].join(" ");

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
