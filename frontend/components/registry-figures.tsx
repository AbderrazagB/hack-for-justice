"use client";

import { Building2, FileText, Users } from "lucide-react";
import { useEffect, useState } from "react";

import CountUp from "@/components/CountUp";
import { useReducedMotion } from "@/components/motion";
import { getStats } from "@/lib/api";
import type { Stats } from "@/lib/types";

/**
 * The figures band. Unlike the registry's own counters these are Sahilli's
 * live numbers, read from GET /submissions/stats — nothing here is hardcoded.
 * React Bits `CountUp` runs them once on load.
 */
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
    <div className="rounded-2xl bg-[#EDF1F7] px-4 py-9 sm:px-8">
      <dl className="grid gap-8 sm:grid-cols-3">
        {figures.map((figure) => {
          const Icon = figure.icon;
          return (
            <div key={figure.label} className="text-center">
              <Icon
                size={30}
                strokeWidth={1.4}
                className="mx-auto text-[var(--navy)]"
                aria-hidden
              />
              <dd className="t-stat mt-3 text-[var(--teal-ink)]">
                {figure.value === null ? (
                  <span className="text-[var(--ink-faint)]">—</span>
                ) : reduced ? (
                  figure.value.toLocaleString("fr-FR")
                ) : (
                  <CountUp to={figure.value} duration={1.4} separator=" " />
                )}
              </dd>
              <dt className="mt-1.5 text-[0.8125rem] font-medium text-[var(--navy)]">
                {figure.label}
              </dt>
              <p className="ar text-[0.75rem] text-[var(--ink-muted)]">
                {figure.labelAr}
              </p>
            </div>
          );
        })}
      </dl>
    </div>
  );
}
