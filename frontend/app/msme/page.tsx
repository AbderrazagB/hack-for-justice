import { PortalBar } from "@/components/chrome";
import { DotField } from "@/components/dot-field";
import { ServiceCard, type ServiceIcon } from "@/components/service-card";
import { SiteFooter } from "@/components/site-footer";
import { Notice } from "@/components/ui";
import { listTransactions } from "@/lib/api";
import type { TransactionInfo } from "@/lib/types";

/**
 * Service catalogue. Same card pattern as the entry page so the two read as one
 * system. The live procedures come from GET /transactions, so the rules engine
 * stays the single source of truth for what Sahilli can actually check; the
 * planned ones are listed statically and carry no pill.
 */

const PLANNED: { icon: ServiceIcon; titleAr: string; titleFr: string }[] = [
  { icon: "immatriculation", titleAr: "ترسيم مؤسسة", titleFr: "Immatriculation Entreprise" },
  { icon: "denomination", titleAr: "حجز التسمية", titleFr: "Réservation dénomination" },
  { icon: "assembly", titleAr: "دعوة للجلسة العامة", titleFr: "Convocation Assemblée Générale" },
  { icon: "extract", titleAr: "إستخراج مضمون من السجل", titleFr: "Extrait du Registre" },
  { icon: "beneficiary", titleAr: "التصريح بالمستفيد الحقيقي", titleFr: "Déclaration du bénéficiaire effectif" },
  { icon: "cessation", titleAr: "شطب مؤسسة", titleFr: "Radiation / Cessation d'activité" },
];

export default async function ServiceCatalogue() {
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
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar />

      <section className="services-luxe relative overflow-hidden">
        <div className="absolute inset-0 opacity-35">
          <DotField />
        </div>
        <div className="relative mx-auto max-w-[1400px] px-4 py-14 sm:px-8 sm:py-20">
          <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
            <div>
              <p className="text-[0.75rem] font-semibold tracking-[0.14em] text-[var(--teal-ink)] uppercase">
                Catalogue des démarches
              </p>
              <h1 className="mt-3 font-[family-name:var(--font-space-grotesk)] text-[clamp(2.25rem,1.65rem+2vw,3.5rem)] leading-[1.05] font-semibold tracking-[-0.035em] text-[var(--navy)]">
                Choisissez votre démarche.
              </h1>
              <p className="ar ar-left mt-2 text-[1.125rem] text-[var(--ink-muted)]">
                اختر الإجراء الذي تريد القيام به
              </p>
            </div>
            <p className="max-w-lg text-[0.9375rem] leading-7 text-[var(--ink-muted)] lg:pb-1">
              Consultez les pièces requises, préparez votre dossier et détectez
              les blocages avant le dépôt officiel au RNE.
            </p>
          </div>

          {error && (
            <div className="mx-auto mt-8 max-w-xl">
              <Notice>{error}</Notice>
            </div>
          )}

          <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {transactions.map((transaction) => (
              <ServiceCard
                key={transaction.transaction_type}
                icon={
                  transaction.transaction_type === "RNE_FINANCIAL_STATEMENTS"
                    ? "financials"
                    : "modification"
                }
                titleAr={transaction.display_name_ar}
                titleFr={transaction.display_name_fr}
                href={`/msme/${transaction.transaction_type}`}
                reference={transaction.official_reference}
              />
            ))}
            {PLANNED.map((service) => (
              <ServiceCard key={service.titleFr} {...service} />
            ))}
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
