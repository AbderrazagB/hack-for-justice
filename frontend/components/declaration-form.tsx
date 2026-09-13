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
 *
 * One question per row, which is what a form meant to be filled from top to
 * bottom should be -- two columns were tried here and reverted: they force a
 * reader to decide where to look next at every row, and the pairing is
 * arbitrary because the questions are not pairs.
 *
 * The height that cost is taken back elsewhere. Each input is drawn at the
 * width of the answer expected in it, so a row is a short box and a label
 * rather than a full-bleed field; and the standing help line folded into the
 * "Pourquoi ?" disclosure, which said roughly the same thing at greater length.
 */
export type DeclarationGroup = {
  key: string;
  label_fr: string;
  label_ar: string;
  fields: DeclarationField[];
};

/**
 * The nine entries, split into the sections the official form's own ordering
 * already groups them into. Exported because the page pages through them: a
 * backend test holds that each group stays contiguous, so this never reorders
 * the form.
 */
export function declarationGroups(fields: DeclarationField[]): DeclarationGroup[] {
  const groups: DeclarationGroup[] = [];
  for (const field of fields) {
    const last = groups[groups.length - 1];
    if (last && last.key === field.group) last.fields.push(field);
    else
      groups.push({
        key: field.group,
        label_fr: field.group_fr,
        label_ar: field.group_ar,
        fields: [field],
      });
  }
  return groups;
}

export function DeclarationForm({
  fields,
  values,
  onChange,
  modificationType,
  modificationTypeAr,
  groupIndex,
}: {
  fields: DeclarationField[];
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
  modificationType: string | null;
  modificationTypeAr: string | null;
  /** Which section to show. The rest are not rendered. */
  groupIndex: number;
}) {
  if (fields.length === 0) return null;

  const groups = declarationGroups(fields);
  const index = Math.min(Math.max(groupIndex, 0), groups.length - 1);
  const section = groups[index];
  const comparedCount = fields.filter((field) => field.cross_checked).length;
  // The preamble earns its height once. After the first section it is in the
  // way of the questions it was introducing.
  const first = index === 0;

  return (
    <Panel className="p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="flex items-start gap-3">
          <span
            aria-hidden
            className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-[var(--teal-wash)] text-[var(--teal-ink)]"
          >
            <FileSignature size={18} strokeWidth={1.8} />
          </span>
          <div className="min-w-0">
            <h2 className="t-h3 text-[var(--navy)]">{section.label_fr}</h2>
            <p className="ar ar-left text-[0.8125rem] text-[var(--ink-faint)]">
              {section.label_ar}
            </p>
          </div>
        </div>

        {/* Where you are inside the declaration. The step bar above says
            "Votre déclaration"; this says which part of it. */}
        <div className="flex items-center gap-2">
          <span className="t-data text-[0.75rem] text-[var(--ink-muted)]">
            {index + 1} / {groups.length}
          </span>
          <span className="flex gap-1" aria-hidden>
            {groups.map((group, position) => (
              <span
                key={group.key}
                className={`h-1.5 rounded-full transition-all ${
                  position === index
                    ? "w-5 bg-[var(--navy)]"
                    : position < index
                      ? "w-1.5 bg-[var(--navy)]"
                      : "w-1.5 bg-[var(--line-strong)]"
                }`}
              />
            ))}
          </span>
        </div>
      </div>

      {first && (
        <>
          <p className="mt-3 text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
            Le formulaire officiel RNE-F-005, posé en questions. Vous n&apos;avez
            ni à le télécharger ni à le déchiffrer&nbsp;: répondez ici, nous le
            remplissons.
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 rounded-[var(--r-control)] bg-[var(--canvas)] px-3 py-2.5 text-[0.75rem]">
            {/* The obvious objection -- "pourquoi me demander ce qui figure déjà
                sur mes pièces ?" -- answered where it is raised. */}
            <span className="flex items-center gap-1.5 text-[var(--ink-muted)]">
              <GitCompareArrows
                size={13}
                strokeWidth={2}
                className="shrink-0 text-[var(--teal-ink)]"
                aria-hidden
              />
              <span>
                <strong className="font-medium text-[var(--ink)]">
                  {comparedCount} réponses
                </strong>{" "}
                sont recoupées avec vos pièces — d&apos;où la comparaison qui
                détecte les contradictions.
              </span>
            </span>
            {modificationType && (
              <span className="flex flex-wrap items-center gap-x-2 text-[var(--ink-muted)]">
                <span>Nature&nbsp;:</span>
                <span className="font-medium text-[var(--navy)]">
                  {modificationType}
                </span>
                {modificationTypeAr && (
                  <span className="ar text-[var(--ink-faint)]">
                    {modificationTypeAr}
                  </span>
                )}
              </span>
            )}
          </div>
        </>
      )}

      <div className="mt-5 space-y-4">
        {section.fields.map((field) => (
          <Field
            key={field.name}
            field={field}
            value={values[field.name] ?? ""}
            onChange={(value) => onChange(field.name, value)}
          />
        ))}
      </div>

      {index === groups.length - 1 && (
        <p className="mt-5 flex items-start gap-2 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
          <Info size={12} strokeWidth={1.8} className="mt-0.5 shrink-0" aria-hidden />
          Le formulaire officiel précise que toute donnée manquante entraîne le
          rejet de la demande.
        </p>
      )}
    </Panel>
  );
}

/**
 * An input as wide as the answer expected in it. An eight-digit CIN in a box
 * built for a street address invites the wrong answer; the backend says which
 * of the three sizes each entry takes.
 */
const WIDTHS: Record<string, string> = {
  sm: "max-w-[11rem]",
  md: "max-w-[20rem]",
  lg: "max-w-[28rem]",
};

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
  const hasNote = Boolean(field.help_fr || field.why_fr);

  return (
    <div className="min-w-0">
      {/* Label left, disclosure right: the controls land in one predictable
          column instead of trailing help text of nine different lengths. */}
      <div className="flex max-w-[28rem] items-baseline gap-x-2">
        <label
          htmlFor={`decl-${field.name}`}
          className="t-label shrink-0 text-[var(--ink)]"
        >
          {field.label_fr}
          {!field.required && (
            <span className="font-normal text-[var(--ink-faint)]"> (facultatif)</span>
          )}
        </label>
        {/* The Arabic label yields first: truncating it keeps every label row to
            exactly one line, which is what makes a two-column grid of them read
            as a grid rather than as a ragged list. */}
        <span className="ar min-w-0 flex-1 truncate text-[0.75rem] text-[var(--ink-faint)]">
          {field.label_ar}
        </span>

        {hasNote && (
          <button
            type="button"
            onClick={() => setShowWhy((open) => !open)}
            aria-expanded={showWhy}
            aria-controls={whyId}
            className="inline-flex shrink-0 items-center gap-0.5 text-[0.75rem] font-medium text-[var(--teal-ink)] underline-offset-2 hover:underline"
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
        className={`mt-1.5 w-full rounded-[var(--r-control)] border border-[var(--line-strong)] bg-[var(--surface)] px-3 py-2.5 text-[0.9375rem] outline-none focus:border-[var(--teal)] ${WIDTHS[field.width] ?? WIDTHS.md}`}
      />

      {field.compared_with_fr && (
        <p className="mt-1.5 flex items-start gap-1.5 text-[0.75rem] leading-snug text-[var(--teal-ink)]">
          <GitCompareArrows size={12} strokeWidth={2.1} className="mt-0.5 shrink-0" aria-hidden />
          <span>
            Recoupé&nbsp;: <span className="font-medium">{field.compared_with_fr}</span>
          </span>
        </p>
      )}

      {hasNote && (
        <div
          id={whyId}
          hidden={!showWhy}
          className="mt-2 rounded-[var(--r-control)] border-l-2 border-[var(--teal)] bg-[var(--canvas)] px-3 py-2"
        >
          {/* help_fr says what the entry is, why_fr says why it is asked. Both
              lived on screen at all times and said much the same thing; they
              are one disclosure now. */}
          {field.help_fr && (
            <p className="text-[0.75rem] leading-relaxed font-medium text-[var(--ink)]">
              {field.help_fr}
            </p>
          )}
          {field.why_fr && (
            <p
              className={`text-[0.75rem] leading-relaxed text-[var(--ink-muted)] ${
                field.help_fr ? "mt-1" : ""
              }`}
            >
              {field.why_fr}
            </p>
          )}
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
