import { ArrowRight, FileText, Lock } from "lucide-react";
import Link from "next/link";

import { AppBar } from "@/components/chrome";
import { ServiceSpotlight } from "@/components/service-spotlight";
import { Notice } from "@/components/ui";
import { listTransactions } from "@/lib/api";
import { DOCUMENT_SHORT_FR } from "@/lib/status";
import type { TransactionInfo } from "@/lib/types";

/**
 * Service selection.
 *
 * The equal-weight card grid is gone on purpose. The one live procedure is a
 * single wide feature panel; the five unavailable ones are a plain bordered
 * list below it — no cards, no shadow, no matching radius — so they read as a
 * roadmap rather than as five siblings of the live one.
 */

const PLANNED_SERVICES = [
  { fr: "Immatriculation Entreprise", ar: "ترسيم مؤسسة" },
  { fr: "Dépôt des états financiers", ar: "إيداع القوائم المالية" },
  { fr: "Radiation / Cessation d'activité", ar: "شطب مؤسسة" },
  { fr: "Modification Personne Physique", ar: "تحيين شخص طبيعي" },
  { fr: "Immatriculation Association", ar: "ترسيم جمعية" },
];

export default async function ServiceSelection() {
  let transactions: TransactionInfo[] = [];
  let error = "";

  try {
    transactions = await listTransactions();
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "L'API Sahilli est injoignable. Démarrez le backend, puis rechargez la page.";
  }

  return (
    <div className="min-h-screen">
      <AppBar />

      <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
        <h1 className="t-h1">Quelle démarche préparez-vous&nbsp;?</h1>
        <p className="mt-2 max-w-xl text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
          Sahilli vérifie vos pièces avant le dépôt officiel au Registre National
          des Entreprises.
        </p>

        {error && (
          <div className="mt-8">
            <Notice>{error}</Notice>
          </div>
        )}

        {/* ------------------------------------------ the one live procedure */}
        {transactions.map((transaction) => (
          <ServiceSpotlight key={transaction.transaction_type}>
            <div className="grid gap-0 md:grid-cols-[minmax(0,13rem)_1fr]">
              {/* Navy rail carries the official reference as record data. */}
              <div className="flex flex-col justify-between gap-6 bg-[var(--navy)] p-6 sm:p-7">
                <div>
                  <p className="t-data text-[var(--teal)]">
                    {transaction.official_reference}
                  </p>
                  <p className="mt-1.5 text-[0.75rem] leading-relaxed text-white/50">
                    Référence du formulaire au registre
                  </p>
                </div>
                <p className="text-[0.75rem] text-white/45">
                  {transaction.required_documents.length} pièces à fournir
                </p>
              </div>

              <div className="p-6 sm:p-7">
                <h2 className="t-h2 text-[var(--navy)]">
                  {transaction.display_name_fr}
                </h2>
                <p className="ar mt-1 text-[1rem] text-[var(--ink-muted)]">
                  {transaction.display_name_ar}
                </p>
                <p className="mt-3 max-w-lg text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
                  Changement de représentant légal. Sahilli contrôle les cinq
                  pièces, compare les informations entre les documents et vérifie
                  le délai de dépôt.
                </p>

                <ul className="mt-5 flex flex-wrap gap-x-4 gap-y-1.5">
                  {transaction.required_documents.map((document) => (
                    <li
                      key={document.key}
                      className="flex items-center gap-1.5 text-[0.8125rem] text-[var(--ink-muted)]"
                    >
                      <FileText
                        size={13}
                        strokeWidth={1.75}
                        className="shrink-0 text-[var(--ink-faint)]"
                        aria-hidden
                      />
                      {DOCUMENT_SHORT_FR[document.key] ?? document.label_fr}
                    </li>
                  ))}
                </ul>

                <Link
                  href={`/msme/${transaction.transaction_type}`}
                  className="mt-6 inline-flex items-center gap-2 rounded-[var(--r-control)] bg-[var(--teal)] px-4 py-2.5 text-[0.875rem] font-medium text-white transition-colors hover:bg-[var(--teal-ink)]"
                >
                  Préparer ce dossier
                  <ArrowRight size={16} strokeWidth={2} aria-hidden />
                </Link>
              </div>
            </div>
          </ServiceSpotlight>
        ))}

        {/* ------------------------------------------- planned, as a list --- */}
        <section className="mt-12">
          <h2 className="t-h3 text-[var(--ink-muted)]">Démarches à venir</h2>
          <p className="mt-1 text-[0.8125rem] text-[var(--ink-faint)]">
            Ces procédures suivront le même contrôle. Elles ne sont pas encore
            ouvertes.
          </p>

          <ul className="mt-4 border-t border-[var(--line)]">
            {PLANNED_SERVICES.map((service) => (
              <li
                key={service.fr}
                className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-[var(--line)] py-3"
              >
                <span className="flex min-w-0 items-center gap-2.5">
                  <Lock
                    size={13}
                    strokeWidth={1.75}
                    className="shrink-0 text-[var(--ink-faint)]"
                    aria-hidden
                  />
                  <span className="truncate text-[0.875rem] text-[var(--ink-muted)]">
                    {service.fr}
                  </span>
                  <span className="ar truncate text-[0.8125rem] text-[var(--ink-faint)]">
                    {service.ar}
                  </span>
                </span>
                <span className="text-[0.75rem] text-[var(--ink-faint)]">
                  Bientôt
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
