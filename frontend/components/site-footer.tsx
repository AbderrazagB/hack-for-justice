import Link from "next/link";

import { Logo } from "@/components/logo";

/**
 * Site footer. Carries what a registry-adjacent product owes its users: what
 * the tool is, what it explicitly is not, and which texts its answers come from.
 */

const COLUMNS: {
  heading: string;
  headingAr: string;
  items: { label: string; href?: string }[];
}[] = [
  {
    heading: "Démarches",
    headingAr: "الإجراءات",
    items: [
      { label: "Modification Entreprise", href: "/msme/RNE_MODIFICATION_ENTREPRISE" },
      { label: "Toutes les démarches", href: "/msme" },
    ],
  },
  {
    heading: "Votre compte",
    headingAr: "حسابك",
    items: [
      { label: "Se connecter", href: "/login" },
      { label: "Créer un compte", href: "/signup" },
      { label: "Espace agent RNE", href: "/admin" },
    ],
  },
  {
    // No hrefs: these are the texts the assistant cites, not navigation.
    heading: "Textes de référence",
    headingAr: "النصوص المرجعية",
    items: [
      { label: "Loi n° 52-2018 relative au RNE" },
      { label: "Checklist RNE-M-005" },
      { label: "Dépôt en ligne obligatoire depuis le 1er juillet 2026" },
    ],
  },
];

export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-[var(--line)] bg-[var(--surface)]">
      <div className="mx-auto max-w-[1400px] px-4 py-12 sm:px-8">
        <div className="grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            {/* Fixed-height slot so the wordmark and the three column headings
                sit on one line, whatever the logo asset's own height is. */}
            <div className="flex h-8 items-center">
              <Logo size="md" />
            </div>
            <p className="mt-4 max-w-xs text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
              Sahilli pré-valide les dossiers destinés au Registre National des
              Entreprises&nbsp;: pièces manquantes, informations discordantes
              entre documents, délais légaux.
            </p>
          </div>

          {COLUMNS.map((column) => (
            <div key={column.heading}>
              <div className="flex h-8 flex-col justify-center">
                <h2 className="t-h3 leading-none text-[var(--navy)]">
                  {column.heading}
                </h2>
                <p className="ar ar-left mt-1 text-[0.75rem] leading-none text-[var(--ink-faint)]">
                  {column.headingAr}
                </p>
              </div>

              <ul className="mt-4 space-y-2.5">
                {column.items.map((item) => (
                  <li key={item.label}>
                    {item.href ? (
                      <Link
                        href={item.href}
                        className="text-[0.9375rem] text-[var(--ink-muted)] transition-colors hover:text-[var(--teal-ink)]"
                      >
                        {item.label}
                      </Link>
                    ) : (
                      <span className="block text-[0.9375rem] leading-snug text-[var(--ink-muted)]">
                        {item.label}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* The independence statement is the one thing every visitor should see,
          so it sits on its own line rather than inside a column. */}
      <div className="border-t border-[var(--line)] bg-[var(--canvas)]">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-x-8 gap-y-2 px-4 py-4 sm:px-8">
          <p className="text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
            Sahilli est un service indépendant. Il ne remplace pas le portail de
            dépôt du RNE et ne transmet aucun dossier au registre.
          </p>
          <p className="flex shrink-0 items-center gap-3 text-[0.8125rem] text-[var(--ink-faint)]">
            <span>Hack4Justice 2026</span>
            <span aria-hidden className="h-3 w-px bg-[var(--line-strong)]" />
            <span className="ar">سهّلي</span>
          </p>
        </div>
      </div>
    </footer>
  );
}
