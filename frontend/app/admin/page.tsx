import { LogIn, ShieldAlert } from "lucide-react";
import Link from "next/link";

import { AdminBar } from "@/components/chrome";
import { DossierCard } from "@/components/dossier-card";
import { HeroAurora } from "@/components/hero-aurora";
import { StatBand, type Figure } from "@/components/stat-band";
import { EmptyState, Notice } from "@/components/ui";
import {
  ApiError,
  getStats,
  listSubmissions,
  listTransactions,
  serverAuthHeaders,
} from "@/lib/api";
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
  let unauthorised = false;

  const headers = await serverAuthHeaders();

  try {
    const [queue, figuresData, transactionList] = await Promise.all([
      listSubmissions(
        {
          ...(status ? { status } : {}),
          ...(transaction ? { transactionType: transaction } : {}),
        },
        headers,
      ),
      getStats(headers),
      listTransactions(),
    ]);
    submissions = queue.submissions;
    stats = figuresData;
    transactions = transactionList;
  } catch (requestError) {
    // The queue lists every applicant's filing, so the backend requires an
    // officer session. Distinguish "not signed in" from a genuine failure.
    if (
      requestError instanceof ApiError &&
      (requestError.status === 401 || requestError.status === 403)
    ) {
      unauthorised = true;
    } else {
      error =
        requestError instanceof Error
          ? requestError.message
          : "La file n'a pas pu être chargée.";
    }
  }

  if (unauthorised) {
    return <OfficerSignInRequired />;
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

        {/* ---------------------------------------------- the queue --- */}
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
            /* A grid of dossiers rather than a table of rows. The officer
               triages on three things -- what is blocking, what state it is
               in, how long it has waited -- and a card puts all three where
               they can be seen without reading across columns. */
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {submissions.map((submission) => (
                <li key={submission.id}>
                  <DossierCard
                    submission={submission}
                    href={`/admin/${submission.id}`}
                    showAge
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}

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

/**
 * Shown when the officer surfaces are reached without an officer session.
 *
 * A bare 401 would read as a broken page. This says what is needed and where
 * to go, without hinting at what the queue contains.
 */
function OfficerSignInRequired() {
  return (
    <div className="min-h-screen">
      <AdminBar />
      <main className="mx-auto max-w-xl px-4 py-20 sm:px-8">
        <div className="rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-8 text-center">
          <span
            aria-hidden
            className="mx-auto flex size-12 items-center justify-center rounded-full bg-[var(--brand-soft,var(--teal-wash))] text-[var(--teal-ink)]"
          >
            <ShieldAlert size={24} strokeWidth={1.8} />
          </span>
          <h1 className="t-h2 mt-5 text-[var(--navy)]">Accès réservé aux agents</h1>
          <p className="ar ar-center mt-1 text-[0.9375rem] text-[var(--ink-muted)]">
            فضاء محجوز لأعوان السجل
          </p>
          <p className="mx-auto mt-4 max-w-sm text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
            La file de traitement contient les dossiers déposés par les
            entreprises. Connectez-vous avec un compte agent du registre pour y
            accéder.
          </p>
          <Link
            href="/login"
            className="mt-6 inline-flex items-center gap-2 rounded-[var(--r-control)] bg-[var(--teal)] px-5 py-3 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-[var(--teal-ink)]"
          >
            <LogIn size={17} strokeWidth={2} aria-hidden />
            Se connecter
          </Link>
        </div>
      </main>
    </div>
  );
}
