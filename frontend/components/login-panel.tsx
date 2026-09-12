"use client";

import {
  ArrowLeft,
  BadgeCheck,
  Building2,
  Fingerprint,
  Info,
  KeyRound,
  Lock,
  Mail,
  UserRound,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useState } from "react";

import { Logo } from "@/components/logo";

/**
 * Sign-in screen.
 *
 * NOTHING HERE AUTHENTICATES. Sahilli has no accounts yet, so the form is
 * deliberately inert: submission is blocked, the fields carry autoComplete
 * "off", and a notice states plainly that credentials are not checked or
 * stored. That matters more than it looks -- a convincing login form that
 * quietly does nothing is a good way to collect real passwords by accident.
 *
 * Email + password is the path we can actually build, so it is the only option
 * presented as live-to-come. The national identity options below it are shown
 * as unavailable rather than hidden, to be honest about what integrating with
 * them would require.
 */

const FEDERATED = [
  {
    icon: Fingerprint,
    label: "Identité numérique nationale",
    labelAr: "الهوية الرقمية الوطنية",
    note: "Nécessite une convention avec l'opérateur national",
  },
  {
    icon: BadgeCheck,
    label: "Certificat électronique",
    labelAr: "الشهادة الإلكترونية",
    note: "Nécessite un lecteur de certificat",
  },
];

export function LoginPanel() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* ------------------------------------------------------- form side --- */}
      <div className="flex flex-col bg-[var(--surface)]">
        <div className="border-b border-[var(--line)] px-6 py-5 sm:px-10">
          <Logo size="lg" />
        </div>

        <div className="flex flex-1 items-center justify-center px-6 py-12 sm:px-10">
          <div className="w-full max-w-[26rem]">
            <h1 className="t-h1 text-[var(--navy)]">Connexion</h1>
            <p className="ar ar-left mt-1 text-[1.125rem] text-[var(--ink-muted)]">
              تسجيل الدخول
            </p>
            <p className="mt-4 text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
              Retrouvez vos dossiers et leur avancement. Vous pouvez aussi
              vérifier un dossier sans compte.
            </p>

            {/* The honesty notice. Do not remove while the form is inert. */}
            <div
              role="note"
              className="mt-6 flex gap-2.5 rounded-[var(--r-control)] border border-[var(--st-correction-ink)]/25 bg-[var(--st-correction-wash)] px-3.5 py-3"
            >
              <Info
                size={16}
                strokeWidth={2}
                className="mt-0.5 shrink-0 text-[var(--st-correction-ink)]"
                aria-hidden
              />
              <p className="text-[0.8125rem] leading-relaxed text-[var(--st-correction-ink)]">
                Maquette : l&apos;authentification n&apos;est pas encore en
                service. Aucun identifiant n&apos;est vérifié ni enregistré.
                N&apos;utilisez pas un mot de passe réel.
              </p>
            </div>

            <form
              className="mt-6 space-y-4"
              onSubmit={(event) => event.preventDefault()}
            >
              <Field
                id="email"
                label="Adresse e-mail"
                labelAr="البريد الإلكتروني"
                icon={Mail}
                type="email"
                placeholder="nom@entreprise.tn"
                value={email}
                onChange={setEmail}
              />
              <Field
                id="password"
                label="Mot de passe"
                labelAr="كلمة المرور"
                icon={Lock}
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={setPassword}
              />

              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 text-[0.8125rem] text-[var(--ink-muted)]">
                  <input
                    type="checkbox"
                    disabled
                    className="size-4 rounded border-[var(--line-strong)] accent-[var(--teal)]"
                  />
                  Rester connecté
                </label>
                <span className="text-[0.8125rem] text-[var(--ink-faint)]">
                  Mot de passe oublié
                </span>
              </div>

              <button
                type="submit"
                disabled
                className="flex w-full items-center justify-center gap-2 rounded-[var(--r-control)] bg-[var(--teal)] px-4 py-3 text-[0.9375rem] font-semibold text-white disabled:cursor-not-allowed disabled:opacity-55"
              >
                <KeyRound size={17} strokeWidth={2} aria-hidden />
                Se connecter
              </button>
            </form>

            <div className="my-7 flex items-center gap-3">
              <span className="h-px flex-1 bg-[var(--line)]" />
              <span className="text-[0.75rem] text-[var(--ink-faint)]">
                ou
              </span>
              <span className="h-px flex-1 bg-[var(--line)]" />
            </div>

            {/* The one route that actually works today. */}
            <Link
              href="/msme"
              className="flex items-center gap-3 rounded-[var(--r-control)] border border-[var(--teal)] bg-[var(--teal-wash)] px-4 py-3.5 transition-colors hover:bg-[var(--teal)]/15"
            >
              <UserRound
                size={18}
                strokeWidth={1.9}
                className="shrink-0 text-[var(--teal-ink)]"
                aria-hidden
              />
              <span className="min-w-0 flex-1">
                <span className="block text-[0.9375rem] font-semibold text-[var(--teal-ink)]">
                  Continuer sans compte
                </span>
                <span className="ar ar-left block text-[0.8125rem] text-[var(--teal-ink)]/75">
                  المتابعة دون حساب
                </span>
              </span>
              <ArrowLeft
                size={16}
                strokeWidth={2}
                className="shrink-0 rotate-180 text-[var(--teal-ink)]"
                aria-hidden
              />
            </Link>

            <ul className="mt-3 space-y-2.5">
              {FEDERATED.map((option) => {
                const Icon = option.icon;
                return (
                  <li
                    key={option.label}
                    className="flex items-center gap-3 rounded-[var(--r-control)] border border-dashed border-[var(--line-strong)] px-4 py-3"
                  >
                    <Icon
                      size={18}
                      strokeWidth={1.7}
                      className="shrink-0 text-[var(--ink-faint)]"
                      aria-hidden
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[0.875rem] text-[var(--ink-muted)]">
                        {option.label}
                      </span>
                      <span className="ar ar-left block text-[0.75rem] text-[var(--ink-faint)]">
                        {option.labelAr}
                      </span>
                    </span>
                    <span
                      title={option.note}
                      className="shrink-0 text-[0.6875rem] whitespace-nowrap text-[var(--ink-faint)]"
                    >
                      Indisponible
                    </span>
                  </li>
                );
              })}
            </ul>

            <p className="mt-8 flex items-start gap-2 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
              <Building2 size={13} strokeWidth={1.8} className="mt-0.5 shrink-0" aria-hidden />
              Sahilli est un service indépendant de pré-validation. Le dépôt
              officiel reste à effectuer sur le portail du RNE.
            </p>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------ visual side --- */}
      <div className="relative hidden overflow-hidden bg-[var(--navy-deep)] lg:block">
        <Image
          src="/brand/sahilli-hero-documents.png"
          alt=""
          aria-hidden
          fill
          sizes="50vw"
          className="object-cover object-[58%_center]"
          priority
        />
        <div className="login-visual-scrim absolute inset-0" />

        <div className="relative flex h-full flex-col justify-end p-12">
          <p className="max-w-md font-[family-name:var(--font-space-grotesk)] text-[2rem] leading-[1.15] font-semibold tracking-[-0.03em] text-white">
            Un dossier vérifié
            <span className="block text-[var(--teal)]">
              part sans surprise.
            </span>
          </p>
          <p className="ar ar-left mt-3 max-w-md text-[1.0625rem] text-white/70">
            ملف تم التثبّت منه يُودَع دون مفاجآت
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({
  id,
  label,
  labelAr,
  icon: Icon,
  type,
  placeholder,
  value,
  onChange,
}: {
  id: string;
  label: string;
  labelAr: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  type: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="flex items-baseline gap-2">
        <span className="t-label text-[var(--ink)]">{label}</span>
        <span className="ar text-[0.75rem] text-[var(--ink-faint)]">{labelAr}</span>
      </label>
      <div className="relative mt-1.5">
        <Icon
          size={17}
          strokeWidth={1.8}
          className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-[var(--ink-faint)]"
        />
        <input
          id={id}
          type={type}
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          autoComplete="off"
          className="w-full rounded-[var(--r-control)] border border-[var(--line-strong)] bg-[var(--surface)] py-3 pr-3.5 pl-10 text-[0.9375rem] outline-none focus:border-[var(--teal)]"
        />
      </div>
    </div>
  );
}
