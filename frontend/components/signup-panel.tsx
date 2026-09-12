"use client";

import { Building2, Info, Lock, Mail, UserPlus, UserRound } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ActionButton } from "@/components/action-button";
import { Logo } from "@/components/logo";
import { signup } from "@/lib/api";

/** Matches MIN_PASSWORD_LENGTH in backend/app/api/auth.py. */
const MIN_PASSWORD_LENGTH = 10;

/**
 * Account creation. Registers against POST /auth/signup, which always creates
 * an applicant -- officer accounts are made out of band, so the form has no
 * role field to tamper with.
 */
export function SignupPanel() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  const tooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;
  const ready =
    fullName.trim().length >= 2 &&
    email.includes("@") &&
    password.length >= MIN_PASSWORD_LENGTH;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      await signup({
        email,
        password,
        full_name: fullName,
        company_name: companyName || undefined,
      });
      router.push("/msme");
      router.refresh();
    } catch (signupError) {
      setError(
        signupError instanceof Error
          ? signupError.message
          : "La création du compte a échoué. Réessayez.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
      <div className="flex flex-col bg-[var(--surface)]">
        <div className="border-b border-[var(--line)]">
          <div className="mx-auto w-full max-w-[60rem] px-6 py-5 sm:px-10">
            <Logo size="lg" />
          </div>
        </div>

        <div className="flex flex-1 items-center">
          <div className="mx-auto w-full max-w-[60rem] px-6 py-10 sm:px-10">
            <header>
              <h1 className="t-h1 text-[var(--navy)]">Créer un compte</h1>
              <p className="ar ar-left mt-1 text-[1.125rem] text-[var(--ink-muted)]">
                إنشاء حساب
              </p>
              <p className="mt-3 max-w-[36rem] text-[0.9375rem] leading-relaxed text-[var(--ink-muted)]">
                Un compte vous permet de retrouver vos dossiers et leur
                avancement. La vérification reste possible sans compte.
              </p>
            </header>

            <div className="mt-9 grid gap-x-10 gap-y-9 lg:grid-cols-2">
              <section>
                <div className="flex h-10 flex-col justify-start">
                  <h2 className="t-h3 leading-none text-[var(--navy)]">
                    Vos informations
                  </h2>
                  <p className="ar ar-left mt-1 text-[0.8125rem] leading-none text-[var(--ink-faint)]">
                    معلوماتك
                  </p>
                </div>

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
                    id="full_name"
                    label="Nom et prénom"
                    labelAr="الاسم واللقب"
                    icon={UserRound}
                    type="text"
                    placeholder="Amine Ben Salah"
                    value={fullName}
                    onChange={setFullName}
                    autoComplete="name"
                  />
                  <Field
                    id="company_name"
                    label="Société (facultatif)"
                    labelAr="الشركة (اختياري)"
                    icon={Building2}
                    type="text"
                    placeholder="SARL Exemple"
                    value={companyName}
                    onChange={setCompanyName}
                    autoComplete="organization"
                  />
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
                    placeholder="••••••••••"
                    value={password}
                    onChange={setPassword}
                    autoComplete="new-password"
                    hint={`Au moins ${MIN_PASSWORD_LENGTH} caractères.`}
                    invalid={tooShort}
                  />

                  <ActionButton
                    type="submit"
                    disabled={pending || !ready}
                    className="w-full"
                  >
                    <UserPlus size={17} strokeWidth={2} aria-hidden />
                    {pending ? "Création en cours" : "Créer mon compte"}
                  </ActionButton>

                  <p className="text-center text-[0.8125rem] text-[var(--ink-muted)]">
                    Vous avez déjà un compte&nbsp;?{" "}
                    <Link
                      href="/login"
                      className="font-medium text-[var(--teal-ink)] hover:underline"
                    >
                      Se connecter
                    </Link>
                  </p>
                </form>
              </section>

              <section>
                <div className="flex h-10 flex-col justify-start">
                  <h2 className="t-h3 leading-none text-[var(--navy)]">
                    Ce que le compte apporte
                  </h2>
                  <p className="ar ar-left mt-1 text-[0.8125rem] leading-none text-[var(--ink-faint)]">
                    ما يوفّره الحساب
                  </p>
                </div>

                <ul className="mt-4 space-y-2.5">
                  {[
                    {
                      title: "Vos dossiers réunis",
                      body: "Retrouvez chaque vérification et son résultat.",
                    },
                    {
                      title: "Suivi de l'examen",
                      body: "Suivez l'avancement jusqu'à la décision de l'agent.",
                    },
                    {
                      title: "Corrections conservées",
                      body: "Les anomalies signalées restent consultables.",
                    },
                  ].map((item) => (
                    <li
                      key={item.title}
                      className="rounded-xl border border-[var(--line)] px-4 py-3.5"
                    >
                      <p className="font-[family-name:var(--font-space-grotesk)] text-[1rem] font-semibold text-[var(--navy)]">
                        {item.title}
                      </p>
                      <p className="mt-1 text-[0.8125rem] leading-snug text-[var(--ink-muted)]">
                        {item.body}
                      </p>
                    </li>
                  ))}
                </ul>

                <div className="mt-4 rounded-xl border border-[var(--teal)] bg-[var(--teal-wash)] px-4 py-3.5">
                  <p className="text-[0.875rem] font-semibold text-[var(--teal-ink)]">
                    Pas besoin de compte pour essayer
                  </p>
                  <Link
                    href="/msme"
                    className="mt-1 inline-block text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
                  >
                    Vérifier un dossier immédiatement
                  </Link>
                </div>
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
            Chaque dossier,
            <span className="block text-[var(--teal)]">suivi de bout en bout.</span>
          </p>
          <p className="ar ar-left mt-3 max-w-sm text-[0.9375rem] text-white/70">
            متابعة كل ملف من البداية إلى القرار
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
  hint,
  invalid,
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
  hint?: string;
  invalid?: boolean;
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
          aria-invalid={invalid || undefined}
          className={`w-full rounded-[var(--r-control)] border bg-[var(--surface)] py-3 pr-3.5 pl-10 text-[0.9375rem] outline-none focus:border-[var(--teal)] ${
            invalid ? "border-[var(--st-rejected-ink)]" : "border-[var(--line-strong)]"
          }`}
        />
      </div>
      {hint && (
        <p
          className={`mt-1 text-[0.75rem] ${
            invalid ? "text-[var(--st-rejected-ink)]" : "text-[var(--ink-faint)]"
          }`}
        >
          {hint}
        </p>
      )}
    </div>
  );
}
