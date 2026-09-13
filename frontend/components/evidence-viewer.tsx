"use client";

import { Loader2, ScanSearch, X } from "lucide-react";
import { useEffect, useState } from "react";

import { API_URL, flagEvidence } from "@/lib/api";
import type { FlagEvidence } from "@/lib/types";

/**
 * The page, with the disputed value boxed on it.
 *
 * A verdict that says two documents disagree about a CIN asks to be believed.
 * This is how it stops asking: the reader sees the pixels the finding came
 * from, on the document they uploaded, with the value outlined.
 *
 * When nothing could be located the page is still shown, with a line saying so.
 * That is the honest failure -- a box drawn over the wrong part of the page
 * would be worse than no box, because the whole point is verification.
 */
export function EvidenceViewer({
  submissionId,
  code,
  title,
  onClose,
}: {
  submissionId: string;
  code: string;
  title: string;
  onClose: () => void;
}) {
  const [evidence, setEvidence] = useState<FlagEvidence | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    flagEvidence(submissionId, code)
      .then((found) => live && setEvidence(found))
      .catch(
        (e) =>
          live &&
          setError(
            e instanceof Error ? e.message : "La pièce n'a pas pu être affichée.",
          ),
      );
    return () => {
      live = false;
    };
  }, [submissionId, code]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Pièce concernée — ${title}`}
      className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-[var(--navy)]/55 p-4 backdrop-blur-sm sm:p-8"
      onClick={(event) => event.target === event.currentTarget && onClose()}
    >
      <div className="w-full max-w-4xl rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] shadow-[0_24px_64px_-20px_rgba(14,39,71,0.5)]">
        <div className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-3.5">
          <div className="min-w-0">
            <p className="t-label text-[var(--ink-muted)]">Pièce concernée</p>
            <p className="mt-0.5 text-[0.9375rem] leading-snug text-[var(--ink)]">
              {title}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="-mr-1.5 shrink-0 rounded-[var(--r-control)] p-1.5 text-[var(--ink-muted)] transition-colors hover:bg-[var(--canvas)] hover:text-[var(--ink)]"
          >
            <X size={17} strokeWidth={2} aria-hidden />
            <span className="sr-only">Fermer</span>
          </button>
        </div>

        <div className="p-5">
          {error && <p className="text-[0.875rem] text-[var(--ink-muted)]">{error}</p>}

          {!evidence && !error && (
            <p className="flex items-center gap-2 text-[0.875rem] text-[var(--ink-muted)]">
              <Loader2 size={15} strokeWidth={2} className="animate-spin" aria-hidden />
              Recherche de la valeur sur la pièce
            </p>
          )}

          {evidence && (
            <>
              {evidence.values.length > 0 && (
                <p className="mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-[0.8125rem] text-[var(--ink-muted)]">
                  <ScanSearch size={14} strokeWidth={2} aria-hidden />
                  {evidence.located ? "Valeurs repérées :" : "Valeurs recherchées :"}
                  {evidence.values.map((value) => (
                    <span
                      key={value}
                      className="t-data rounded-[var(--r-control)] bg-[var(--canvas)] px-1.5 py-0.5 text-[var(--ink)]"
                    >
                      {value}
                    </span>
                  ))}
                </p>
              )}

              {!evidence.located && (
                <p className="mb-4 rounded-[var(--r-control)] border-l-2 border-[var(--st-correction-ink)] bg-[var(--canvas)] px-3 py-2 text-[0.75rem] leading-relaxed text-[var(--ink-muted)]">
                  Ces valeurs n&apos;ont pas pu être localisées sur la page —
                  l&apos;écriture y est peut-être trop dégradée. La pièce est
                  affichée telle quelle&nbsp;: rien n&apos;est entouré au hasard.
                </p>
              )}

              <div className="space-y-6">
                {evidence.documents.map((document) => (
                  <figure key={document.key}>
                    <figcaption className="mb-2 flex flex-wrap items-baseline gap-2">
                      <span className="t-label text-[var(--ink)]">
                        {document.label_fr}
                      </span>
                      <span className="ar ar-left text-[0.75rem] text-[var(--ink-faint)]">
                        {document.label_ar}
                      </span>
                    </figcaption>

                    {document.pages.map((page) => (
                      <div
                        key={page.page}
                        className="relative overflow-hidden rounded-[var(--r-control)] border border-[var(--line)] bg-[var(--canvas)]"
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`${API_URL}${page.image_url}`}
                          alt={`${document.label_fr} — page ${page.page + 1}`}
                          className="block w-full"
                        />
                        {/* Boxes are fractions of the page, so the overlay
                            tracks the image at whatever width it renders. */}
                        {page.boxes.map((box, index) => (
                          <span
                            key={index}
                            title={box.text}
                            className="pointer-events-none absolute rounded-[2px] border-2 border-[var(--st-rejected-ink)] bg-[var(--st-rejected-ink)]/12"
                            style={{
                              left: `${box.x * 100}%`,
                              top: `${box.y * 100}%`,
                              width: `${box.width * 100}%`,
                              height: `${box.height * 100}%`,
                            }}
                          />
                        ))}
                      </div>
                    ))}
                  </figure>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
