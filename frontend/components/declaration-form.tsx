"use client";

import { FileSignature, Info } from "lucide-react";

import { Panel } from "@/components/ui";
import type { DeclarationField } from "@/lib/types";

/**
 * The RNE-F-005 declaration, asked as questions.
 *
 * The official form is a two-page bilingual PDF with a twenty-five box grid;
 * an applicant is expected to find it, decipher it and fill it by hand. Asking
 * the same nine questions plainly is the whole point of this step.
 *
 * Capturing it also lets the backend compare what is declared against what OCR
 * read from the documents -- the contradiction the registry rejects on, and the
 * one thing reading the attachments alone can never catch.
 */
export function DeclarationForm({
  fields,
  values,
  onChange,
  modificationType,
  modificationTypeAr,
}: {
  fields: DeclarationField[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
  modificationType: string | null;
  modificationTypeAr: string | null;
}) {
  if (fields.length === 0) return null;

  return (
    <Panel className="p-5">
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-[var(--teal-wash)] text-[var(--teal-ink)]"
        >
          <FileSignature size={18} strokeWidth={1.8} />
        </span>
        <div className="min-w-0">
          <h2 className="t-h3 text-[var(--navy)]">Votre déclaration</h2>
          <p className="ar ar-left text-[0.8125rem] text-[var(--ink-faint)]">
            التصريح
          </p>
        </div>
      </div>

      <p className="mt-3 text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
        Ces informations constituent la déclaration officielle (formulaire
        RNE-F-005). Nous les comparons à vos pièces pour détecter toute
        discordance avant le dépôt.
      </p>

      {modificationType && (
        <p className="mt-3 flex flex-wrap items-center gap-x-2 gap-y-1 rounded-[var(--r-control)] bg-[var(--canvas)] px-3 py-2 text-[0.8125rem]">
          <span className="text-[var(--ink-muted)]">Nature de la mise à jour&nbsp;:</span>
          <span className="font-medium text-[var(--navy)]">{modificationType}</span>
          {modificationTypeAr && (
            <span className="ar text-[var(--ink-faint)]">{modificationTypeAr}</span>
          )}
        </p>
      )}

      <div className="mt-5 space-y-4">
        {fields.map((field) => (
          <Field
            key={field.name}
            field={field}
            value={values[field.name] ?? ""}
            onChange={(value) => onChange(field.name, value)}
          />
        ))}
      </div>

      <p className="mt-5 flex items-start gap-2 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
        <Info size={12} strokeWidth={1.8} className="mt-0.5 shrink-0" aria-hidden />
        Le formulaire officiel précise que toute donnée manquante entraîne le
        rejet de la demande.
      </p>
    </Panel>
  );
}

function Field({
  field,
  value,
  onChange,
}: {
  field: DeclarationField;
  value: string;
  onChange: (value: string) => void;
}) {
  const inputType =
    field.type === "email" ? "email" : field.type === "tel" ? "tel" : "text";

  return (
    <div>
      <label htmlFor={`decl-${field.name}`} className="flex flex-wrap items-baseline gap-2">
        <span className="t-label text-[var(--ink)]">
          {field.label_fr}
          {!field.required && (
            <span className="font-normal text-[var(--ink-faint)]"> (facultatif)</span>
          )}
        </span>
        <span className="ar text-[0.75rem] text-[var(--ink-faint)]">
          {field.label_ar}
        </span>
      </label>
      <input
        id={`decl-${field.name}`}
        type={inputType}
        inputMode={field.type === "id" ? "numeric" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1.5 w-full rounded-[var(--r-control)] border border-[var(--line-strong)] bg-[var(--surface)] px-3 py-2.5 text-[0.9375rem] outline-none focus:border-[var(--teal)]"
      />
      {field.help_fr && (
        <p className="mt-1 text-[0.75rem] text-[var(--ink-faint)]">{field.help_fr}</p>
      )}
    </div>
  );
}
