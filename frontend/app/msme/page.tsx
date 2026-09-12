import Link from "next/link";

import { Card, Header } from "@/components/ui";
import { listTransactions } from "@/lib/api";
import type { TransactionInfo } from "@/lib/types";

/**
 * Service selection. Mirrors the familiar pattern of a public-service portal
 * (icon, bilingual title, call to action) with Sahilli's own visual design --
 * none of RNE's colours, layout or branding.
 *
 * Only Modification Entreprise is wired up. The other cards are shown disabled
 * to convey platform breadth without pretending they work.
 */

const COMING_SOON = [
  { icon: "🏢", fr: "Immatriculation Entreprise", ar: "ترسيم مؤسسة" },
  { icon: "📄", fr: "Dépôt des états financiers", ar: "إيداع القوائم المالية" },
  { icon: "🔒", fr: "Radiation / Cessation", ar: "شطب مؤسسة" },
  { icon: "👤", fr: "Modification Personne Physique", ar: "تحيين شخص طبيعي" },
  { icon: "🏛️", fr: "Immatriculation Association", ar: "ترسيم جمعية" },
];

export default async function MsmeLanding() {
  let transactions: TransactionInfo[] = [];
  let error = "";

  try {
    transactions = await listTransactions();
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "L'API Sahilli est injoignable.";
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-6xl px-5 py-12">
        <h1 className="text-3xl font-bold tracking-tight">
          Quelle démarche souhaitez-vous préparer&nbsp;?
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed opacity-70">
          Sahilli vérifie votre dossier avant le dépôt officiel. Choisissez une
          démarche pour voir les pièces requises.
        </p>

        {error && (
          <div className="mt-8 rounded-lg bg-[var(--danger-soft)] px-4 py-3 text-sm text-[var(--danger)]">
            {error}
          </div>
        )}

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {transactions.map((transaction) => (
            <Link
              key={transaction.transaction_type}
              href={`/msme/${transaction.transaction_type}`}
              className="group"
            >
              <Card className="flex h-full flex-col p-6 transition group-hover:border-[var(--brand)] group-hover:shadow-sm">
                <span aria-hidden className="text-2xl">
                  🔁
                </span>
                <h2 className="mt-3 font-semibold">
                  {transaction.display_name_fr}
                </h2>
                <p className="ar mt-1 text-sm opacity-70">
                  {transaction.display_name_ar}
                </p>
                <p className="mt-3 text-xs font-medium uppercase tracking-wide opacity-50">
                  Réf. {transaction.official_reference}
                </p>
                <p className="mt-3 text-sm opacity-70">
                  {transaction.required_documents.length} pièces requises
                </p>
                <span className="mt-auto pt-4 text-sm font-semibold text-[var(--brand)]">
                  Préparer mon dossier →
                </span>
              </Card>
            </Link>
          ))}

          {COMING_SOON.map((service) => (
            <Card
              key={service.fr}
              className="flex h-full flex-col p-6 opacity-55"
              aria-disabled
            >
              <span aria-hidden className="text-2xl grayscale">
                {service.icon}
              </span>
              <h2 className="mt-3 font-semibold">{service.fr}</h2>
              <p className="ar mt-1 text-sm opacity-70">{service.ar}</p>
              <span className="mt-auto pt-4 text-xs font-semibold uppercase tracking-wide">
                Bientôt disponible
              </span>
            </Card>
          ))}
        </div>
      </main>
    </div>
  );
}
