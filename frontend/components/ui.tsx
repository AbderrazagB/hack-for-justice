import Link from "next/link";
import type { ReactNode } from "react";

import type { CompletenessStatus, Severity, SubmissionStatus } from "@/lib/types";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-xl border border-[var(--border)] bg-[var(--surface)] ${className}`}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  children,
  hint,
}: {
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-lg font-semibold">{children}</h2>
      {hint && <span className="text-sm opacity-60">{hint}</span>}
    </div>
  );
}

const STATUS_STYLES: Record<string, string> = {
  SUBMITTED: "bg-[var(--surface-muted)] text-[var(--foreground)]",
  PRE_VALIDATED: "bg-[var(--brand-soft)] text-[var(--brand-strong)]",
  UNDER_INSTITUTIONAL_REVIEW: "bg-[var(--accent-soft)] text-[var(--accent)]",
  APPROVED: "bg-[var(--success-soft)] text-[var(--success)]",
  REJECTED: "bg-[var(--danger-soft)] text-[var(--danger)]",
  NEEDS_CORRECTION: "bg-[var(--accent-soft)] text-[var(--accent)]",
  COMPLETE: "bg-[var(--success-soft)] text-[var(--success)]",
  INCOMPLETE: "bg-[var(--danger-soft)] text-[var(--danger)]",
  NEEDS_REVIEW: "bg-[var(--accent-soft)] text-[var(--accent)]",
};

export const STATUS_LABELS_FR: Record<string, string> = {
  SUBMITTED: "Déposé",
  PRE_VALIDATED: "Pré-validé",
  UNDER_INSTITUTIONAL_REVIEW: "En cours d'examen",
  APPROVED: "Approuvé",
  REJECTED: "Rejeté",
  NEEDS_CORRECTION: "À corriger",
  COMPLETE: "Complet",
  INCOMPLETE: "Incomplet",
  NEEDS_REVIEW: "À vérifier",
};

export function StatusBadge({
  status,
}: {
  status: SubmissionStatus | CompletenessStatus | string;
}) {
  const style = STATUS_STYLES[status] ?? "bg-[var(--surface-muted)]";
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-semibold ${style}`}
    >
      {STATUS_LABELS_FR[status] ?? status}
    </span>
  );
}

export function SeverityDot({ severity }: { severity: Severity }) {
  const color =
    severity === "ERROR"
      ? "var(--danger)"
      : severity === "WARNING"
        ? "var(--accent)"
        : "var(--brand)";
  return (
    <span
      aria-hidden
      className="mt-1.5 inline-block size-2 shrink-0 rounded-full"
      style={{ background: color }}
    />
  );
}

export function Button({
  children,
  onClick,
  disabled,
  variant = "primary",
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
  type?: "button" | "submit";
  className?: string;
}) {
  const styles = {
    primary:
      "bg-[var(--brand)] text-white hover:bg-[var(--brand-strong)] disabled:opacity-50",
    secondary:
      "border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] disabled:opacity-50",
    danger:
      "bg-[var(--danger)] text-white hover:opacity-90 disabled:opacity-50",
  }[variant];

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`rounded-lg px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Header({ trailing }: { trailing?: ReactNode }) {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--surface)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-5 py-4">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="text-xl font-bold tracking-tight text-[var(--brand)]">
            Sahilli
          </span>
          <span className="ar text-lg text-[var(--brand)] opacity-70">سهّلي</span>
        </Link>
        {trailing}
      </div>
    </header>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]">
      {children}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-[var(--border)] px-6 py-12 text-center text-sm opacity-70">
      {children}
    </div>
  );
}
