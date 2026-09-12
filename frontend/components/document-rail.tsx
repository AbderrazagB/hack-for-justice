"use client";

import { Check, Paperclip, RotateCcw, X } from "lucide-react";
import { useRef } from "react";

import { DOCUMENT_SHORT_FR } from "@/lib/status";
import type { BilingualLabel } from "@/lib/types";

/**
 * The upload checklist as a vertical rail: a connecting line with one state
 * marker per document, so how far along you are is legible without counting.
 * Structural and borderless by design — it is not a card.
 */
export function DocumentRail({
  documents,
  files,
  onAttach,
}: {
  documents: BilingualLabel[];
  files: Record<string, File>;
  onAttach: (key: string, file: File | null) => void;
}) {
  return (
    <ol className="relative">
      {/* The connecting line, behind the markers. */}
      <span
        aria-hidden
        className="absolute top-4 bottom-4 left-[11px] w-px bg-[var(--line)]"
      />
      {documents.map((document) => (
        <DocumentRow
          key={document.key}
          document={document}
          file={files[document.key]}
          onAttach={(file) => onAttach(document.key, file)}
        />
      ))}
    </ol>
  );
}

function DocumentRow({
  document,
  file,
  onAttach,
}: {
  document: BilingualLabel;
  file?: File;
  onAttach: (file: File | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const attached = Boolean(file);
  const label = DOCUMENT_SHORT_FR[document.key] ?? document.label_fr;

  return (
    <li className="relative flex gap-4 py-3.5 pl-0">
      <span
        aria-hidden
        className={`relative z-10 mt-0.5 flex size-[23px] shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
          attached
            ? "border-[var(--teal)] bg-[var(--teal)]"
            : "border-[var(--line-strong)] bg-[var(--surface)]"
        }`}
      >
        {attached && <Check size={12} strokeWidth={3} className="text-white" />}
      </span>

      <div className="flex min-w-0 flex-1 flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <div className="min-w-0">
          <p className="t-label text-[var(--ink)]">{label}</p>
          <p className="ar text-[0.75rem] text-[var(--ink-faint)]">
            {document.label_ar}
          </p>
          {file && (
            <p className="mt-0.5 truncate text-[0.75rem] text-[var(--teal-ink)]">
              {file.name}
            </p>
          )}
        </div>

        <div className="flex shrink-0 items-center gap-1">
          <input
            ref={input}
            type="file"
            accept="image/*,application/pdf"
            className="sr-only"
            aria-label={`Joindre : ${label}`}
            onChange={(event) => onAttach(event.target.files?.[0] ?? null)}
          />
          <button
            type="button"
            onClick={() => input.current?.click()}
            className="inline-flex items-center gap-1.5 rounded-[var(--r-control)] border border-[var(--line-strong)] px-2.5 py-1.5 text-[0.8125rem] font-medium text-[var(--ink)] transition-colors hover:border-[var(--ink-faint)] hover:bg-[var(--canvas)]"
          >
            {attached ? (
              <>
                <RotateCcw size={13} strokeWidth={2} aria-hidden />
                Remplacer
              </>
            ) : (
              <>
                <Paperclip size={13} strokeWidth={2} aria-hidden />
                Joindre
              </>
            )}
          </button>
          {attached && (
            <button
              type="button"
              onClick={() => {
                onAttach(null);
                if (input.current) input.current.value = "";
              }}
              aria-label={`Retirer : ${label}`}
              className="rounded-[var(--r-control)] p-1.5 text-[var(--ink-faint)] transition-colors hover:bg-[var(--canvas)] hover:text-[var(--st-rejected-ink)]"
            >
              <X size={14} strokeWidth={2} aria-hidden />
            </button>
          )}
        </div>
      </div>
    </li>
  );
}
