"use client";

import { ArrowLeft, Loader2, MessagesSquare, Send, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { ActionButton } from "@/components/action-button";
import { PortalBar } from "@/components/chrome";
import { StatusTracker } from "@/components/status-tracker";
import { Notice, Panel, SectionHeading } from "@/components/ui";
import { VerdictPanel } from "@/components/verdict-panel";
import { openAssistant, setActiveSubmission } from "@/lib/active-submission";
import { correctSubmission, getSubmission, submitForReview } from "@/lib/api";
import { DOCUMENT_SHORT_FR } from "@/lib/status";
import type { Submission, SubmissionResult } from "@/lib/types";

/**
 * One of your own dossiers, reopened.
 *
 * A filing used to be reachable only from the tab that created it, and a
 * correction meant starting again as a new dossier -- losing the id the
 * registry had been given and the decisions attached to it. This is the way
 * back in: the verdict as it stands, what an officer asked for, and the
 * documents that need replacing, replaced in place.
 */
export function DossierDetail({ submissionId }: { submissionId: string }) {
  const [dossier, setDossier] = useState<Submission | null>(null);
  const [error, setError] = useState("");
  const [replacements, setReplacements] = useState<Record<string, File>>({});
  const [working, setWorking] = useState<"" | "correcting" | "submitting">("");
  const [note, setNote] = useState("");

  const load = useCallback(() => {
    getSubmission(submissionId)
      .then(setDossier)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Ce dossier n'a pas pu être chargé."),
      );
  }, [submissionId]);

  useEffect(load, [load]);

  // The floating assistant answers about whichever dossier is on screen.
  useEffect(() => {
    setActiveSubmission(submissionId);
    return () => setActiveSubmission(null);
  }, [submissionId]);

  if (error && !dossier) {
    return (
      <Shell>
        <Notice>{error}</Notice>
      </Shell>
    );
  }

  if (!dossier) {
    return (
      <Shell>
        <p className="flex items-center gap-2 text-[0.875rem] text-[var(--ink-muted)]">
          <Loader2 size={15} strokeWidth={2} className="animate-spin" aria-hidden />
          Chargement du dossier
        </p>
      </Shell>
    );
  }

  // VerdictPanel speaks the shape the check endpoint returns; a stored dossier
  // carries the same facts under different names.
  const asResult: SubmissionResult = {
    submission_id: dossier.id,
    status: dossier.status,
    required_documents: Object.keys(dossier.documents),
    completeness: dossier.completeness,
    flags: dossier.flags,
    flag_summary: {
      total: dossier.flag_count,
      errors: dossier.error_flag_count,
      warnings: dossier.flag_count - dossier.error_flag_count,
      info: 0,
    },
  };

  const decided = dossier.status === "APPROVED" || dossier.status === "REJECTED";
  const lastReview = dossier.reviews.at(-1);

  // Which pages are worth offering to replace: the ones a finding names, plus
  // any that are missing outright.
  const flagged = new Set<string>();
  for (const flag of dossier.flags) {
    for (const document of flag.documents ?? []) flagged.add(document.key);
  }
  for (const missing of dossier.completeness.missing_documents ?? []) {
    flagged.add(missing.key);
  }
  const replaceable = Array.from(
    new Set([...flagged, ...Object.keys(dossier.documents)]),
  );

  async function correct() {
    setWorking("correcting");
    setError("");
    setNote("");
    try {
      const documents = Object.entries(replacements).map(([documentType, file]) => ({
        documentType,
        file,
      }));
      const result = await correctSubmission(dossier!.id, documents);
      setReplacements({});
      setNote(
        `${result.replaced.length} pièce${result.replaced.length > 1 ? "s" : ""} remplacée${
          result.replaced.length > 1 ? "s" : ""
        }. Le dossier a été revérifié.`,
      );
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "La correction n'a pas abouti.");
    } finally {
      setWorking("");
    }
  }

  async function transmit() {
    setWorking("submitting");
    setError("");
    try {
      await submitForReview(dossier!.id);
      setNote("Dossier transmis au registre.");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Le dépôt n'a pas abouti.");
    } finally {
      setWorking("");
    }
  }

  return (
    <Shell>
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h1 className="t-h2 text-[var(--navy)]">
          {dossier.completeness.display_name_fr}
        </h1>
        <p className="t-data text-[0.75rem] text-[var(--ink-faint)]">{dossier.id}</p>
      </div>

      <div className="mt-5">
        <StatusTracker status={dossier.status} />
      </div>

      {lastReview?.note && (
        <div className="mt-6 rounded-[var(--r-panel)] border-l-2 border-[var(--st-correction-ink)] bg-[var(--st-correction-wash)] p-4">
          <p className="t-label text-[var(--st-correction-ink)]">
            Message de l&apos;agent du registre
          </p>
          <p className="mt-1.5 text-[0.875rem] leading-relaxed text-[var(--ink)]">
            {lastReview.note}
          </p>
        </div>
      )}

      {note && (
        <div className="mt-6">
          <Notice tone="info">{note}</Notice>
        </div>
      )}
      {error && (
        <div className="mt-6">
          <Notice>{error}</Notice>
        </div>
      )}

      <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1fr_1fr] lg:gap-8">
        <section>
          <SectionHeading>Résultat de la vérification</SectionHeading>
          <VerdictPanel result={asResult} />
        </section>

        <section>
          <SectionHeading
            hint={decided ? undefined : "Remplacez une pièce et nous revérifions"}
          >
            Corriger le dossier
          </SectionHeading>

          {decided ? (
            <Panel className="p-5 text-[0.875rem] leading-relaxed text-[var(--ink-muted)]">
              Ce dossier a été tranché par un agent. Ses pièces ne peuvent plus
              être modifiées&nbsp;: un dossier décidé est un enregistrement, et
              changer les pièces sous une décision ferait décrire à cette
              décision quelque chose qui n&apos;existe plus. Déposez un nouveau
              dossier si nécessaire.
            </Panel>
          ) : (
            <Panel className="p-5">
              <ul className="space-y-3">
                {replaceable.map((key) => {
                  const isFlagged = flagged.has(key);
                  const chosen = replacements[key];
                  return (
                    <li
                      key={key}
                      className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2"
                    >
                      <span className="min-w-0">
                        <span className="block text-[0.875rem] text-[var(--ink)]">
                          {DOCUMENT_SHORT_FR[key] ?? key}
                        </span>
                        {isFlagged && (
                          <span className="text-[0.75rem] text-[var(--st-correction-ink)]">
                            Signalée
                          </span>
                        )}
                        {chosen && (
                          <span className="block truncate text-[0.75rem] text-[var(--teal-ink)]">
                            {chosen.name}
                          </span>
                        )}
                      </span>
                      <label className="inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-[var(--r-control)] border border-[var(--line-strong)] px-2.5 py-1.5 text-[0.75rem] font-medium text-[var(--ink)] transition-colors hover:border-[var(--teal)]">
                        <Upload size={13} strokeWidth={2} aria-hidden />
                        {chosen ? "Changer" : "Remplacer"}
                        <input
                          type="file"
                          className="sr-only"
                          accept="image/png,image/jpeg,application/pdf"
                          onChange={(event) => {
                            const file = event.target.files?.[0];
                            if (file) {
                              setReplacements((current) => ({ ...current, [key]: file }));
                            }
                          }}
                        />
                      </label>
                    </li>
                  );
                })}
              </ul>

              <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-[var(--line)] pt-4">
                <ActionButton
                  onClick={correct}
                  disabled={working !== "" || Object.keys(replacements).length === 0}
                >
                  <Upload size={17} strokeWidth={1.9} aria-hidden />
                  {working === "correcting"
                    ? "Vérification en cours"
                    : "Remplacer et revérifier"}
                </ActionButton>
                <ActionButton onClick={transmit} disabled={working !== ""} variant="teal">
                  <Send size={17} strokeWidth={1.9} aria-hidden />
                  {working === "submitting" ? "Transmission" : "Transmettre au registre"}
                </ActionButton>
              </div>
              <p className="mt-3 text-[0.75rem] leading-relaxed text-[var(--ink-faint)]">
                Une pièce remplacée rejoint le dossier existant&nbsp;: son
                numéro et son historique sont conservés. Après correction, le
                dossier doit être transmis à nouveau.
              </p>
            </Panel>
          )}

          <button
            type="button"
            onClick={openAssistant}
            className="mt-4 inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
          >
            <MessagesSquare size={15} strokeWidth={2} aria-hidden />
            Demander à l&apos;assistant ce qu&apos;il faut changer
          </button>
        </section>
      </div>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
        <div className="mb-5 border-b border-[var(--line)] pb-4">
          <Link
            href="/msme/dossiers"
            className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
          >
            <ArrowLeft size={15} strokeWidth={2} aria-hidden />
            Mes dossiers
          </Link>
        </div>
        {children}
      </main>
    </div>
  );
}
