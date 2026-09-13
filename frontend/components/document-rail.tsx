"use client";

import { Check, Paperclip, RotateCcw, X } from "lucide-react";
import { useRef } from "react";

import { FilePreview } from "@/components/file-preview";
import { DOCUMENT_SHORT_FR } from "@/lib/status";
import type { BilingualLabel } from "@/lib/types";

/**
 * The upload checklist as a grid of the pages themselves.
 *
 * It was a vertical rail: five rows of label, filename and buttons, which read
 * as a list of chores and showed nothing of what had been attached. Five cards
 * show which slots are filled at a glance and what went into each -- and a
 * folder of similarly named scans is exactly where a page ends up in the wrong
 * slot, which is the mistake that costs a full minute of OCR to discover.
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
    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {documents.map((document) => (
        <li key={document.key}>
          <DocumentCard
            document={document}
            file={files[document.key]}
            onAttach={(file) => onAttach(document.key, file)}
          />
        </li>
      ))}
    </ul>
  );
}

function DocumentCard({
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
    <div
      className={`flex h-full flex-col overflow-hidden rounded-[var(--r-panel)] border transition-colors ${
        attached
          ? "border-[var(--teal)] bg-[var(--surface)]"
          : "border-dashed border-[var(--line-strong)] bg-[var(--canvas)]"
      }`}
    >
      <div className="relative flex h-32 items-center justify-center overflow-hidden bg-[var(--canvas)]">
        {file ? (
          <FilePreview file={file} label={label} />
        ) : (
          <span className="flex flex-col items-center gap-1.5 text-[var(--ink-faint)]">
            <Paperclip size={18} strokeWidth={1.7} aria-hidden />
            <span className="text-[0.75rem]">Aucune pièce</span>
          </span>
        )}
        {attached && (
          <span
            aria-hidden
            className="absolute top-2 left-2 flex size-5 items-center justify-center rounded-full bg-[var(--teal)]"
          >
            <Check size={12} strokeWidth={3} className="text-white" />
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col justify-between gap-2 border-t border-[var(--line)] p-3">
        <div className="min-w-0">
          <p className="t-label text-[var(--ink)]">{label}</p>
          <p className="ar ar-left text-[0.6875rem] text-[var(--ink-faint)]">
            {document.label_ar}
          </p>
          {file && (
            <p className="mt-1 truncate text-[0.6875rem] text-[var(--ink-faint)]">
              {file.name}
            </p>
          )}
        </div>

        <div className="flex items-center gap-1">
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
            className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-[var(--r-control)] border border-[var(--line-strong)] px-2 py-1.5 text-[0.75rem] font-medium text-[var(--ink)] transition-colors hover:border-[var(--teal)] hover:bg-[var(--surface)]"
          >
            {attached ? (
              <>
                <RotateCcw size={12} strokeWidth={2} aria-hidden />
                Remplacer
              </>
            ) : (
              <>
                <Paperclip size={12} strokeWidth={2} aria-hidden />
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
              <X size={13} strokeWidth={2} aria-hidden />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
