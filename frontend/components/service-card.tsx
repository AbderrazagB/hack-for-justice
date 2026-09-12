"use client";

import {
  ArrowLeft,
  Building2,
  FileCheck2,
  FileSearch,
  Files,
  ScrollText,
  ShieldCheck,
  UserRoundCog,
  Users,
} from "lucide-react";
import Link from "next/link";

/**
 * Icons are selected by name rather than passed as components: these cards are
 * rendered from Server Components, and React cannot serialise a function across
 * that boundary.
 */
const ICONS = {
  modification: UserRoundCog,
  immatriculation: Building2,
  financials: Files,
  denomination: ScrollText,
  assembly: Users,
  extract: FileSearch,
  beneficiary: FileCheck2,
  cessation: ShieldCheck,
} as const;

export type ServiceIcon = keyof typeof ICONS;

/**
 * Service card, matching the registry portal's own pattern: outlined icon,
 * Arabic title above the French one, and a wide teal pill carrying both
 * languages.
 *
 * Available and unavailable cards share the pattern but not the weight — an
 * unavailable one loses its shadow and its pill, so the grid still tells you
 * where you can actually go.
 */
export function ServiceCard({
  icon,
  titleAr,
  titleFr,
  href,
  reference,
}: {
  icon: ServiceIcon;
  titleAr: string;
  titleFr: string;
  href?: string;
  reference?: string;
}) {
  const Icon = ICONS[icon];
  const available = Boolean(href);

  const body = (
    <>
      <span
        className={`flex h-11 items-start justify-center ${
          available ? "text-[var(--teal-ink)]" : "text-[var(--ink-faint)]"
        }`}
      >
        <Icon size={30} strokeWidth={1.4} aria-hidden />
      </span>

      <h3
        className={`ar mt-3 text-center text-[1.0625rem] font-semibold ${
          available ? "text-[var(--navy)]" : "text-[var(--ink-muted)]"
        }`}
      >
        {titleAr}
      </h3>
      <p
        className={`mt-1 text-center text-[0.9375rem] ${
          available ? "text-[var(--ink)]" : "text-[var(--ink-muted)]"
        }`}
      >
        {titleFr}
      </p>

      {reference && (
        <p className="t-data mt-1.5 text-center text-[var(--ink-faint)]">
          {reference}
        </p>
      )}

      <span className="mt-auto w-full pt-5">
        {available ? (
          <span className="flex w-full items-center justify-center gap-2 rounded-full bg-[var(--teal)] px-4 py-2.5 text-[0.875rem] font-medium text-white transition-colors group-hover:bg-[var(--teal-ink)]">
            <ArrowLeft size={16} strokeWidth={2} aria-hidden />
            <span>Accès au service</span>
            <span aria-hidden className="text-white/50">/</span>
            <span className="ar">الولوج الى الخدمة</span>
          </span>
        ) : (
          <span className="flex w-full items-center justify-center rounded-full border border-dashed border-[var(--line-strong)] px-4 py-2.5 text-[0.8125rem] text-[var(--ink-faint)]">
            Bientôt disponible
          </span>
        )}
      </span>
    </>
  );

  const shell =
    "group flex h-full flex-col rounded-2xl border px-5 pt-6 pb-5 transition-all duration-200";

  if (!available) {
    return (
      <div
        aria-disabled
        className={`${shell} border-[var(--line)] bg-[var(--surface)]/60`}
      >
        {body}
      </div>
    );
  }

  return (
    <Link
      href={href!}
      className={`${shell} border-transparent bg-[var(--surface)] shadow-[0_1px_2px_rgba(14,39,71,0.05),0_10px_28px_-14px_rgba(14,39,71,0.28)] hover:-translate-y-1 hover:shadow-[0_2px_4px_rgba(14,39,71,0.06),0_18px_40px_-16px_rgba(21,173,162,0.45)]`}
    >
      {body}
    </Link>
  );
}
