"use client";

import { ChevronDown, FileSignature, GitCompareArrows, Info } from "lucide-react";
import { useState } from "react";

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
 * one thing reading the attachments alone can never catch. That comparison is
 * why the pieces are still required alongside the answers, so the three
 * questions it applies to say out loud which document they are held against.
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

  // The form's own order already groups cleanly, so sections are drawn over it
  // rather than rearranging it (a backend test holds that true).
  const sections: { key: string; label_fr: string; label_ar: string; fields: DeclarationField[] }[] =
    [];
  for (const field of fields) {
    const last = sections[sections.length - 1];
    if (last && last.key === field.group) last.fields.push(field);
    else
      sections.push({
        key: field.group,
        label_fr: field.group_fr,
        label_ar: field.group_ar,
        fields: [field],
      });
  }

  const comparedCount = fields.filter((field) => field.cross_checked).length;

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
        RNE-F-005). Vous n&apos;avez pas à le télécharger ni à le déchiffrer :
        répondez ici, nous le remplissons.
      </p>

      {/* The obvious objection -- "pourquoi me demander ce qui figure déjà sur
          mes pièces ?" -- answered where it is raised. */}
      <p className="mt-3 flex items-start gap-2 rounded-[var(--r-control)] border-l-2 border-[var(--teal)] bg-[var(--teal-wash)] px-3 py-2 text-[0.75rem] leading-relaxed text-[var(--ink-muted)]">
        <GitCompareArrows
          size={13}
          strokeWidth={2}
          className="mt-0.5 shrink-0 text-[var(--teal-ink)]"
          aria-hidden
        />
        <span>
          {comparedCount} de ces réponses sont <strong className="font-medium text-[var(--ink)]">recoupées</strong>{" "}
          avec vos pièces. C&apos;est la comparaison des deux — et non la lecture
          des documents seuls — qui révèle les contradictions sur lesquelles le
          registre rejette. Vos pièces restent donc exigées, comme sur la liste
          officielle.
        </span>
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

      <div className="mt-6 space-y-7">
        {sections.map((section) => (
          <section key={section.key}>
            <div className="flex items-baseline gap-2 border-b border-[var(--line)] pb-1.5">
              <h3 className="t-label text-[var(--ink-muted)]">{section.label_fr}</h3>
              <span className="ar text-[0.75rem] text-[var(--ink-faint)]">
                {section.label_ar}
              </span>
            </div>
            <div className="mt-4 space-y-4">
              {section.fields.map((field) => (
                <Field
                  key={field.name}
                  field={field}
                  value={values[field.name] ?? ""}
                  onChange={(value) => onChange(field.name, value)}
                />
              ))}
            </div>
          </section>
        ))}
      </div>

      <p className="mt-6 flex items-start gap-2 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
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
  const [showWhy, setShowWhy] = useState(false);
  const inputType =
    field.type === "email" ? "email" : field.type === "tel" ? "tel" : "text";
  const whyId = `decl-${field.name}-why`;

  return (
    <div>
      {/* Label left, affordances right: nine of these stack, so the "Pourquoi ?"
          controls need to land in one predictable column rather than trailing
          help text of nine different lengths. */}
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        <label htmlFor={`decl-${field.name}`} className="t-label text-[var(--ink)]">
          {field.label_fr}
          {!field.required && (
            <span className="font-normal text-[var(--ink-faint)]"> (facultatif)</span>
          )}
        </label>
        <span className="ar text-[0.75rem] text-[var(--ink-faint)]">
          {field.label_ar}
        </span>

        {field.why_fr && (
          <button
            type="button"
            onClick={() => setShowWhy((open) => !open)}
            aria-expanded={showWhy}
            aria-controls={whyId}
            className="ms-auto inline-flex shrink-0 items-center gap-0.5 text-[0.75rem] font-medium text-[var(--teal-ink)] underline-offset-2 hover:underline"
          >
            Pourquoi&nbsp;?
            <ChevronDown
              size={12}
              strokeWidth={2.2}
              aria-hidden
              className={`transition-transform ${showWhy ? "rotate-180" : ""}`}
            />
          </button>
        )}
      </div>

      <input
        id={`decl-${field.name}`}
        type={inputType}
        inputMode={field.type === "id" ? "numeric" : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1.5 w-full rounded-[var(--r-control)] border border-[var(--line-strong)] bg-[var(--surface)] px-3 py-2.5 text-[0.9375rem] outline-none focus:border-[var(--teal)]"
      />

      {field.compared_with_fr && (
        <p className="mt-1.5 flex items-start gap-1.5 text-[0.75rem] leading-relaxed text-[var(--teal-ink)]">
          <GitCompareArrows size={12} strokeWidth={2.1} className="mt-0.5 shrink-0" aria-hidden />
          <span>
            Recoupé avec <span className="font-medium">{field.compared_with_fr}</span>
          </span>
        </p>
      )}

      {field.help_fr && (
        <p className="mt-1.5 text-[0.75rem] text-[var(--ink-faint)]">{field.help_fr}</p>
      )}

      {field.why_fr && (
        <div
          id={whyId}
          hidden={!showWhy}
          className="mt-2 rounded-[var(--r-control)] border-l-2 border-[var(--teal)] bg-[var(--canvas)] px-3 py-2"
        >
          <p className="text-[0.75rem] leading-relaxed text-[var(--ink-muted)]">
            {field.why_fr}
          </p>
          {field.why_ar && (
            <p className="ar ar-left mt-1.5 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
              {field.why_ar}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
