"use client";

import { AlertTriangle, Loader2, Upload } from "lucide-react";
import { useState } from "react";

import { ActionButton } from "@/components/action-button";
import { FileThumbnail } from "@/components/file-preview";
import { Notice, Panel } from "@/components/ui";
import { correctSubmission } from "@/lib/api";
import { DOCUMENT_SHORT_FR } from "@/lib/status";
import type { BilingualLabel, SubmissionResult } from "@/lib/types";

/**
 * Replace a page and re-check, without redoing the filing.
 *
 * Before this, a wrong page meant walking back through the stepper and running
 * the whole dossier through OCR again -- five pages, over a minute, to fix one.
 * Only the replaced page is read; the rest of the dossier is the rest of the
 * dossier.
 *
 * Shared by the result step and by a dossier reopened later, because they are
 * the same act: the id stays, the history stays, the verdict is recomputed.
 */
export function CorrectionPanel({
  submissionId,
  documents,
  flagged,
  disabled = false,
  disabledReason,
  onCorrected,
}: {
  submissionId: string;
  documents: BilingualLabel[];
  /** Document keys a finding names, or that are missing outright. */
  flagged: Set<string>;
  disabled?: boolean;
  disabledReason?: string;
  onCorrected: (result: SubmissionResult) => void;
}) {
  const [replacements, setReplacements] = useState<Record<string, File>>({});
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");

  if (disabled) {
    return (
      <Panel className="p-5 text-[0.875rem] leading-relaxed text-[var(--ink-muted)]">
        {disabledReason}
      </Panel>
    );
  }

  const chosen = Object.entries(replacements);

  async function apply() {
    setWorking(true);
    setError("");
    try {
      const result = await correctSubmission(
        submissionId,
        chosen.map(([documentType, file]) => ({ documentType, file })),
      );
      setReplacements({});
      onCorrected(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "La correction n'a pas abouti.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <Panel className="p-5">
      <ul className="space-y-3">
        {documents.map((document) => {
          const key = document.key;
          const label = DOCUMENT_SHORT_FR[key] ?? document.label_fr;
          const replacement = replacements[key];
          return (
            <li
              key={key}
              className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-[var(--line)] pb-3 last:border-0 last:pb-0"
            >
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-x-2 text-[0.875rem] text-[var(--ink)]">
                  {label}
                  {flagged.has(key) && (
                    <span className="inline-flex items-center gap-1 text-[0.6875rem] font-medium text-[var(--st-correction-ink)]">
                      <AlertTriangle size={11} strokeWidth={2.2} aria-hidden />
                      signalée
                    </span>
                  )}
                </span>
                <span className="ar ar-left block text-[0.75rem] text-[var(--ink-faint)]">
                  {document.label_ar}
                </span>
              </span>

              <span className="flex shrink-0 items-center gap-2">
                {replacement && <FileThumbnail file={replacement} label={label} />}
                <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-[var(--r-control)] border border-[var(--line-strong)] px-2.5 py-1.5 text-[0.75rem] font-medium text-[var(--ink)] transition-colors hover:border-[var(--teal)]">
                  <Upload size={13} strokeWidth={2} aria-hidden />
                  {replacement ? "Changer" : "Remplacer"}
                  <input
                    type="file"
                    className="sr-only"
                    accept="image/*,application/pdf"
                    aria-label={`Remplacer : ${label}`}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (file) {
                        setReplacements((current) => ({ ...current, [key]: file }));
                      }
                    }}
                  />
                </label>
              </span>
            </li>
          );
        })}
      </ul>

      {error && (
        <div className="mt-4">
          <Notice>{error}</Notice>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-[var(--line)] pt-4">
        <ActionButton onClick={apply} disabled={working || chosen.length === 0}>
          {working ? (
            <Loader2 size={17} strokeWidth={2} className="animate-spin" aria-hidden />
          ) : (
            <Upload size={17} strokeWidth={1.9} aria-hidden />
          )}
          {working
            ? "Relecture en cours"
            : `Remplacer ${chosen.length || ""} et revérifier`.replace("  ", " ")}
        </ActionButton>
        <p className="text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
          Seule la pièce remplacée est relue. Le numéro du dossier et son
          historique sont conservés.
        </p>
      </div>
    </Panel>
  );
}
