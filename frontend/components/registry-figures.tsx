"use client";

import { Building2, FileText, Radio, Users } from "lucide-react";
import { useEffect, useState } from "react";

import CountUp from "@/components/CountUp";
import { useReducedMotion } from "@/components/motion";
import { getStats } from "@/lib/api";
import type { Stats } from "@/lib/types";

export function RegistryFigures() {
  const [stats, setStats] = useState<Stats | null>(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    let cancelled = false;
    getStats()
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch(() => {
        /* The band simply shows dashes if the API is unreachable. */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const figures = [
    {
      icon: Building2,
      value: stats?.total ?? null,
      label: "Dossiers vérifiés",
      labelAr: "ملفات تم التحقق منها",
    },
    {
      icon: FileText,
      value: stats ? stats.flagged : null,
      label: "Dossiers signalés",
      labelAr: "ملفات بها ملاحظات",
    },
    {
      icon: Users,
      value: stats ? stats.reviewed : null,
      label: "Décisions rendues",
      labelAr: "قرارات صادرة",
    },
  ];

  return (
    <div className="on-navy relative isolate overflow-hidden rounded-[30px] bg-[var(--navy)] px-5 py-7 shadow-[0_30px_80px_-45px_rgba(8,26,49,0.8)] sm:px-8 sm:py-9 lg:px-10">
      <div
        aria-hidden
        className="absolute -top-32 -right-24 size-80 rounded-full bg-[var(--teal)]/15 blur-3xl"
      />
      <div
        aria-hidden
        className="absolute -bottom-40 -left-24 size-80 rounded-full bg-white/6 blur-3xl"
      />

      <div className="relative grid items-center gap-8 lg:grid-cols-[0.8fr_2fr]">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/6 px-3 py-1.5 text-[0.6875rem] font-semibold tracking-[0.1em] text-white/68 uppercase">
            <Radio size={13} className="text-[var(--teal)]" aria-hidden />
            Activité en direct
          </div>
          <h2 className="mt-4 font-[family-name:var(--font-space-grotesk)] text-[1.6rem] leading-tight font-semibold tracking-[-0.03em] text-white">
            La confiance,
            <span className="block text-[var(--teal)]">rendue visible.</span>
          </h2>
          <p className="mt-3 max-w-xs text-[0.8125rem] leading-6 text-white/50">
            Les chiffres sont synchronisés avec les dossiers traités par
            Sahilli.
          </p>
        </div>

        <dl className="grid gap-3 sm:grid-cols-3">
          {figures.map((figure) => {
            const Icon = figure.icon;
            return (
              <div
                key={figure.label}
                className="rounded-[20px] border border-white/10 bg-white/6 px-5 py-5 backdrop-blur-sm transition-colors hover:bg-white/9"
              >
                <div className="flex items-center justify-between">
                  <span className="flex size-9 items-center justify-center rounded-xl bg-[var(--teal)]/12 text-[var(--teal)] ring-1 ring-[var(--teal)]/20">
                    <Icon size={18} strokeWidth={1.6} aria-hidden />
                  </span>
                  <span className="size-1.5 rounded-full bg-[var(--teal)] shadow-[0_0_12px_var(--teal)]" />
                </div>
                <dd className="t-stat mt-6 text-white">
                  {figure.value === null ? (
                    <span className="text-white/28">—</span>
                  ) : reduced ? (
                    figure.value.toLocaleString("fr-FR")
                  ) : (
                    <CountUp to={figure.value} duration={1.4} separator=" " />
                  )}
                </dd>
                <dt className="mt-2 text-[0.75rem] font-semibold text-white/76">
                  {figure.label}
                </dt>
                <p className="ar mt-0.5 text-[0.6875rem] text-white/38">
                  {figure.labelAr}
                </p>
              </div>
            );
          })}
        </dl>
      </div>
    </div>
  );
}
