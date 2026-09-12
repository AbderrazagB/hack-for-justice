import {
  ArrowRight,
  ClipboardCheck,
  FileSearch,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { PortalBar } from "@/components/chrome";
import { DotField } from "@/components/dot-field";
import { HeroAccent } from "@/components/hero-accent";
import { HeroAurora } from "@/components/hero-aurora";
import { Logo } from "@/components/logo";
import { RegistryFigures } from "@/components/registry-figures";
import { ServiceCard, type ServiceIcon } from "@/components/service-card";
import { SiteFooter } from "@/components/site-footer";

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
  {
    icon: "immatriculation",
    titleAr: "ترسيم مؤسسة",
    titleFr: "Immatriculation Entreprise",
  },
  {
    icon: "financials",
    titleAr: "إيداع القوائم المالية",
    titleFr: "Dépôt des états financiers",
  },
  {
    icon: "denomination",
    titleAr: "حجز التسمية",
    titleFr: "Réservation dénomination",
  },
  {
    icon: "assembly",
    titleAr: "دعوة للجلسة العامة",
    titleFr: "Convocation Assemblée Générale",
  },
  {
    icon: "extract",
    titleAr: "إستخراج مضمون من السجل",
    titleFr: "Extrait du Registre",
  },
  {
    icon: "beneficiary",
    titleAr: "التصريح بالمستفيد الحقيقي",
    titleFr: "Déclaration du bénéficiaire effectif",
  },
  {
    icon: "cessation",
    titleAr: "شطب مؤسسة",
    titleFr: "Radiation / Cessation d'activité",
  },
];

const SIGNALS = [
  { icon: ScanLine, label: "Pièces analysées", labelAr: "تحليل الوثائق" },
  { icon: FileSearch, label: "Données comparées", labelAr: "مطابقة البيانات" },
  { icon: ShieldCheck, label: "Blocages signalés", labelAr: "رصد النقائص" },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar immersive />

      <section className="on-navy hero-shell relative isolate min-h-[660px] overflow-hidden bg-[var(--navy-deep)]">
        <HeroAurora />

        <div className="relative mx-auto flex min-h-[660px] max-w-[1400px] items-center px-4 py-20 sm:px-8 lg:py-28">
          <div className="max-w-[62rem]">
            <Logo size="xl" tone="dark" href={null} />

            <h1 className="hero-title mt-9 text-white">
              Vérifiez votre dossier{" "}
              <HeroAccent>avant de le déposer.</HeroAccent>
            </h1>
            <p className="ar ar-left mt-5 text-[1.5rem] font-medium text-white/75">
              تثبّت من ملفك قبل الإيداع
            </p>
            <p className="mt-7 max-w-[46rem] text-[1.125rem] leading-8 text-white/75 sm:text-[1.1875rem] sm:leading-9">
              Sahilli contrôle vos pièces, recoupe les informations et révèle
              ce qui pourrait bloquer votre dépôt au RNE — avant que vous ne
              perdiez du temps.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                href="/msme"
                className="hero-primary-cta group inline-flex items-center gap-2.5 rounded-full bg-[var(--teal)] px-7 py-4 text-[1rem] font-semibold text-white shadow-[0_14px_38px_-14px_rgba(21,173,162,0.9)] transition-all hover:-translate-y-0.5 hover:bg-[var(--teal-ink)]"
              >
                Commencer la vérification
                <ArrowRight
                  size={18}
                  className="transition-transform group-hover:translate-x-0.5"
                  aria-hidden
                />
              </Link>
              <Link
                href="/admin"
                className="inline-flex items-center gap-2.5 rounded-full border border-white/22 bg-white/6 px-7 py-4 text-[1rem] font-medium text-white/88 backdrop-blur-md transition-all hover:-translate-y-0.5 hover:border-white/40 hover:bg-white/10 hover:text-white"
              >
                <ClipboardCheck size={18} strokeWidth={2} aria-hidden />
                Espace agent RNE
              </Link>
            </div>

            <dl className="mt-14 grid max-w-[52rem] gap-5 border-t border-white/12 pt-7 sm:grid-cols-3">
              {SIGNALS.map((signal) => {
                const Icon = signal.icon;
                return (
                  <div key={signal.label} className="flex items-start gap-3">
                    <span className="mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-xl bg-[var(--teal)]/12 text-[var(--teal)] ring-1 ring-[var(--teal)]/20">
                      <Icon size={19} strokeWidth={1.8} aria-hidden />
                    </span>
                    <div>
                      <dt className="text-[0.9375rem] font-semibold text-white/90">
                        {signal.label}
                      </dt>
                      <dd className="ar text-[0.8125rem] text-white/55">
                        {signal.labelAr}
                      </dd>
                    </div>
                  </div>
                );
              })}
            </dl>
          </div>
        </div>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-[var(--navy-deep)]/55 to-transparent" />
      </section>

      <section className="services-luxe relative overflow-hidden">
        <div className="absolute inset-0 opacity-35">
          <DotField />
        </div>
        <div className="pointer-events-none absolute top-0 left-1/2 h-px w-[min(90%,1200px)] -translate-x-1/2 bg-gradient-to-r from-transparent via-[var(--teal)]/35 to-transparent" />

        <div className="relative mx-auto max-w-[1400px] px-4 py-20 sm:px-8 sm:py-28">
          <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
            <div>
              <p className="text-[0.875rem] font-semibold tracking-[0.1em] text-[var(--teal-ink)] uppercase">
                Vos démarches, simplifiées
              </p>
              <h2 className="mt-3 max-w-2xl font-[family-name:var(--font-space-grotesk)] text-[clamp(2rem,1.35rem+2vw,3.25rem)] leading-[1.05] font-semibold tracking-[-0.035em] text-[var(--navy)]">
                Une porte d&apos;entrée claire
                <span className="block text-[var(--ink-muted)]">
                  pour chaque formalité.
                </span>
              </h2>
            </div>
            <p className="max-w-lg text-[1.0625rem] leading-8 text-[var(--ink-muted)] lg:pb-1">
              Pré-validez votre dossier avant son dépôt officiel. Chaque
              contrôle vous indique ce qui est conforme, ce qui manque et ce
              qui mérite votre attention.
            </p>
          </div>

          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {SERVICES.map((service) => (
              <ServiceCard key={service.titleFr} {...service} />
            ))}
          </div>

          <div className="mt-16">
            <RegistryFigures />
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
