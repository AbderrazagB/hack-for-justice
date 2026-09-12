import Link from "next/link";
import type { ReactNode } from "react";

import { Logo } from "@/components/logo";

/**
 * Portal chrome for the public entry: a thin navy utility strip above the white
 * bar, echoing the layout of the registry portal an applicant already knows.
 * Carries Sahilli's own wordmark only — no state emblem, no flag, no RNE logo.
 */
export function PortalBar({ immersive = false }: { immersive?: boolean }) {
  const linkClass = immersive
    ? "text-white/70 hover:bg-white/8 hover:text-white"
    : "text-[var(--ink-muted)] hover:bg-[var(--canvas)] hover:text-[var(--navy)]";

  return (
    <>
      <div className="relative z-30 bg-[var(--navy-deep)]">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-2 px-4 py-2.5 text-[0.75rem] text-white/60 sm:px-8">
          <span>Pré-validation des dossiers du Registre National des Entreprises</span>
          <span className="ar">التحقق المسبق من ملفات السجل الوطني للمؤسسات</span>
        </div>
      </div>
      <header
        className={`relative z-30 border-b backdrop-blur-xl ${
          immersive
            ? "border-white/10 bg-[var(--navy)]/90"
            : "border-[var(--line)] bg-[var(--surface)]"
        }`}
      >
        <nav className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8">
          <Logo size="md" tone={immersive ? "dark" : "light"} />
          <div className="flex items-center gap-1">
            <Link
              href="/msme"
              className={`rounded-[var(--r-control)] px-3 py-1.5 text-[0.875rem] font-medium transition-colors ${linkClass}`}
            >
              Services
            </Link>
            <Link
              href="/admin"
              className={`rounded-[var(--r-control)] px-3 py-1.5 text-[0.875rem] font-medium transition-colors ${linkClass}`}
            >
              Espace agent
            </Link>
          </div>
        </nav>
      </header>
    </>
  );
}

/** Navy chrome, used for the officer workspace. */
export function AdminBar({ trailing }: { trailing?: ReactNode }) {
  return (
    <header className="on-navy bg-[var(--navy)]">
      <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8">
        <Logo size="md" tone="dark" />
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
