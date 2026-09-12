"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  Card,
  Empty,
  ErrorNote,
  Header,
  SectionTitle,
  StatusBadge,
} from "@/components/ui";
import { getStats, listSubmissions } from "@/lib/api";
import type { Stats, SubmissionSummary } from "@/lib/types";

const STATUS_FILTERS = [
  { value: "", label: "Toutes" },
  { value: "SUBMITTED", label: "Déposées" },
  { value: "PRE_VALIDATED", label: "Pré-validées" },
  { value: "NEEDS_CORRECTION", label: "À corriger" },
  { value: "APPROVED", label: "Approuvées" },
  { value: "REJECTED", label: "Rejetées" },
];

export default function OfficerQueue() {
  const [submissions, setSubmissions] = useState<SubmissionSummary[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [queue, figures] = await Promise.all([
        listSubmissions(status ? { status } : {}),
        getStats(),
      ]);
      setSubmissions(queue.submissions);
      setStats(figures);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chargement impossible.");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="min-h-screen">
      <Header
        trailing={
          <span className="rounded-full bg-[var(--brand-soft)] px-3 py-1 text-xs font-semibold text-[var(--brand-strong)]">
            Espace agent RNE
          </span>
        }
      />

      <main className="mx-auto max-w-6xl px-5 py-10">
        <h1 className="text-3xl font-bold tracking-tight">
          File de traitement
        </h1>

        {/* ------------------------------------------------------ stats panel */}
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            label="Demandes traitées"
            value={stats ? String(stats.total) : "—"}
            hint={stats ? `${stats.reviewed} décidées` : undefined}
          />
          <StatCard
            label="Délai moyen de décision"
            value={formatLatency(stats?.average_review_seconds ?? null)}
            hint="dépôt → décision"
          />
          <StatCard
            label="Taux d'anomalie"
            value={stats ? `${Math.round(stats.flag_rate * 100)} %` : "—"}
            hint={stats ? `${stats.flagged} dossiers signalés` : undefined}
            tone={stats && stats.flag_rate > 0.5 ? "accent" : undefined}
          />
          <StatCard
            label="Anomalies par dossier"
            value={stats ? stats.average_flags_per_submission.toFixed(1) : "—"}
            hint="moyenne"
          />
        </div>

        {/* ----------------------------------------------------------- filter */}
        <div className="mt-8 flex flex-wrap gap-1.5">
          {STATUS_FILTERS.map((filter) => (
            <button
              key={filter.value}
              type="button"
              onClick={() => setStatus(filter.value)}
              className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                status === filter.value
                  ? "bg-[var(--brand)] text-white"
                  : "border border-[var(--border)] hover:bg-[var(--surface-muted)]"
              }`}
            >
              {filter.label}
              {stats && filter.value
                ? ` (${stats.by_status[filter.value] ?? 0})`
                : ""}
            </button>
          ))}
        </div>

        {error && (
          <div className="mt-6">
            <ErrorNote>{error}</ErrorNote>
          </div>
        )}

        {/* ------------------------------------------------------------ queue */}
        <div className="mt-5">
          <SectionTitle hint={`${submissions.length} dossier(s)`}>
            Demandes
          </SectionTitle>

          {loading && !submissions.length ? (
            <Empty>Chargement…</Empty>
          ) : submissions.length === 0 ? (
            <Empty>
              Aucun dossier pour ce filtre. Lancez{" "}
              <code className="font-mono text-xs">
                ./scripts/seed_demo_data.sh
              </code>{" "}
              pour peupler la file.
            </Empty>
          ) : (
            <Card className="divide-y divide-[var(--border)]">
              {submissions.map((submission) => (
                <Link
                  key={submission.id}
                  href={`/admin/${submission.id}`}
                  className="flex flex-wrap items-center gap-3 p-4 transition hover:bg-[var(--surface-muted)]"
                >
                  <span className="font-mono text-xs opacity-50">
                    #{submission.id}
                  </span>

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      Modification Entreprise
                    </p>
                    <p className="text-xs opacity-55">
                      {new Date(submission.created_at).toLocaleString("fr-FR")} ·{" "}
                      {submission.document_count} pièces
                    </p>
                  </div>

                  <FlagBadge
                    total={submission.flag_count}
                    errors={submission.error_flag_count}
                  />
                  <StatusBadge status={submission.status} />
                </Link>
              ))}
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}

function StatCard({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "accent";
}) {
  return (
    <Card className="p-4">
      <p className="text-xs opacity-60">{label}</p>
      <p
        className={`mt-1 text-2xl font-bold ${
          tone === "accent" ? "text-[var(--accent)]" : ""
        }`}
      >
        {value}
      </p>
      {hint && <p className="mt-0.5 text-xs opacity-45">{hint}</p>}
    </Card>
  );
}

function FlagBadge({ total, errors }: { total: number; errors: number }) {
  if (!total) {
    return (
      <span className="rounded-full bg-[var(--success-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--success)]">
        0 anomalie
      </span>
    );
  }
  const tone = errors > 0 ? "danger" : "accent";
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-semibold bg-[var(--${tone}-soft)] text-[var(--${tone})]`}
      style={{
        background: `var(--${tone}-soft)`,
        color: `var(--${tone})`,
      }}
    >
      {total} anomalie{total > 1 ? "s" : ""}
      {errors > 0 ? ` · ${errors} bloquante${errors > 1 ? "s" : ""}` : ""}
    </span>
  );
}

function formatLatency(seconds: number | null): string {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)} s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)} h`;
  return `${(seconds / 86400).toFixed(1)} j`;
}
