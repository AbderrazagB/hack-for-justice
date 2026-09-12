import Link from "next/link";

import { Logo } from "@/components/logo";

/**
 * Site footer. Carries what a registry-adjacent product owes its users: what
 * the tool is, what it is not, where the procedures come from, and how to reach
 * the registry itself.
 */

const PROCEDURES = [
  { label: "Modification Entreprise", href: "/msme/RNE_MODIFICATION_ENTREPRISE" },
  { label: "Toutes les démarches", href: "/msme" },
  { label: "Espace agent RNE", href: "/admin" },
];

const REFERENCES = [
  "Loi n° 52-2018 relative au RNE",
  "Checklist RNE-M-005",
  "Dépôt en ligne obligatoire depuis le 1er juillet 2026",
];

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-[var(--line)] bg-[var(--surface)]">
      <div className="mx-auto max-w-[1400px] px-4 py-12 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[1.6fr_1fr_1.2fr]">
          {/* Identity and the disclaimer that matters most. */}
          <div>
            <Logo size="md" />
            <p className="mt-4 max-w-sm text-[0.875rem] leading-relaxed text-[var(--ink-muted)]">
              Sahilli pré-valide les dossiers destinés au Registre National des
              Entreprises&nbsp;: pièces manquantes, informations discordantes
              entre documents, délais légaux.
            </p>
            <p className="mt-3 max-w-sm rounded-[var(--r-control)] bg-[var(--canvas)] px-3 py-2.5 text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
              Sahilli est un service indépendant. Il ne remplace pas le portail
              de dépôt du RNE et ne transmet aucun dossier au registre.
            </p>
          </div>

          <nav aria-label="Démarches">
            <h2 className="t-h3 text-[var(--navy)]">Démarches</h2>
            <ul className="mt-3.5 space-y-2.5">
              {PROCEDURES.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className="text-[0.875rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--teal-ink)]"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div>
            <h2 className="t-h3 text-[var(--navy)]">Textes de référence</h2>
            <ul className="mt-3.5 space-y-2.5">
              {REFERENCES.map((reference) => (
                <li
                  key={reference}
                  className="text-[0.875rem] leading-relaxed text-[var(--ink-muted)]"
                >
                  {reference}
                </li>
              ))}
            </ul>
            <p className="mt-4 text-[0.8125rem] text-[var(--ink-faint)]">
              Les réponses de l&apos;assistant citent uniquement ces textes.
            </p>
          </div>
        </div>
      </div>

      <div className="border-t border-[var(--line)]">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-8">
          <p className="text-[0.8125rem] text-[var(--ink-faint)]">
            Sahilli — Hack4Justice 2026
          </p>
          <p className="ar text-[0.8125rem] text-[var(--ink-faint)]">
            سهّلي — خدمة مستقلة للتحقق المسبق
          </p>
        </div>
      </div>
    </footer>
  );
}
