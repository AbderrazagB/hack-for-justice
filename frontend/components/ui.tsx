import Link from "next/link";
import type { ReactNode } from "react";

import { SEVERITY, statusStyle } from "@/lib/status";
import type { CompletenessStatus, Severity, SubmissionStatus } from "@/lib/types";

/* --------------------------------------------------------------- surfaces --- */

/**
 * Structural surface: border and background only. Deliberately flat — shadow is
 * reserved for `FloatingPanel`, so elevation means "this floats", not "this is
 * a box". See docs/DESIGN.md section 6, item 3.
 */
export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] ${className}`}
    >
      {children}
    </div>
  );
}

/** The one surface allowed to cast a shadow: it genuinely floats above content. */
export function FloatingPanel({
  children,
  className = "",
  accent,
}: {
  children: ReactNode;
  className?: string;
  /** CSS colour for the 3px top edge, used to carry status. */
  accent?: string;
}) {
  return (
    <div
      className={`overflow-hidden rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(14,39,71,0.06),0_12px_28px_-12px_rgba(14,39,71,0.18)] ${className}`}
    >
      {accent && <div aria-hidden className="h-[3px] w-full" style={{ background: accent }} />}
      {children}
    </div>
  );
}

/* ------------------------------------------------------------------ text --- */

export function SectionHeading({
  children,
  hint,
  className = "",
}: {
  children: ReactNode;
  hint?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`mb-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 ${className}`}>
      <h2 className="t-h2">{children}</h2>
      {hint && <span className="t-meta">{hint}</span>}
    </div>
  );
}

/** A French line with its Arabic counterpart directly beneath, direction-isolated. */
export function Bilingual({
  fr,
  ar,
  className = "",
  arClassName = "",
}: {
  fr: string;
  ar: string;
  className?: string;
  arClassName?: string;
}) {
  return (
    <span className={className}>
      <span className="block">{fr}</span>
      <span className={`ar block text-[var(--ink-muted)] ${arClassName}`}>{ar}</span>
    </span>
  );
}

/* ---------------------------------------------------------------- status --- */

export function StatusBadge({
  status,
  size = "md",
}: {
  status: SubmissionStatus | CompletenessStatus | string;
  size?: "sm" | "md";
}) {
  const style = statusStyle(status);
  const Icon = style.icon;
  const compact = size === "sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-[var(--r-control)] font-medium whitespace-nowrap ${
        compact ? "px-2 py-0.5 text-[0.75rem]" : "px-2.5 py-1 text-[0.8125rem]"
      }`}
      style={{ background: style.wash, color: style.ink }}
    >
      <Icon size={compact ? 12 : 14} strokeWidth={2.25} aria-hidden />
      {style.fr}
    </span>
  );
}

export function SeverityTag({ severity }: { severity: Severity }) {
  const tone = SEVERITY[severity];
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-[var(--r-control)] px-1.5 py-0.5 text-[0.6875rem] font-semibold"
      style={{ background: tone.wash, color: tone.ink }}
    >
      {tone.fr}
    </span>
  );
}

/* --------------------------------------------------------------- controls --- */

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  // The single teal element per screen. Scarcity is the system.
  primary:
    "bg-[var(--teal)] text-white hover:bg-[var(--teal-ink)] disabled:bg-[var(--line-strong)] disabled:text-[var(--ink-faint)]",
  secondary:
    "border border-[var(--line-strong)] bg-[var(--surface)] text-[var(--ink)] hover:border-[var(--ink-faint)] hover:bg-[var(--canvas)] disabled:text-[var(--ink-faint)]",
  ghost:
    "text-[var(--ink-muted)] hover:bg-[var(--canvas)] hover:text-[var(--ink)]",
  danger:
    "border border-[var(--st-rejected-ink)] text-[var(--st-rejected-ink)] hover:bg-[var(--st-rejected-wash)]",
};

export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  type = "button",
  className = "",
  icon: Icon,
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: ButtonVariant;
  type?: "button" | "submit";
  className?: string;
  icon?: React.ComponentType<{ size?: number; strokeWidth?: number }>;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-[var(--r-control)] px-4 py-2.5 text-[0.875rem] font-medium transition-colors duration-150 disabled:cursor-not-allowed ${BUTTON_STYLES[variant]} ${className}`}
    >
      {Icon && <Icon size={16} strokeWidth={2} />}
      {children}
    </button>
  );
}

export function TextLink({
  href,
  children,
  icon: Icon,
  className = "",
}: {
  href: string;
  children: ReactNode;
  icon?: React.ComponentType<{ size?: number; strokeWidth?: number }>;
  className?: string;
}) {
  return (
    <Link
      href={href}
      className={`inline-flex items-center gap-1.5 text-[0.875rem] font-medium text-[var(--teal-ink)] hover:underline ${className}`}
    >
      {Icon && <Icon size={15} strokeWidth={2} />}
      {children}
    </Link>
  );
}

/* ------------------------------------------------------------------ notes --- */

export function Notice({
  children,
  tone = "error",
}: {
  children: ReactNode;
  tone?: "error" | "info";
}) {
  const style =
    tone === "error"
      ? { background: "var(--st-rejected-wash)", color: "var(--st-rejected-ink)" }
      : { background: "var(--teal-wash)", color: "var(--teal-ink)" };

  return (
    <div
      role={tone === "error" ? "alert" : undefined}
      className="rounded-[var(--r-control)] px-4 py-3 text-[0.875rem]"
      style={style}
    >
      {children}
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="rounded-[var(--r-panel)] border border-dashed border-[var(--line-strong)] px-6 py-12 text-center">
      <p className="t-h3">{title}</p>
      {children && (
        <p className="mx-auto mt-2 max-w-md text-[0.875rem] text-[var(--ink-muted)]">
          {children}
        </p>
      )}
    </div>
  );
}
