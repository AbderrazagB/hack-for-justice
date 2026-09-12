import { Flag, Inbox } from "lucide-react";
import Link from "next/link";

import { AdminBar } from "@/components/chrome";
import { HeroAurora } from "@/components/hero-aurora";
import { StatBand, type Figure } from "@/components/stat-band";
import { EmptyState, Notice, StatusBadge } from "@/components/ui";
import { getStats, listSubmissions, listTransactions } from "@/lib/api";
import { statusStyle } from "@/lib/status";
import type { Stats, SubmissionSummary, TransactionInfo } from "@/lib/types";

/**
 * Officer queue.
 *
 * Three distinct objects, not three paddings of one card: the navy stat band
 * (glanceable), the filter row, and the queue as a dense table (scannable).
 * Rows carry a left border in their status colour so the queue can be read by
 * colour alone.
 */

const FILTERS = [
  { value: "", label: "Toutes" },
  { value: "SUBMITTED", label: "Déposées" },
  { value: "PRE_VALIDATED", label: "Pré-validées" },
  { value: "NEEDS_CORRECTION", label: "À corriger" },
  { value: "APPROVED", label: "Approuvées" },
  { value: "REJECTED", label: "Rejetées" },
];

function figures(stats: Stats | null): Figure[] {
  if (!stats) {
    return [
      { label: "Demandes reçues", value: 0, placeholder: "—" },
      { label: "Délai moyen de décision", value: 0, placeholder: "—" },
      { label: "Taux d'anomalie", value: 0, placeholder: "—" },
      { label: "Anomalies par dossier", value: 0, placeholder: "—" },
    ];
  }

  const latency = stats.average_review_seconds;
  const latencyFigure: Figure =
    latency === null
      ? {
          label: "Délai moyen de décision",
          value: 0,
          placeholder: "—",
          hint: "aucune décision encore",
        }
      : latency < 60
        ? {
            label: "Délai moyen de décision",
            value: Math.round(latency),
            suffix: " s",
            hint: "du dépôt à la décision",
          }
        : latency < 3600
          ? {
              label: "Délai moyen de décision",
              value: Math.round(latency / 60),
              suffix: " min",
              hint: "du dépôt à la décision",
            }
          : {
              label: "Délai moyen de décision",
              value: Math.round(latency / 3600),
              suffix: " h",
              hint: "du dépôt à la décision",
            };

  return [
    {
      label: "Demandes reçues",
      value: stats.total,
      hint: `${stats.reviewed} décidée${stats.reviewed > 1 ? "s" : ""}`,
    },
    latencyFigure,
    {
      label: "Taux d'anomalie",
      value: Math.round(stats.flag_rate * 100),
      suffix: " %",
      hint: `${stats.flagged} dossier${stats.flagged > 1 ? "s" : ""} signalé${stats.flagged > 1 ? "s" : ""}`,
    },
    {
      label: "Anomalies par dossier",
      value: stats.total
        ? Math.round(stats.average_flags_per_submission * 10) / 10
        : 0,
      hint: "moyenne",
    },
  ];
}

export default async function OfficerQueue({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; transaction?: string }>;
}) {
  const { status = "", transaction = "" } = await searchParams;

  let submissions: SubmissionSummary[] = [];
  let stats: Stats | null = null;
  let transactions: TransactionInfo[] = [];
  let error = "";

  try {
    const [queue, figuresData, transactionList] = await Promise.all([
      listSubmissions({
        ...(status ? { status } : {}),
        ...(transaction ? { transactionType: transaction } : {}),
      }),
      getStats(),
      listTransactions(),
    ]);
    submissions = queue.submissions;
    stats = figuresData;
    transactions = transactionList;
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "La file n'a pas pu être chargée.";
  }

  return (
    <div className="min-h-screen">
      <AdminBar />

      {/* ---------------------------------------------- navy masthead --- */}
      <div className="relative overflow-hidden bg-[var(--navy)]">
        <HeroAurora />
        <div className="relative mx-auto max-w-[1400px] px-4 pb-7 sm:px-8">
          <div className="pb-6 pt-1">
            <p className="text-[0.6875rem] font-semibold tracking-[0.14em] text-[var(--teal)] uppercase">
              Espace institutionnel
            </p>
            <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
              <h1 className="t-h1 text-white">File de traitement</h1>
              <p className="max-w-md text-[0.8125rem] text-white/55">
                Priorisez les dossiers signalés et consignez chaque décision.
              </p>
            </div>
          </div>
          <StatBand figures={figures(stats)} />
        </div>
      </div>

      <main className="mx-auto max-w-[1400px] px-4 py-8 sm:px-8">
        {error && <Notice>{error}</Notice>}

        {/* Transaction filter. Built from GET /transactions, so a new workflow
            appears here without a frontend change. Hidden while only one
            exists, since a filter with a single option is noise. */}
        {transactions.length > 1 && (
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            <FilterChip
              href={queryFor({ status, transaction: "" })}
              active={transaction === ""}
            >
              Toutes les démarches
            </FilterChip>
            {transactions.map((entry) => (
              <FilterChip
                key={entry.transaction_type}
                href={queryFor({ status, transaction: entry.transaction_type })}
                active={transaction === entry.transaction_type}
              >
                {entry.display_name_fr}
              </FilterChip>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {FILTERS.map((filter) => {
            const active = status === filter.value;
            const count = stats && filter.value ? stats.by_status[filter.value] : null;
            return (
              <Link
                key={filter.value}
                href={queryFor({ status: filter.value, transaction })}
                aria-current={active ? "page" : undefined}
                className={`rounded-[var(--r-control)] px-3 py-1.5 text-[0.8125rem] font-medium transition-colors ${
                  active
                    ? "bg-[var(--navy)] text-white"
                    : "border border-[var(--line)] text-[var(--ink-muted)] hover:border-[var(--line-strong)] hover:text-[var(--ink)]"
                }`}
              >
                {filter.label}
                {count !== null && (
                  <span className={active ? "text-white/60" : "text-[var(--ink-faint)]"}>
                    {" "}
                    {count ?? 0}
                  </span>
                )}
              </Link>
            );
          })}
        </div>

        {/* --------------------------------------------- queue table --- */}
        <div className="mt-5">
          {submissions.length === 0 && !error ? (
            <EmptyState title="Aucun dossier pour ce filtre">
              Lancez{" "}
              <code className="t-data text-[var(--ink)]">
                ./scripts/seed_demo_data.sh
              </code>{" "}
              pour remplir la file avec des dossiers de démonstration.
            </EmptyState>
          ) : (
            <div className="overflow-hidden rounded-[var(--r-panel)] border border-[var(--line)]">
              {/* The table is the one element allowed to scroll sideways on a
                  narrow screen; the page body itself never does. */}
              <div className="overflow-x-auto">
                <table className="w-full min-w-[34rem] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-[var(--line-strong)] bg-[var(--canvas)]">
                      <Th className="w-[7.5rem]">Référence</Th>
                      <Th>Démarche</Th>
                      <Th className="hidden w-[11rem] sm:table-cell">Reçu le</Th>
                      <Th className="w-[8.5rem]">Anomalies</Th>
                      <Th className="w-[9rem]">État</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {submissions.map((submission) => {
                      const tone = statusStyle(submission.status).ink;
                      return (
                        <tr
                          key={submission.id}
                          className="border-b border-[var(--line)] bg-[var(--surface)] last:border-b-0 hover:bg-[var(--canvas)]"
                        >
                          <td className="relative py-0 pl-4">
                            <span
                              aria-hidden
                              className="absolute top-0 bottom-0 left-0 w-[3px]"
                              style={{ background: tone }}
                            />
                            <Link
                              href={`/admin/${submission.id}`}
                              className="t-data block py-3.5 text-[var(--ink)] hover:text-[var(--teal-ink)]"
                            >
                              {submission.id}
                            </Link>
                          </td>
                          <td className="px-3 py-3.5 text-[0.875rem]">
                            {submission.display_name_fr}
                            <span className="ar block text-[0.75rem] text-[var(--ink-faint)]">
                              {submission.display_name_ar}
                            </span>
                          </td>
                          <td className="hidden px-3 py-3.5 text-[0.8125rem] text-[var(--ink-muted)] sm:table-cell">
                            {new Date(submission.created_at).toLocaleString("fr-FR", {
                              day: "2-digit",
                              month: "2-digit",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                          <td className="px-3 py-3.5">
                            <FlagCell
                              total={submission.flag_count}
                              errors={submission.error_flag_count}
                            />
                          </td>
                          <td className="px-3 py-3.5">
                            <StatusBadge status={submission.status} size="sm" />
                          </td>
                        </tr>
                      );
                    })}
                    </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Th({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <th
      scope="col"
      className={`px-3 py-2.5 text-[0.6875rem] font-semibold text-[var(--ink-muted)] first:pl-4 ${className}`}
    >
      {children}
    </th>
  );
}

function FlagCell({ total, errors }: { total: number; errors: number }) {
  if (!total) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[0.8125rem] text-[var(--ink-faint)]">
        <Inbox size={13} strokeWidth={1.75} aria-hidden />
        Aucune
      </span>
    );
  }

  const tone = errors > 0 ? "var(--st-rejected-ink)" : "var(--st-correction-ink)";
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium"
      style={{ color: tone }}
    >
      <Flag size={13} strokeWidth={2} aria-hidden />
      {total}
      {errors > 0 && (
        <span className="text-[0.75rem] font-normal">
          ({errors} bloquant{errors > 1 ? "s" : ""})
        </span>
      )}
    </span>
  );
}

/** Build an /admin URL preserving whichever filters are not being changed. */
function queryFor({
  status,
  transaction,
}: {
  status: string;
  transaction: string;
}): string {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  if (transaction) params.set("transaction", transaction);
  const query = params.toString();
  return query ? `/admin?${query}` : "/admin";
}

function FilterChip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={`rounded-[var(--r-control)] px-3 py-1.5 text-[0.8125rem] font-medium transition-colors ${
        active
          ? "bg-[var(--teal-ink)] text-white"
          : "border border-[var(--line)] text-[var(--ink-muted)] hover:border-[var(--line-strong)] hover:text-[var(--ink)]"
      }`}
    >
      {children}
    </Link>
  );
}
