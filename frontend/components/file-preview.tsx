"use client";

import { FileText, Maximize2, X } from "lucide-react";
import { useEffect, useState } from "react";

/**
 * What you actually attached, before anything is sent.
 *
 * A filename is not a preview. Five slots filled from a folder of similarly
 * named scans is exactly where a page ends up in the wrong one, and the check
 * that catches it costs a minute of OCR. Seeing the page is cheaper.
 *
 * The blob URL is created once per file and revoked when the file changes or
 * the row unmounts: an un-revoked object URL pins the whole file in memory,
 * and five scans is tens of megabytes held for as long as the tab lives.
 */
function useObjectUrl(file: File): string | null {
  const [url, setUrl] = useState<string | null>(null);

  // Creating and revoking must happen in the same effect, as one pair.
  //
  // Deriving the URL with useMemo and revoking it in a separate cleanup looks
  // tidier and is broken: React invokes effects twice in development, so the
  // first cleanup revokes a URL useMemo will not recreate, and every preview
  // renders as a broken image. Caught by checking naturalWidth rather than by
  // looking at a screenshot, where an empty 44px box reads as a light one.
  //
  // This is the case the rule below exists to allow -- synchronising React
  // with an external resource that has a lifetime -- so it is disabled here
  // rather than worked around.
  useEffect(() => {
    const created = URL.createObjectURL(file);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setUrl(created);
    return () => URL.revokeObjectURL(created);
  }, [file]);

  return url;
}

function isImage(file: File): boolean {
  return file.type.startsWith("image/");
}

/** A small view of the attached page, opening the full one on click. */
export function FileThumbnail({ file, label }: { file: File; label: string }) {
  const url = useObjectUrl(file);
  const [open, setOpen] = useState(false);

  const size =
    file.size > 1024 * 1024
      ? `${(file.size / 1024 / 1024).toFixed(1)} Mo`
      : `${Math.round(file.size / 1024)} ko`;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="group flex w-[13.5rem] items-center gap-2.5 rounded-[var(--r-control)] border border-[var(--line)] bg-[var(--surface)] p-1.5 pr-3 text-left transition-colors hover:border-[var(--teal)]"
        aria-label={`Aperçu : ${label}`}
      >
        <span className="relative flex size-11 shrink-0 items-center justify-center overflow-hidden rounded-[4px] bg-[var(--canvas)]">
          {url && isImage(file) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={url} alt="" className="size-full object-cover" />
          ) : (
            <FileText size={17} strokeWidth={1.8} className="text-[var(--ink-faint)]" aria-hidden />
          )}
          <span className="absolute inset-0 flex items-center justify-center bg-[var(--navy)]/0 text-white opacity-0 transition-all group-hover:bg-[var(--navy)]/45 group-hover:opacity-100">
            <Maximize2 size={14} strokeWidth={2.2} aria-hidden />
          </span>
        </span>
        <span className="min-w-0">
          <span className="block truncate text-[0.75rem] font-medium text-[var(--ink)]">
            {file.name}
          </span>
          <span className="block text-[0.6875rem] text-[var(--ink-faint)]">
            {size} · voir
          </span>
        </span>
      </button>

      {open && url && (
        <FileViewer file={file} url={url} label={label} onClose={() => setOpen(false)} />
      )}
    </>
  );
}

function FileViewer({
  file,
  url,
  label,
  onClose,
}: {
  file: File;
  url: string;
  label: string;
  onClose: () => void;
}) {
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
      aria-label={`Aperçu — ${label}`}
      onClick={(event) => event.target === event.currentTarget && onClose()}
      className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto bg-[var(--navy)]/55 p-4 backdrop-blur-sm sm:p-8"
    >
      <div className="w-full max-w-3xl rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] shadow-[0_24px_64px_-20px_rgba(14,39,71,0.5)]">
        <div className="flex items-start justify-between gap-4 border-b border-[var(--line)] px-5 py-3.5">
          <div className="min-w-0">
            <p className="t-label text-[var(--ink-muted)]">{label}</p>
            <p className="mt-0.5 truncate text-[0.875rem] text-[var(--ink)]">{file.name}</p>
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

        <div className="p-4">
          {isImage(file) ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={url}
              alt={label}
              className="mx-auto block max-h-[72vh] w-auto rounded-[var(--r-control)] border border-[var(--line)]"
            />
          ) : (
            // A PDF is rendered by the browser's own viewer; nothing to ship.
            <iframe
              src={url}
              title={`Aperçu — ${label}`}
              className="h-[72vh] w-full rounded-[var(--r-control)] border border-[var(--line)]"
            />
          )}
          <p className="mt-3 text-[0.75rem] text-[var(--ink-faint)]">
            Ce fichier n&apos;a pas encore quitté votre appareil.
          </p>
        </div>
      </div>
    </div>
  );
}
