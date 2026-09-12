import Link from "next/link";

import { Card, Header } from "@/components/ui";

export default function Home() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-4xl px-5 py-16">
        <p className="text-sm font-semibold uppercase tracking-widest text-[var(--brand)]">
          Hack4Justice 2026
        </p>
        <h1 className="mt-3 text-4xl font-bold tracking-tight">
          Vérifiez votre dossier RNE avant de le déposer.
        </h1>
        <p className="mt-4 max-w-2xl text-base leading-relaxed opacity-75">
          Sahilli contrôle les pièces d&apos;une <strong>Modification
          Entreprise</strong> — pièces manquantes, numéros de CIN qui ne
          concordent pas, délai légal de 30 jours dépassé — et explique, en
          français ou en arabe, ce qu&apos;il faut corriger. Sahilli ne remplace
          pas le portail de dépôt du RNE&nbsp;: il s&apos;y ajoute en amont.
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <Link href="/msme" className="group">
            <Card className="h-full p-6 transition group-hover:border-[var(--brand)]">
              <h2 className="text-lg font-semibold">Je suis une entreprise</h2>
              <p className="mt-2 text-sm opacity-70">
                Déposer mes documents et savoir immédiatement si mon dossier
                passerait le contrôle du registre.
              </p>
              <span className="mt-4 inline-block text-sm font-semibold text-[var(--brand)]">
                Commencer →
              </span>
            </Card>
          </Link>

          <Link href="/admin" className="group">
            <Card className="h-full p-6 transition group-hover:border-[var(--brand)]">
              <h2 className="text-lg font-semibold">Je suis agent RNE</h2>
              <p className="mt-2 text-sm opacity-70">
                Consulter la file des demandes, les anomalies détectées et
                décider&nbsp;: approuver, rejeter, demander une correction.
              </p>
              <span className="mt-4 inline-block text-sm font-semibold text-[var(--brand)]">
                Ouvrir le tableau de bord →
              </span>
            </Card>
          </Link>
        </div>
      </main>
    </div>
  );
}
