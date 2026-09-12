import { ClipboardCheck } from "lucide-react";
import Link from "next/link";

import { DotField } from "@/components/dot-field";
import { HeroAurora } from "@/components/hero-aurora";
import { PortalBar } from "@/components/chrome";
import { RegistryFigures } from "@/components/registry-figures";
import { ServiceCard, type ServiceIcon } from "@/components/service-card";
import { SiteFooter } from "@/components/site-footer";

/**
 * Entry. Follows the layout language of the registry portal an applicant
 * already knows — navy masthead, centred section heading, a grid of bilingual
 * service cards, then a figures band — in Sahilli's own palette and wordmark.
 * No state emblem, no flag, no RNE logo: this sits in front of the registry, it
 * does not present itself as the registry.
 */

const SERVICES: {
  icon: ServiceIcon;
  titleAr: string;
  titleFr: string;
  href?: string;
  reference?: string;
}[] = [
  {
    icon: "modification",
    titleAr: "تحيين مؤسسة",
    titleFr: "Modification Entreprise",
    href: "/msme/RNE_MODIFICATION_ENTREPRISE",
    reference: "RNE-M-005",
  },
  { icon: "immatriculation", titleAr: "ترسيم مؤسسة", titleFr: "Immatriculation Entreprise" },
  { icon: "financials", titleAr: "إيداع القوائم المالية", titleFr: "Dépôt des états financiers" },
  { icon: "denomination", titleAr: "حجز التسمية", titleFr: "Réservation dénomination" },
  { icon: "assembly", titleAr: "دعوة للجلسة العامة", titleFr: "Convocation Assemblée Générale" },
  { icon: "extract", titleAr: "إستخراج مضمون من السجل", titleFr: "Extrait du Registre" },
  { icon: "beneficiary", titleAr: "التصريح بالمستفيد الحقيقي", titleFr: "Déclaration du bénéficiaire effectif" },
  { icon: "cessation", titleAr: "شطب مؤسسة", titleFr: "Radiation / Cessation d'activité" },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar />

      {/* ------------------------------------------------ navy masthead --- */}
      <section className="on-navy relative overflow-hidden bg-[var(--navy)]">
        <HeroAurora />
        <div className="relative mx-auto max-w-[1400px] px-4 py-16 sm:px-8 sm:py-24">
          <div className="max-w-2xl">
            <h1 className="t-display text-white">
              Vérifiez votre dossier
              <span className="block text-[var(--teal)]">avant de le déposer.</span>
            </h1>
            <p className="ar ar-left mt-3 text-[1.125rem] text-white/70">
              تثبّت من ملفك قبل الإيداع
            </p>
            <p className="mt-5 max-w-xl text-[0.9375rem] leading-relaxed text-white/70">
              Sahilli contrôle les pièces d&apos;une Modification Entreprise,
              compare les informations d&apos;un document à l&apos;autre et
              signale ce qui bloquerait le dépôt — pièce manquante, numéro de CIN
              discordant, délai légal de 30 jours dépassé.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                href="/msme"
                className="rounded-full bg-[var(--teal)] px-5 py-2.5 text-[0.875rem] font-medium text-white transition-colors hover:bg-[var(--teal-ink)]"
              >
                Commencer la vérification
              </Link>
              <Link
                href="/admin"
                className="inline-flex items-center gap-2 rounded-full border border-white/25 px-5 py-2.5 text-[0.875rem] font-medium text-white/85 transition-colors hover:border-white/50 hover:text-white"
              >
                <ClipboardCheck size={16} strokeWidth={2} aria-hidden />
                Espace agent RNE
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ------------------------------------------------- service grid --- */}
      <section className="relative">
        <DotField />
        <div className="relative mx-auto max-w-[1400px] px-4 py-16 sm:px-8">
          <h2 className="t-h1 text-center text-[var(--navy)]">
            Accès rapide aux services
          </h2>
          <p className="mx-auto mt-2.5 max-w-xl text-center text-[0.9375rem] text-[var(--ink-muted)]">
            Sahilli pré-valide votre dossier avant le dépôt officiel au Registre
            National des Entreprises.
          </p>

          <div className="mt-11 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {SERVICES.map((service) => (
              <ServiceCard key={service.titleFr} {...service} />
            ))}
          </div>

          <div className="mt-12">
            <RegistryFigures />
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
