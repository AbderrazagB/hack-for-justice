"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";

import { StatusTracker } from "@/components/status-tracker";
import {
  Button,
  Card,
  Empty,
  ErrorNote,
  Header,
  SectionTitle,
  SeverityDot,
  StatusBadge,
} from "@/components/ui";
import { API_URL, getSubmission, reviewSubmission } from "@/lib/api";
import type { ExtractedDocument, ReviewAction, Submission } from "@/lib/types";

const FIELD_LABELS: Record<string, string> = {
  id_number: "N° CIN",
  person_name: "Nom",
  company_name: "Société",
  company_id: "Identifiant",
  issue_date: "Date de délivrance",
  decision_date: "Date de décision",
  signature_date: "Date de signature",
  has_signature: "Signé",
  other_id_numbers: "Autres numéros",
  notes: "Remarques",
};

export default function SubmissionDetail({
  params,
}: {
  params: Promise<{ submissionId: string }>;
}) {
  const { submissionId } = use(params);

  const [submission, setSubmission] = useState<Submission | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getSubmission(submissionId);
      setSubmission(data);
      setSelected((current) => current || Object.keys(data.documents)[0] || "");
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chargement impossible.");
    }
  }, [submissionId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function decide(action: ReviewAction) {
    setBusy(true);
    try {
      await reviewSubmission(submissionId, action, note);
      setNote("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "La décision a échoué.");
    } finally {
      setBusy(false);
    }
  }

  if (error && !submission) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-3xl px-5 py-12">
          <ErrorNote>{error}</ErrorNote>
        </main>
      </div>
    );
  }

  if (!submission) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-3xl px-5 py-12">
          <Empty>Chargement…</Empty>
        </main>
      </div>
    );
  }

  const document = submission.documents[selected];
  // Which documents this flag implicates, so selecting a flag jumps to it.
  const flagsForSelected = submission.flags.filter((flag) =>
    flag.documents.some((doc) => doc.key === selected),
  );

  return (
    <div className="min-h-screen">
      <Header
        trailing={
          <Link
            href="/admin"
            className="text-sm font-semibold text-[var(--brand)]"
          >
            ← Retour à la file
          </Link>
        }
      />

      <main className="mx-auto max-w-6xl px-5 py-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs opacity-50">#{submission.id}</p>
            <h1 className="mt-1 text-2xl font-bold tracking-tight">
              {submission.completeness.display_name_fr}
            </h1>
            <p className="ar text-sm opacity-70">
              {submission.completeness.display_name_ar}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <StatusBadge status={submission.completeness.status} />
            <StatusBadge status={submission.status} />
          </div>
        </div>

        <div className="mt-6">
          <StatusTracker status={submission.status} />
        </div>

        {/* ------------------------------------------------------------ flags */}
        <div className="mt-8">
          <SectionTitle hint={`${submission.flags.length} au total`}>
            Anomalies détectées
          </SectionTitle>
          {submission.flags.length === 0 ? (
            <Card className="bg-[var(--success-soft)] p-4">
              <p className="text-sm font-medium text-[var(--success)]">
                Aucune anomalie. Toutes les vérifications sont passées.
              </p>
            </Card>
          ) : (
            <Card className="divide-y divide-[var(--border)]">
              {submission.flags.map((flag, index) => (
                <button
                  key={`${flag.code}-${index}`}
                  type="button"
                  onClick={() =>
                    flag.documents[0] && setSelected(flag.documents[0].key)
                  }
                  className="flex w-full gap-2.5 p-4 text-left transition hover:bg-[var(--surface-muted)]"
                >
                  <SeverityDot severity={flag.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm">{flag.message_fr}</p>
                    <p className="ar mt-0.5 text-xs opacity-60">
                      {flag.message_ar}
                    </p>
                    {flag.documents.length > 0 && (
                      <p className="mt-1.5 text-xs text-[var(--brand)]">
                        {flag.documents.map((doc) => doc.label_fr).join(" ↔ ")}
                      </p>
                    )}
                  </div>
                </button>
              ))}
            </Card>
          )}
        </div>

        {/* ------------------------------ extracted fields beside the document */}
        <div className="mt-10">
          <SectionTitle hint="Données extraites face au document original">
            Vérification pièce par pièce
          </SectionTitle>

          <div className="flex flex-wrap gap-1.5">
            {Object.keys(submission.documents).map((key) => (
              <button
                key={key}
                type="button"
                onClick={() => setSelected(key)}
                className={`rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                  selected === key
                    ? "bg-[var(--brand)] text-white"
                    : "border border-[var(--border)] hover:bg-[var(--surface-muted)]"
                }`}
              >
                {key}
                {submission.flags.some((f) =>
                  f.documents.some((d) => d.key === key),
                ) && <span className="ml-1 text-[var(--accent)]">•</span>}
              </button>
            ))}
          </div>

          {document ? (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <DocumentPreview document={document} />
              <FieldTable document={document} flagged={flagsForSelected.length > 0} />
            </div>
          ) : (
            <div className="mt-4">
              <Empty>Aucune pièce jointe à ce dossier.</Empty>
            </div>
          )}
        </div>

        {/* ----------------------------------------------------------- decide */}
        <div className="mt-10 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
          <Card className="p-5">
            <h2 className="text-sm font-semibold">Décision</h2>
            <label className="sr-only" htmlFor="review-note">
              Note
            </label>
            <textarea
              id="review-note"
              value={note}
              onChange={(event) => setNote(event.target.value)}
              rows={3}
              placeholder="Note à l'attention du déposant (facultatif)…"
              className="mt-3 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm outline-none focus:border-[var(--brand)]"
            />
            <div className="mt-3 flex flex-wrap gap-2">
              <Button onClick={() => void decide("approve")} disabled={busy}>
                Approuver
              </Button>
              <Button
                variant="secondary"
                onClick={() => void decide("request_correction")}
                disabled={busy}
              >
                Demander une correction
              </Button>
              <Button
                variant="danger"
                onClick={() => void decide("reject")}
                disabled={busy}
              >
                Rejeter
              </Button>
            </div>
            {error && (
              <div className="mt-3">
                <ErrorNote>{error}</ErrorNote>
              </div>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="text-sm font-semibold">Historique</h2>
            {submission.reviews.length === 0 ? (
              <p className="mt-3 text-sm opacity-60">Aucune décision enregistrée.</p>
            ) : (
              <ol className="mt-3 space-y-3">
                {submission.reviews.map((review, index) => (
                  <li key={index} className="text-sm">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={review.status} />
                      <span className="text-xs opacity-55">
                        {new Date(review.at).toLocaleString("fr-FR")}
                      </span>
                    </div>
                    <p className="mt-1 text-xs opacity-70">
                      par {review.officer}
                      {review.note ? ` — « ${review.note} »` : ""}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </Card>
        </div>
      </main>
    </div>
  );
}

function DocumentPreview({ document }: { document: ExtractedDocument }) {
  const [broken, setBroken] = useState(false);
  const source = `${API_URL}/documents/${document.document_type}/${encodeURIComponent(document.stored_path)}`;

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] px-4 py-2.5">
        <p className="truncate text-xs font-medium">{document.filename}</p>
        <span className="shrink-0 text-xs opacity-50">
          {(document.size_bytes / 1024).toFixed(0)} ko
        </span>
      </div>
      <div className="flex min-h-64 items-center justify-center bg-[var(--surface-muted)] p-3">
        {broken ? (
          <p className="px-6 py-10 text-center text-xs opacity-55">
            Aperçu indisponible.
            <br />
            Fichier conservé sous{" "}
            <code className="font-mono">
              data/raw/{document.document_type}/{document.stored_path}
            </code>
          </p>
        ) : (
          /* eslint-disable-next-line @next/next/no-img-element */
          <img
            src={source}
            alt={`Document déposé : ${document.filename}`}
            className="max-h-[28rem] w-auto max-w-full rounded"
            onError={() => setBroken(true)}
          />
        )}
      </div>
    </Card>
  );
}

function FieldTable({
  document,
  flagged,
}: {
  document: ExtractedDocument;
  flagged: boolean;
}) {
  const entries = Object.entries(document.fields).filter(
    ([key]) => key !== "full_text",
  );

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Données extraites</h3>
        <span className="rounded-full bg-[var(--surface-muted)] px-2 py-0.5 font-mono text-[11px] opacity-70">
          {document.engine || "—"}
        </span>
      </div>

      {document.degraded && (
        <p className="mt-2 text-xs text-[var(--accent)]">
          Extraction dégradée{document.error ? ` : ${document.error}` : ""}. Les
          valeurs doivent être vérifiées manuellement.
        </p>
      )}
      {flagged && (
        <p className="mt-2 text-xs text-[var(--danger)]">
          Cette pièce est concernée par une anomalie.
        </p>
      )}

      {entries.length === 0 ? (
        <p className="mt-4 text-sm opacity-60">Aucun champ extrait.</p>
      ) : (
        <dl className="mt-4 divide-y divide-[var(--border)]">
          {entries.map(([key, value]) => (
            <div key={key} className="flex gap-3 py-2">
              <dt className="w-40 shrink-0 text-xs opacity-60">
                {FIELD_LABELS[key] ?? key}
              </dt>
              <dd className="min-w-0 flex-1 break-words font-mono text-xs">
                {formatValue(value)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "boolean") return value ? "oui" : "non";
  return String(value);
}
