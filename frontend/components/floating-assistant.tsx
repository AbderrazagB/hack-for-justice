"use client";

import { MessagesSquare, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { useEffect, useId } from "react";

import { AssistantPanel } from "@/components/assistant-panel";
import { setAssistantOpen, useAssistantState } from "@/lib/active-submission";

// The officer dashboard and the auth screens are not places to ask about a
// filing, so the widget stays out of them rather than following every route.
const HIDDEN_ON = ["/admin", "/login", "/signup"];

/**
 * The assistant, reachable from anywhere in the applicant-facing app.
 *
 * It answers; it never decides. The verdict on a filing always comes from the
 * deterministic rules engine, and every procedural fact the assistant states
 * comes from retrieved RNE text that it cites. Opened with a filing in hand it
 * explains that filing's result; opened cold it answers about the procedure and
 * says nothing about documents it has not seen.
 */
export function FloatingAssistant() {
  const pathname = usePathname();
  const { submissionId, open } = useAssistantState();
  const panelId = useId();

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setAssistantOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  if (HIDDEN_ON.some((prefix) => pathname.startsWith(prefix))) return null;

  return (
    <>
      <div
        id={panelId}
        hidden={!open}
        className="fixed inset-x-3 bottom-[4.75rem] z-50 sm:inset-x-auto sm:right-6 sm:bottom-[5.25rem] sm:w-[25rem]"
      >
        <div className="flex max-h-[min(32rem,70vh)] flex-col overflow-hidden rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(14,39,71,0.06),0_20px_48px_-16px_rgba(14,39,71,0.32)]">
          <div className="flex items-start justify-between gap-3 bg-[var(--navy)] px-5 py-3 text-white">
            <div className="min-w-0">
              <p className="t-label text-white">Assistant</p>
              <p className="mt-0.5 text-[0.75rem] leading-relaxed text-white/70">
                {submissionId
                  ? "Répond sur le dossier que vous venez de vérifier, d'après les textes du RNE."
                  : "Répond d'après les textes officiels du RNE, et cite ses sources."}
              </p>
            </div>
            <button
              type="button"
              onClick={() => setAssistantOpen(false)}
              className="-mr-1.5 -mt-0.5 shrink-0 rounded-[var(--r-control)] p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X size={16} strokeWidth={2} aria-hidden />
              <span className="sr-only">Fermer l&apos;assistant</span>
            </button>
          </div>

          <AssistantPanel submissionId={submissionId} floating />
        </div>
      </div>

      <button
        type="button"
        onClick={() => setAssistantOpen(!open)}
        aria-expanded={open}
        aria-controls={panelId}
        className="fixed right-5 bottom-5 z-50 inline-flex items-center gap-2 rounded-full bg-[var(--navy)] px-4 py-3 text-[0.8125rem] font-medium text-white shadow-[0_8px_24px_-6px_rgba(14,39,71,0.45)] transition-colors hover:bg-[var(--navy-deep)] sm:right-6 sm:bottom-6"
      >
        {open ? (
          <X size={17} strokeWidth={2} aria-hidden />
        ) : (
          <MessagesSquare size={17} strokeWidth={1.9} aria-hidden />
        )}
        <span className={open ? "sr-only" : ""}>
          {open ? "Fermer l'assistant" : "Besoin d'aide ?"}
        </span>
      </button>
    </>
  );
}
