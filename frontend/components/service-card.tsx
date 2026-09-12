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

import { ServiceGlow } from "@/components/service-glow";

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
      {available && (
        <span
          aria-hidden
          className="absolute -top-20 -right-20 size-44 rounded-full bg-[var(--teal)]/10 blur-3xl transition-transform duration-500 group-hover:scale-125"
        />
      )}

      <span className="relative flex items-start justify-between">
        <span
          className={`flex size-12 items-center justify-center rounded-[14px] ring-1 ${
            available
              ? "bg-[var(--teal-wash)] text-[var(--teal-ink)] ring-[var(--teal)]/18"
              : "bg-[var(--canvas)] text-[var(--ink-faint)] ring-[var(--line)]"
          }`}
        >
          <Icon size={25} strokeWidth={1.55} aria-hidden />
        </span>
        <span
          className={`rounded-full px-2.5 py-1 text-[0.625rem] font-semibold tracking-[0.08em] uppercase ${
            available
              ? "bg-[var(--teal-wash)] text-[var(--teal-ink)]"
              : "bg-[var(--canvas)] text-[var(--ink-faint)]"
          }`}
        >
          {available ? "Disponible" : "Bientôt"}
        </span>
      </span>

      {/* Both titles sit in a fixed-height block so every card in the row has
          its pill on the same baseline, whatever the title wraps to. */}
      <span className="relative mt-7 flex min-h-[5.75rem] flex-col items-start justify-start">
        <h3
          className={`ar ar-left text-[1.0625rem] leading-snug font-semibold ${
            available ? "text-[var(--navy)]" : "text-[var(--ink-muted)]"
          }`}
        >
          {titleAr}
        </h3>
        <p
          className={`mt-1.5 text-left text-[0.9375rem] leading-snug ${
            available ? "text-[var(--ink)]" : "text-[var(--ink-muted)]"
          }`}
        >
          {titleFr}
        </p>
        <span className="t-data mt-2 block text-left text-[var(--ink-faint)]">
          {reference ?? "\u00A0"}
        </span>
      </span>

      <span className="relative mt-auto w-full pt-5">
        {available ? (
          <span className="flex w-full items-center justify-center gap-2 rounded-xl bg-[var(--navy)] px-3 py-3 text-white shadow-[0_10px_24px_-14px_rgba(8,26,49,0.8)] transition-all group-hover:bg-[var(--teal-ink)]">
            <ArrowLeft size={15} strokeWidth={2} className="shrink-0" aria-hidden />
            <span className="text-[0.875rem] font-medium whitespace-nowrap">
              Accès au service
            </span>
            <span aria-hidden className="text-white/40">
              |
            </span>
            <span className="ar text-[0.875rem] font-medium whitespace-nowrap">
              الولوج الى الخدمة
            </span>
          </span>
        ) : (
          <span className="flex w-full items-center justify-between border-t border-[var(--line)] pt-4 text-[0.75rem] text-[var(--ink-faint)]">
            <span>Prochainement</span>
            <span aria-hidden>—</span>
          </span>
        )}
      </span>
    </>
  );

  const inner =
    "group relative flex min-h-[292px] h-full flex-col px-5 pt-5 pb-5";

  // Unavailable services get no glow: the effect is an affordance, and giving
  // it to a card you cannot open would be a lie about where the page goes.
  if (!available) {
    return (
      <div
        aria-disabled
        className={`${inner} rounded-[22px] border border-[var(--line)] bg-[var(--surface)]/72 backdrop-blur-sm`}
      >
        {body}
      </div>
    );
  }

  return (
    <ServiceGlow>
      <Link href={href!} className={inner}>
        {body}
      </Link>
    </ServiceGlow>
  );
}
