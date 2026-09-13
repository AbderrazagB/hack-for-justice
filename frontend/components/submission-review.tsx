"use client";

import { ArrowLeft, Check, FileText, RotateCcw, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Logo } from "@/components/logo";
import { ActionButton } from "@/components/action-button";
import { DocumentGrid } from "@/components/document-grid";
import { OfficerBrief } from "@/components/officer-brief";
import { StatusTracker } from "@/components/status-tracker";
import {
  EmptyState,
  Notice,
  Panel,
  SectionHeading,
  SeverityTag,
  StatusBadge,
} from "@/components/ui";
import { API_URL, reviewSubmission } from "@/lib/api";
import { DOCUMENT_SHORT_FR, SEVERITY } from "@/lib/status";
import type { ExtractedDocument, ReviewAction, Submission } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  id_number: "Numéro de CIN",
  person_name: "Nom et prénom",
  company_name: "Dénomination",
  company_id: "Identifiant unique",
  issue_date: "Date de délivrance",
  decision_date: "Date de la décision",
  signature_date: "Date de signature",
  has_signature: "Document signé",
  other_id_numbers: "Autres numéros relevés",
  notes: "Remarques de lecture",
};

export function SubmissionReview({ submission }: { submission: Submission }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const documentKeys = Object.keys(submission.documents);
  const [selected, setSelected] = useState(documentKeys[0] ?? "");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function decide(action: ReviewAction) {
    setSaving(true);
    setError("");
    try {
      await reviewSubmission(submission.id, action, note);
      setNote("");
      startTransition(() => router.refresh());
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "La décision n'a pas été enregistrée. Réessayez.",
      );
    } finally {
      setSaving(false);
    }
  }

  const document = submission.documents[selected];
  const flaggedHere = submission.flags.filter((flag) =>
    flag.documents.some((doc) => doc.key === selected),
  );
  const busy = saving || pending;

  return (
    <div className="min-h-screen">
      {/* Sticky navy sub-header: the dossier id and the way back stay reachable
          on a screen that scrolls a long way. */}
      <header className="on-navy sticky top-0 z-20 bg-[var(--navy)]">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-x-6 gap-y-2 px-4 py-3 sm:px-8">
          <div className="flex items-center gap-4">
            <Logo size="sm" tone="dark" />
            <span aria-hidden className="h-5 w-px bg-white/15" />
            <span className="t-data text-white/85">{submission.id}</span>
          </div>
          <Link
            href="/admin"
            className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal)] hover:underline"
          >
            <ArrowLeft size={15} strokeWidth={2} aria-hidden />
            Retour à la file
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-[1400px] px-4 py-8 sm:px-8">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div>
            <h1 className="t-h1">{submission.completeness.display_name_fr}</h1>
            <p className="ar mt-0.5 text-[1rem] text-[var(--ink-muted)]">
              {submission.completeness.display_name_ar}
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={submission.completeness.status} />
            <StatusBadge status={submission.status} />
          </div>
        </div>

        <div className="mt-6">
          <StatusTracker status={submission.status} />
        </div>

        {/* The dossier in one read, before the officer starts reading it. */}
        <div className="mt-7">
          <OfficerBrief submissionId={submission.id} />
        </div>

        {/* ------------------------------------------------------ findings --- */}
        <section className="mt-9">
          <SectionHeading
            hint={
              submission.flags.length
                ? `${submission.flags.length} relevée${submission.flags.length > 1 ? "s" : ""}`
                : undefined
            }
          >
            Anomalies
          </SectionHeading>

          {submission.flags.length === 0 ? (
            <div
              className="rounded-[var(--r-panel)] px-5 py-4 text-[0.875rem]"
              style={{
                background: "var(--st-approved-wash)",
                color: "var(--st-approved-ink)",
              }}
            >
              Toutes les vérifications sont passées. Aucune anomalie à signaler
              sur ce dossier.
            </div>
          ) : (
            <ul className="overflow-hidden rounded-[var(--r-panel)] border border-[var(--line)]">
              {submission.flags.map((flag, index) => (
                <li
                  key={`${flag.code}-${index}`}
                  className="border-b border-[var(--line)] last:border-b-0"
                >
                  <button
                    type="button"
                    onClick={() =>
                      flag.documents[0] && setSelected(flag.documents[0].key)
                    }
                    className="relative flex w-full gap-3 bg-[var(--surface)] py-3.5 pr-4 pl-5 text-left transition-colors hover:bg-[var(--canvas)]"
                  >
                    <span
                      aria-hidden
                      className="absolute top-0 bottom-0 left-0 w-[3px]"
                      style={{ background: SEVERITY[flag.severity].ink }}
                    />
                    <SeverityTag severity={flag.severity} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-[0.875rem] leading-relaxed">
                        {flag.message_fr}
                      </span>
                      <span className="ar mt-0.5 block text-[0.8125rem] text-[var(--ink-muted)]">
                        {flag.message_ar}
                      </span>
                      {flag.documents.length > 0 && (
                        <span className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[0.75rem] text-[var(--teal-ink)]">
                          <FileText size={12} strokeWidth={1.75} aria-hidden />
                          {flag.documents
                            .map(
                              (doc) => DOCUMENT_SHORT_FR[doc.key] ?? doc.label_fr,
                            )
                            .join("  /  ")}
                        </span>
                      )}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ------------------------------------------- document inspector --- */}
        <section className="mt-10">
          <SectionHeading hint="Données lues face au document déposé">
            Pièces du dossier
          </SectionHeading>

          {/* A grid of pages, not a row of labels: the officer picks the
              document they mean by looking at it. */}
          <DocumentGrid
            submissionId={submission.id}
            documentKeys={documentKeys}
            flagCounts={Object.fromEntries(
              documentKeys.map((key) => [
                key,
                submission.flags.filter((flag) =>
                  flag.documents.some((d) => d.key === key),
                ).length,
              ]),
            )}
            selected={selected}
            onSelect={setSelected}
          />

          {document ? (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <DocumentView document={document} />
              <FieldTable document={document} flagCount={flaggedHere.length} />
            </div>
          ) : (
            <div className="mt-4">
              <EmptyState title="Aucune pièce jointe">
                Ce dossier a été déposé sans document.
              </EmptyState>
            </div>
          )}
        </section>

        {/* --------------------------------------------------- decision --- */}
        <section className="mt-10 grid gap-4 lg:grid-cols-[1.35fr_1fr]">
          {/* The only teal-bordered element on the page: the thing the officer
              is here to do. */}
          <div className="rounded-[var(--r-panel)] border-2 border-[var(--teal)] bg-[var(--surface)] p-5">
            <h2 className="t-h3">Décision</h2>
            <label
              className="mt-3 block text-[0.8125rem] text-[var(--ink-muted)]"
              htmlFor="review-note"
            >
              Note transmise au déposant (facultative)
            </label>
            <textarea
              id="review-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              placeholder="Par exemple : fournir un Extrait RNE de moins de 90 jours."
              className="mt-1.5 w-full rounded-[var(--r-control)] border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-[0.875rem] outline-none focus:border-[var(--teal)]"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <ActionButton
                onClick={() => void decide("approve")}
                disabled={busy}
                size="sm"
              >
                <Check size={16} strokeWidth={2} aria-hidden />
                Approuver le dossier
              </ActionButton>
              <button
                type="button"
                onClick={() => void decide("request_correction")}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-[var(--r-control)] border border-[var(--line-strong)] px-4 py-2.5 text-[0.875rem] font-medium transition-colors hover:bg-[var(--canvas)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <RotateCcw size={16} strokeWidth={2} aria-hidden />
                Demander une correction
              </button>
              <button
                type="button"
                onClick={() => void decide("reject")}
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-[var(--r-control)] border border-[var(--st-rejected-ink)] px-4 py-2.5 text-[0.875rem] font-medium text-[var(--st-rejected-ink)] transition-colors hover:bg-[var(--st-rejected-wash)] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <X size={16} strokeWidth={2} aria-hidden />
                Rejeter
              </button>
            </div>
            {error && (
              <div className="mt-3">
                <Notice>{error}</Notice>
              </div>
            )}
          </div>

          <Panel className="p-5">
            <h2 className="t-h3">Historique</h2>
            {submission.reviews.length === 0 ? (
              <p className="mt-3 text-[0.875rem] text-[var(--ink-muted)]">
                Aucune décision enregistrée. Ce dossier attend un premier examen.
              </p>
            ) : (
              <ol className="mt-3 space-y-3.5">
                {submission.reviews.map((review, index) => (
                  <li key={index}>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={review.status} size="sm" />
                      <span className="text-[0.75rem] text-[var(--ink-faint)]">
                        {new Date(review.at).toLocaleString("fr-FR")}
                      </span>
                    </div>
                    <p className="mt-1 text-[0.8125rem] text-[var(--ink-muted)]">
                      Agent {review.officer}
                      {review.note ? ` — ${review.note}` : ""}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </Panel>
        </section>
      </main>
    </div>
  );
}

function DocumentView({ document }: { document: ExtractedDocument }) {
  const [unavailable, setUnavailable] = useState(false);
  const source = `${API_URL}/documents/${document.document_type}/${encodeURIComponent(document.stored_path)}`;

  return (
    <Panel className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--line)] px-4 py-2.5">
        <p className="truncate text-[0.8125rem] font-medium">
          {document.filename}
        </p>
        <span className="t-data shrink-0 text-[var(--ink-faint)]">
          {(document.size_bytes / 1024).toFixed(0)} ko
        </span>
      </div>
      <div className="flex min-h-72 items-center justify-center bg-[var(--canvas)] p-3">
        {unavailable ? (
          <p className="max-w-xs px-6 py-10 text-center text-[0.8125rem] text-[var(--ink-muted)]">
            Le fichier déposé n&apos;est plus accessible à cet emplacement. Il
            reste enregistré sous{" "}
            <span className="t-data text-[var(--ink)]">
              data/raw/{document.document_type}/{document.stored_path}
            </span>
            .
          </p>
        ) : (
          /* The applicant's own uploaded file, not decorative imagery. */
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={source}
            alt={`Pièce déposée : ${document.filename}`}
            className="max-h-[30rem] w-auto max-w-full rounded-[4px]"
            onError={() => setUnavailable(true)}
          />
        )}
      </div>
    </Panel>
  );
}

function FieldTable({
  document,
  flagCount,
}: {
  document: ExtractedDocument;
  flagCount: number;
}) {
  const entries = Object.entries(document.fields).filter(
    ([key]) => key !== "full_text",
  );

  return (
    <Panel className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="t-h3">Données lues</h3>
        <span className="t-data rounded-[var(--r-control)] bg-[var(--canvas)] px-2 py-0.5 text-[var(--ink-muted)]">
          {document.engine || "non lu"}
        </span>
      </div>

      {document.degraded && (
        <p
          className="mt-2.5 rounded-[var(--r-control)] px-3 py-2 text-[0.75rem] leading-relaxed"
          style={{
            background: "var(--st-correction-wash)",
            color: "var(--st-correction-ink)",
          }}
        >
          Lecture dégradée{document.error ? ` : ${document.error}` : ""}.
          Vérifiez ces valeurs sur le document avant de décider.
        </p>
      )}
      {flagCount > 0 && (
        <p
          className="mt-2.5 rounded-[var(--r-control)] px-3 py-2 text-[0.75rem]"
          style={{
            background: "var(--st-rejected-wash)",
            color: "var(--st-rejected-ink)",
          }}
        >
          {flagCount} anomalie{flagCount > 1 ? "s" : ""} porte
          {flagCount > 1 ? "nt" : ""} sur cette pièce.
        </p>
      )}

      {entries.length === 0 ? (
        <p className="mt-4 text-[0.875rem] text-[var(--ink-muted)]">
          Aucune donnée n&apos;a pu être extraite de cette pièce.
        </p>
      ) : (
        <dl className="mt-4">
          {entries.map(([key, value]) => (
            <div
              key={key}
              className="flex flex-col gap-0.5 border-b border-[var(--line)] py-2 last:border-b-0 sm:flex-row sm:gap-4"
            >
              <dt className="text-[0.8125rem] text-[var(--ink-muted)] sm:w-44 sm:shrink-0">
                {FIELD_LABELS[key] ?? key}
              </dt>
              <dd className="t-data min-w-0 flex-1 break-words text-[var(--ink)]">
                {formatValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </Panel>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "boolean") return value ? "oui" : "non";
  return String(value);
}
