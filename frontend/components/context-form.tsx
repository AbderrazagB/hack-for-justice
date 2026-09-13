"use client";

import { Info } from "lucide-react";

import { Panel } from "@/components/ui";
import type { ContextField } from "@/lib/types";

/**
 * The pre-step before uploading.
 *
 * Some rules cannot be evaluated from the documents -- a company's legal form
 * and its fiscal year close are declared, not extracted. The backend describes
 * these questions in `context_fields`, so this renders whatever a workflow
 * needs without knowing which workflow it is. A transaction with no context
 * fields simply renders nothing.
 */
export function ContextForm({
  fields,
  values,
  onChange,
}: {
  fields: ContextField[];
  values: Record<string, string | boolean>;
  onChange: (name: string, value: string | boolean) => void;
}) {
  if (fields.length === 0) return null;

  const choices = fields.filter((field) => field.type !== "checkbox");
  const toggles = fields.filter((field) => field.type === "checkbox");

  return (
    <Panel className="p-5">
      <h2 className="t-h3 text-[var(--navy)]">Votre société</h2>
      <p className="ar ar-left mt-0.5 text-[0.8125rem] text-[var(--ink-faint)]">
        معلومات الشركة
      </p>
      <p className="mt-2 text-[0.8125rem] leading-relaxed text-[var(--ink-muted)]">
        Ces informations ne figurent pas dans les documents. Elles déterminent
        les pièces attendues et les délais applicables.
      </p>

      {/* Selects and dates pair up; checkboxes read as statements and keep the
          full width, so the four questions take two rows rather than four. */}
      {choices.length > 0 && (
        <div className="mt-5 grid gap-x-5 gap-y-4 sm:grid-cols-2">
          {choices.map((field) => (
            <Field
              key={field.name}
              field={field}
              value={values[field.name]}
              onChange={(value) => onChange(field.name, value)}
            />
          ))}
        </div>
      )}

      {toggles.length > 0 && (
        <div className="mt-4 space-y-3 border-t border-[var(--line)] pt-4">
          {toggles.map((field) => (
            <Field
              key={field.name}
              field={field}
              value={values[field.name]}
              onChange={(value) => onChange(field.name, value)}
            />
          ))}
        </div>
      )}
    </Panel>
  );
}

function Field({
  field,
  value,
  onChange,
}: {
  field: ContextField;
  value: string | boolean | undefined;
  onChange: (value: string | boolean) => void;
}) {
  const inputClass =
    "w-full rounded-[var(--r-control)] border border-[var(--line-strong)] bg-[var(--surface)] px-3 py-2.5 text-[0.9375rem] outline-none focus:border-[var(--teal)]";

  if (field.type === "checkbox") {
    return (
      <div>
        <label className="flex items-start gap-2.5">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(event) => onChange(event.target.checked)}
            className="mt-0.5 size-4 shrink-0 rounded border-[var(--line-strong)] accent-[var(--teal)]"
          />
          <span className="min-w-0">
            <span className="block text-[0.875rem] text-[var(--ink)]">
              {field.label_fr}
            </span>
            <span className="ar ar-left block text-[0.75rem] text-[var(--ink-faint)]">
              {field.label_ar}
            </span>
          </span>
        </label>
        {field.help_fr && <Help>{field.help_fr}</Help>}
      </div>
    );
  }

  return (
    <div>
      <label htmlFor={field.name} className="flex items-baseline gap-2">
        <span className="t-label text-[var(--ink)]">{field.label_fr}</span>
        <span className="ar text-[0.75rem] text-[var(--ink-faint)]">
          {field.label_ar}
        </span>
      </label>

      {field.type === "select" ? (
        <select
          id={field.name}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          className={`${inputClass} mt-1.5`}
        >
          <option value="">Sélectionnez…</option>
          {field.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label_fr}
            </option>
          ))}
        </select>
      ) : (
        <input
          id={field.name}
          type="date"
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          className={`${inputClass} mt-1.5`}
        />
      )}

      {field.help_fr && <Help>{field.help_fr}</Help>}
    </div>
  );
}

function Help({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-1.5 flex items-start gap-1.5 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
      <Info size={12} strokeWidth={1.8} className="mt-0.5 shrink-0" aria-hidden />
      {children}
    </p>
  );
}
