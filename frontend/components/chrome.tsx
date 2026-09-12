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

/**
 * Portal chrome for the public entry: a thin navy utility strip above the white
 * bar, echoing the layout of the registry portal an applicant already knows.
 * Carries Sahilli's own wordmark only — no state emblem, no flag, no RNE logo.
 */
export function PortalBar() {
  return (
    <>
      <div className="bg-[var(--navy-deep)]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-2 text-[0.75rem] text-white/60 sm:px-6">
          <span>Pré-validation des dossiers du Registre National des Entreprises</span>
          <span className="ar">التحقق المسبق من ملفات السجل الوطني للمؤسسات</span>
        </div>
      </div>
      <header className="border-b border-[var(--line)] bg-[var(--surface)]">
        <nav className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
          <Wordmark />
          <div className="flex items-center gap-1">
            <Link
              href="/msme"
              className="rounded-[var(--r-control)] px-3 py-1.5 text-[0.875rem] font-medium text-[var(--ink-muted)] transition-colors hover:bg-[var(--canvas)] hover:text-[var(--navy)]"
            >
              Services
            </Link>
            <Link
              href="/admin"
              className="rounded-[var(--r-control)] px-3 py-1.5 text-[0.875rem] font-medium text-[var(--ink-muted)] transition-colors hover:bg-[var(--canvas)] hover:text-[var(--navy)]"
            >
              Espace agent
            </Link>
          </div>
        </nav>
      </header>
    </>
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
