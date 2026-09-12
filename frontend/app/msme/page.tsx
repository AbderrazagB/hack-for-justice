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
  { icon: "financials", titleAr: "إيداع القوائم المالية", titleFr: "Dépôt des états financiers" },
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

      <section className="relative">
        <DotField />
        <div className="relative mx-auto max-w-[1400px] px-4 py-12 sm:px-8 sm:py-16">
          <h1 className="t-h1 text-center text-[var(--navy)]">
            Accès rapide aux services
          </h1>
          <p className="ar ar-center mt-1.5 text-[1.0625rem] text-[var(--ink-muted)]">
            الولوج السريع إلى الخدمات
          </p>
          <p className="mx-auto mt-3 max-w-xl text-center text-[0.9375rem] text-[var(--ink-muted)]">
            Choisissez une démarche pour voir les pièces requises et lancer la
            vérification.
          </p>

          {error && (
            <div className="mx-auto mt-8 max-w-xl">
              <Notice>{error}</Notice>
            </div>
          )}

          <div className="mt-11 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {transactions.map((transaction) => (
              <ServiceCard
                key={transaction.transaction_type}
                icon="modification"
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
