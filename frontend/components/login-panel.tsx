"use client";

import {
  ArrowRight,
  Building2,
  Info,
  KeyRound,
  Lock,
  Mail,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/logo";
import { login } from "@/lib/api";

/**
 * Sign-in screen.
 *
 * Email and password authenticate for real against POST /auth/login, which
 * sets an httpOnly session cookie. The federated options below remain
 * unavailable, and say so.
 */

/**
 * The four ways in, matching the registry portal's own sign-in options.
 *
 * Digigo and MobileID carry their real marks, downloaded rather than drawn.
 * "Compte entreprise" and "Compte invité" are account types rather than
 * branded products, so they take icons.
 *
 * Only the guest route works today; the rest are marked "Bientôt". Showing a
 * provider's mark must not imply the integration exists.
 */
const OPTIONS: {
  id: string;
  logo?: string;
  icon?: LucideIcon;
  label: string;
  description: string;
  href?: string;
}[] = [
  {
    id: "digigo",
    logo: "/brand/providers/tuntrust.png",
    label: "Digigo",
    description:
      "Identité numérique TunTrust liée à votre e-mail.",
  },
  {
    id: "mobileid",
    logo: "/brand/providers/ehouwiya.png",
    label: "MobileID",
    description:
      "Validation par identité mobile, sans ressaisie.",
  },
  {
    id: "entreprise",
    icon: Building2,
    label: "Compte entreprise",
    description:
      "Identifiants de votre espace entreprise.",
  },
  {
    id: "invite",
    icon: UserRound,
    label: "Compte invité",
    description:
      "Sans création de compte. Vérifiez un dossier immédiatement.",
    href: "/msme",
  },
];

export function LoginPanel() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await login(email, password);
      router.push("/msme");
      router.refresh();
    } catch (loginError) {
      setError(
        loginError instanceof Error
          ? loginError.message
          : "La connexion a échoué. Réessayez.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
      {/* ------------------------------------------------------- form side --- */}
      <div className="flex flex-col bg-[var(--surface)]">
        <div className="border-b border-[var(--line)]">
          <div className="mx-auto w-full max-w-[60rem] px-6 py-5 sm:px-10">
            <Logo size="lg" />
          </div>
        </div>

        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-[60rem] px-6 py-10 sm:px-10">
            <header>
              <h1 className="t-h1 text-[var(--navy)]">Connexion</h1>
              <p className="ar ar-left mt-1 text-[1.125rem] text-[var(--ink-muted)]">
                تسجيل الدخول
              </p>
              <p className="mt-3 max-w-[36rem] text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
                Retrouvez vos dossiers et leur avancement. Vous pouvez aussi
                vérifier un dossier sans compte.
              </p>
            </header>

            {/* Two columns instead of one long stack: the credentials path on
                the left, every other way in on the right. */}
            <div className="mt-9 grid gap-x-10 gap-y-9 lg:grid-cols-2">
              <section>
                <ColumnHeading fr="Avec vos identifiants" ar="بمعرّفاتك" />

                {error && (
                  <div
                    role="alert"
                    className="mt-4 flex gap-2.5 rounded-[var(--r-control)] border border-[var(--st-rejected-ink)]/25 bg-[var(--st-rejected-wash)] px-3.5 py-3"
                  >
                    <Info
                      size={16}
                      strokeWidth={2}
                      className="mt-0.5 shrink-0 text-[var(--st-rejected-ink)]"
                      aria-hidden
                    />
                    <p className="text-[0.8125rem] leading-relaxed text-[var(--st-rejected-ink)]">
                      {error}
                    </p>
                  </div>
                )}

                <form className="mt-5 space-y-4" onSubmit={submit}>
                  <Field
                    id="email"
                    label="Adresse e-mail"
                    labelAr="البريد الإلكتروني"
                    icon={Mail}
                    type="email"
                    placeholder="nom@entreprise.tn"
                    value={email}
                    onChange={setEmail}
                    autoComplete="email"
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
                    autoComplete="current-password"
                  />

                  <div className="flex items-center justify-between pt-0.5">
                    <Link
                      href="/signup"
                      className="text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
                    >
                      Créer un compte
                    </Link>
                    <span className="text-[0.8125rem] text-[var(--ink-faint)]">
                      Mot de passe oublié
                    </span>
                  </div>

                  <button
                    type="submit"
                    disabled={pending || !email || !password}
                    className="flex w-full items-center justify-center gap-2 rounded-[var(--r-control)] bg-[var(--teal)] px-4 py-3 text-[0.9375rem] font-semibold text-white transition-colors hover:bg-[var(--teal-ink)] disabled:cursor-not-allowed disabled:opacity-55"
                  >
                    <KeyRound size={17} strokeWidth={2} aria-hidden />
                    {pending ? "Connexion en cours" : "Se connecter"}
                  </button>
                </form>
              </section>

              <section>
                <ColumnHeading fr="Autres moyens de connexion" ar="طرق أخرى للدخول" />

                <ul className="mt-4 space-y-2.5">
                  {OPTIONS.map((option) => (
                    <li key={option.id}>
                      <OptionCard option={option} />
                    </li>
                  ))}
                </ul>

              </section>
            </div>

            <p className="mt-9 flex items-start gap-2 border-t border-[var(--line)] pt-5 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
              <Building2
                size={13}
                strokeWidth={1.8}
                className="mt-0.5 shrink-0"
                aria-hidden
              />
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
          sizes="34vw"
          className="object-cover object-[58%_center]"
          priority
        />
        <div className="login-visual-scrim absolute inset-0" />

        <div className="relative flex h-full flex-col justify-end p-9">
          <p className="max-w-sm font-[family-name:var(--font-space-grotesk)] text-[1.625rem] leading-[1.18] font-semibold tracking-[-0.03em] text-white">
            Un dossier vérifié
            <span className="block text-[var(--teal)]">
              part sans surprise.
            </span>
          </p>
          <p className="ar ar-left mt-3 max-w-sm text-[0.9375rem] text-white/70">
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
  autoComplete,
}: {
  id: string;
  label: string;
  labelAr: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number; className?: string }>;
  type: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
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
          autoComplete={autoComplete}
          className="w-full rounded-[var(--r-control)] border border-[var(--line-strong)] bg-[var(--surface)] py-3 pr-3.5 pl-10 text-[0.9375rem] outline-none focus:border-[var(--teal)]"
        />
      </div>
    </div>
  );
}

function OptionCard({
  option,
}: {
  option: {
    logo?: string;
    icon?: LucideIcon;
    label: string;
    description: string;
    href?: string;
  };
}) {
  const Icon = option.icon;
  const live = Boolean(option.href);

  const body = (
    <>
      <span
        className={`flex size-12 shrink-0 items-center justify-center rounded-xl border ${
          live
            ? "border-[var(--teal)]/30 bg-[var(--teal-wash)]"
            : "border-[var(--line)] bg-[var(--surface)]"
        }`}
      >
        {option.logo ? (
          <Image
            src={option.logo}
            alt=""
            aria-hidden
            width={256}
            height={256}
            sizes="96px"
            className="size-7 object-contain"
          />
        ) : Icon ? (
          <Icon
            size={22}
            strokeWidth={1.6}
            className={live ? "text-[var(--teal-ink)]" : "text-[var(--ink-muted)]"}
            aria-hidden
          />
        ) : null}
      </span>

      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-3">
          <span className="font-[family-name:var(--font-space-grotesk)] text-[1rem] leading-none font-semibold whitespace-nowrap text-[var(--navy)]">
            {option.label}
          </span>
          <span className="ml-auto shrink-0">
            {live ? (
              <ArrowRight
                size={16}
                strokeWidth={2}
                className="text-[var(--teal-ink)]"
                aria-hidden
              />
            ) : (
              <span className="rounded-full bg-[var(--canvas)] px-2 py-0.5 text-[0.6875rem] leading-none font-medium text-[var(--ink-faint)]">
                Bientôt
              </span>
            )}
          </span>
        </span>
        <span className="mt-1 block text-[0.8125rem] leading-snug text-[var(--ink-muted)]">
          {option.description}
        </span>
      </span>
    </>
  );

  const shell =
    "flex w-full items-center gap-3.5 rounded-xl border px-4 py-3.5 transition-colors duration-200";

  if (!live) {
    return (
      <div
        aria-disabled
        className={`${shell} border-[var(--line)] bg-[var(--surface)]`}
      >
        {body}
      </div>
    );
  }

  return (
    <Link
      href={option.href!}
      className={`${shell} border-[var(--teal)] bg-[var(--surface)] hover:bg-[var(--teal-wash)]`}
    >
      {body}
    </Link>
  );
}

function ColumnHeading({ fr, ar }: { fr: string; ar: string }) {
  return (
    <div className="flex h-10 flex-col justify-start">
      <h2 className="t-h3 leading-none text-[var(--navy)]">{fr}</h2>
      <p className="ar ar-left mt-1 text-[0.8125rem] leading-none text-[var(--ink-faint)]">
        {ar}
      </p>
    </div>
  );
}
