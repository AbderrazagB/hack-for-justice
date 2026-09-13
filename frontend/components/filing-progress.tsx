"use client";

import { Check, FileSearch, Loader2 } from "lucide-react";

import type { UploadProgress } from "@/lib/types";

/**
 * What the server is doing, while it does it.
 *
 * Reading five pages through a vision model takes over a minute. The only sign
 * of life used to be a button whose label had changed, which is indisputably
 * true and tells a waiting person nothing: not how far along, not whether
 * anything is happening, not how much longer.
 *
 * Every number here comes from the server's own count of documents it has
 * finished reading. Nothing is animated forward on a timer to look busy -- a
 * bar that advances while a request is hung is worse than no bar.
 */
export function FilingProgress({
  progress,
  documents,
  elapsedSeconds,
}: {
  progress: UploadProgress | null;
  documents: { key: string; label_fr: string }[];
  elapsedSeconds: number;
}) {
  const done = progress?.done ?? 0;
  const total = progress?.total || documents.length;
  const stage = progress?.stage ?? "upload";
  const percent = total ? Math.round((done / total) * 100) : 0;

  const heading =
    stage === "checking"
      ? "Application des règles du registre"
      : stage === "done"
        ? "Vérification terminée"
        : done > 0 || stage === "reading"
          ? `Lecture des pièces — ${done} sur ${total}`
          : "Envoi des pièces";

  return (
    <div className="rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-5">
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-[var(--teal-wash)] text-[var(--teal-ink)]"
        >
          <FileSearch size={18} strokeWidth={1.8} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="t-label text-[var(--ink)]">{heading}</p>
          <p className="mt-0.5 text-[0.75rem] text-[var(--ink-faint)]">
            Chaque page est lue une fois. Comptez une quinzaine de secondes par
            pièce — {elapsedSeconds}s écoulées.
          </p>
        </div>
      </div>

      <div
        className="mt-4 h-1.5 overflow-hidden rounded-full bg-[var(--canvas)]"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Progression de la vérification"
      >
        <div
          className="h-full rounded-full bg-[var(--teal)] transition-[width] duration-500"
          style={{ width: `${stage === "checking" || stage === "done" ? 100 : percent}%` }}
        />
      </div>

      <ul className="mt-4 space-y-2">
        {documents.map((document, index) => {
          const finished = index < done;
          const active =
            !finished && (progress?.current === document.key || index === done);
          return (
            <li
              key={document.key}
              className={`flex items-center gap-2.5 text-[0.8125rem] ${
                finished
                  ? "text-[var(--ink-muted)]"
                  : active
                    ? "text-[var(--ink)]"
                    : "text-[var(--ink-faint)]"
              }`}
            >
              <span aria-hidden className="flex size-4 shrink-0 items-center justify-center">
                {finished ? (
                  <Check size={14} strokeWidth={2.6} className="text-[var(--teal-ink)]" />
                ) : active ? (
                  <Loader2 size={13} strokeWidth={2.4} className="animate-spin" />
                ) : (
                  <span className="size-1.5 rounded-full bg-[var(--line-strong)]" />
                )}
              </span>
              {document.label_fr}
            </li>
          );
        })}
      </ul>

      {stage === "checking" && (
        <p className="mt-4 flex items-center gap-2 border-t border-[var(--line)] pt-3 text-[0.8125rem] text-[var(--ink)]">
          <Loader2 size={13} strokeWidth={2.4} className="animate-spin" aria-hidden />
          Comparaison des pièces entre elles et avec votre déclaration
        </p>
      )}
    </div>
  );
}
