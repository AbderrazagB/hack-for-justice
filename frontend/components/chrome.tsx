import Link from "next/link";
import type { ReactNode } from "react";

/** The wordmark. Type-only: no logo image, no emblem, no emoji. */
export function Wordmark({ tone = "light" }: { tone?: "light" | "dark" }) {
  const color = tone === "dark" ? "text-white" : "text-[var(--navy)]";
  const mark = tone === "dark" ? "bg-[var(--teal)]" : "bg-[var(--teal)]";

  return (
    <Link href="/" className="group inline-flex items-center gap-2.5">
      {/* A 3px teal stroke stands in for a logo: structural, not pictorial. */}
      <span aria-hidden className={`h-6 w-[3px] rounded-full ${mark}`} />
      <span className="flex items-baseline gap-2">
        <span
          className={`font-[family-name:var(--font-space-grotesk)] text-[1.0625rem] font-semibold tracking-[-0.01em] ${color}`}
        >
          Sahilli
        </span>
        <span
          className={`ar text-[0.9375rem] ${tone === "dark" ? "text-white/55" : "text-[var(--ink-faint)]"}`}
        >
          سهّلي
        </span>
      </span>
    </Link>
  );
}

/** Light chrome, used on the applicant-facing screens. */
export function AppBar({ trailing }: { trailing?: ReactNode }) {
  return (
    <header className="border-b border-[var(--line)] bg-[var(--surface)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
        <Wordmark />
        {trailing}
      </div>
    </header>
  );
}

/** Navy chrome, used for the officer workspace. */
export function AdminBar({ trailing }: { trailing?: ReactNode }) {
  return (
    <header className="on-navy bg-[var(--navy)]">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
        <Wordmark tone="dark" />
        <div className="flex items-center gap-3">
          <span className="rounded-[var(--r-control)] border border-white/15 px-2.5 py-1 text-[0.75rem] font-medium text-white/75">
            Espace agent
          </span>
          {trailing}
        </div>
      </div>
    </header>
  );
}
