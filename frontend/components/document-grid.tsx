"use client";

import { AlertTriangle, FileText } from "lucide-react";
import { useState } from "react";

import { API_URL } from "@/lib/api";
import { DOCUMENT_SHORT_FR } from "@/lib/status";

/**
 * The dossier's pages, as pages.
 *
 * A row of tab chips names the pieces but shows none of them, so choosing one
 * to look at means reading labels and guessing. A grid of thumbnails is the
 * dossier as it sits on a desk: the officer picks the page they mean, and the
 * count on each card says how much is wrong with it before they open it.
 *
 * Each thumbnail is the page render endpoint, which rasterises a PDF at the
 * same DPI the evidence boxes are measured against — so what a card shows is
 * what an overlay would be drawn on.
 */
export function DocumentGrid({
  submissionId,
  documentKeys,
  flagCounts,
  selected,
  onSelect,
}: {
  submissionId: string;
  documentKeys: string[];
  /** How many findings name each document. */
  flagCounts: Record<string, number>;
  selected: string | null;
  onSelect: (key: string) => void;
}) {
  return (
    <ul className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
      {documentKeys.map((key) => (
        <li key={key}>
          <DocumentCard
            submissionId={submissionId}
            documentKey={key}
            flagCount={flagCounts[key] ?? 0}
            active={selected === key}
            onSelect={() => onSelect(key)}
          />
        </li>
      ))}
    </ul>
  );
}

function DocumentCard({
  submissionId,
  documentKey,
  flagCount,
  active,
  onSelect,
}: {
  submissionId: string;
  documentKey: string;
  flagCount: number;
  active: boolean;
  onSelect: () => void;
}) {
  const [failed, setFailed] = useState(false);
  const label = DOCUMENT_SHORT_FR[documentKey] ?? documentKey;
  const src = `${API_URL}/submissions/${submissionId}/pages/${documentKey}/0.png`;

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      className={`group w-full overflow-hidden rounded-[var(--r-panel)] border text-left transition-colors ${
        active
          ? "border-[var(--navy)] bg-[var(--surface)] ring-2 ring-[var(--navy)]/12"
          : "border-[var(--line)] bg-[var(--surface)] hover:border-[var(--line-strong)]"
      }`}
    >
      <span className="relative flex h-28 items-center justify-center overflow-hidden bg-[var(--canvas)]">
        {failed ? (
          <FileText size={22} strokeWidth={1.6} className="text-[var(--ink-faint)]" aria-hidden />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={src}
            alt=""
            loading="lazy"
            onError={() => setFailed(true)}
            // Top-anchored: a document's heading is what identifies it, and
            // centring a tall page crops exactly that away.
            className="size-full object-cover object-top"
          />
        )}
        {flagCount > 0 && (
          <span
            aria-label={`${flagCount} anomalie${flagCount > 1 ? "s" : ""}`}
            className="absolute top-1.5 right-1.5 inline-flex items-center gap-1 rounded-full bg-[var(--st-correction-wash)] px-1.5 py-0.5 text-[0.6875rem] font-semibold text-[var(--st-correction-ink)] tabular-nums"
          >
            <AlertTriangle size={10} strokeWidth={2.4} aria-hidden />
            {flagCount}
          </span>
        )}
      </span>

      <span className="block border-t border-[var(--line)] px-2.5 py-2">
        <span
          className={`block truncate text-[0.75rem] font-medium ${
            active ? "text-[var(--navy)]" : "text-[var(--ink)]"
          }`}
        >
          {label}
        </span>
      </span>
    </button>
  );
}
