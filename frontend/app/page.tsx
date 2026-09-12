import { ArrowRight, Building2, ClipboardCheck, Landmark } from "lucide-react";
import Link from "next/link";

import { Wordmark } from "@/components/chrome";

/**
 * Entry. Full-bleed navy field with one statement of purpose and two routes in.
 * The two routes are deliberately NOT matching cards: businesses are the primary
 * audience and get the solid white panel; the officer route is a quieter inset
 * on the navy itself.
 */
export default function Home() {
  return (
    <div className="on-navy flex min-h-screen flex-col bg-[var(--navy)]">
      <header className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
        <Wordmark tone="dark" />
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-16 sm:px-6">
        <div className="max-w-2xl pt-10 sm:pt-16">
          <h1 className="t-display text-white">
            Vérifiez votre dossier RNE
            <span className="block text-[var(--teal)]">avant de le déposer.</span>
          </h1>
          <p className="mt-5 text-[1rem] leading-relaxed text-white/70">
            Sahilli contrôle les pièces d&apos;une Modification Entreprise, compare
            les informations d&apos;un document à l&apos;autre et signale ce qui
            bloquerait le dépôt — pièce manquante, numéro de CIN discordant, délai
            légal de 30&nbsp;jours dépassé.
          </p>
          <p className="mt-3 text-[0.875rem] text-white/50">
            Sahilli ne remplace pas le portail de dépôt du RNE. Il s&apos;utilise
            avant, pour éviter un rejet.
          </p>
        </div>

        <div className="mt-12 grid gap-4 lg:grid-cols-[1.45fr_1fr]">
          {/* Primary route — solid, full weight. */}
          <Link
            href="/msme"
            className="group block rounded-[var(--r-panel)] bg-[var(--surface)] p-7 transition-transform duration-200 hover:-translate-y-0.5 sm:p-8"
          >
            <Building2 size={22} strokeWidth={1.75} className="text-[var(--teal-ink)]" />
            <h2 className="t-h2 mt-4 text-[var(--navy)]">Je prépare un dossier</h2>
            <p className="mt-2 text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
              Déposez vos cinq pièces et sachez immédiatement si le dossier
              passerait le contrôle du registre.
            </p>
            <span className="mt-6 inline-flex items-center gap-2 rounded-[var(--r-control)] bg-[var(--teal)] px-4 py-2.5 text-[0.875rem] font-medium text-white">
              Commencer la vérification
              <ArrowRight size={16} strokeWidth={2} aria-hidden />
            </span>
          </Link>

          {/* Secondary route — recessed into the navy, visibly lighter weight. */}
          <Link
            href="/admin"
            className="group block rounded-[var(--r-panel)] border border-white/12 bg-white/[0.04] p-7 transition-colors duration-200 hover:border-white/25 hover:bg-white/[0.07]"
          >
            <Landmark size={22} strokeWidth={1.75} className="text-white/60" />
            <h2 className="t-h2 mt-4 text-white">Je suis agent RNE</h2>
            <p className="mt-2 text-[0.9375rem] leading-relaxed text-white/60">
              File de traitement, anomalies détectées et décision sur chaque
              demande reçue.
            </p>
            <span className="mt-6 inline-flex items-center gap-2 text-[0.875rem] font-medium text-[var(--teal)]">
              <ClipboardCheck size={16} strokeWidth={2} aria-hidden />
              Ouvrir la file
            </span>
          </Link>
        </div>
      </main>
    </div>
  );
}
