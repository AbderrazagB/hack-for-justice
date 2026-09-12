"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AssistantPanel } from "@/components/assistant-panel";
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
import { createSubmission, listTransactions } from "@/lib/api";
import type { SubmissionResult, TransactionInfo } from "@/lib/types";

export default function SubmissionFlow({
  params,
}: {
  params: Promise<{ transactionType: string }>;
}) {
  const { transactionType } = use(params);

  const [transaction, setTransaction] = useState<TransactionInfo | null>(null);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listTransactions()
      .then((all) => {
        const match = all.find((t) => t.transaction_type === transactionType);
        if (!match) throw new Error(`Démarche inconnue : ${transactionType}`);
        setTransaction(match);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [transactionType]);

  const required = transaction?.required_documents ?? [];
  const missing = useMemo(
    () => required.filter((doc) => !files[doc.key]),
    [required, files],
  );

  const attach = useCallback((key: string, file: File | null) => {
    setFiles((current) => {
      const next = { ...current };
      if (file) next[key] = file;
      else delete next[key];
      return next;
    });
  }, []);

  async function submit() {
    if (!transaction) return;
    setSubmitting(true);
    setError("");
    try {
      const documents = Object.entries(files).map(([documentType, file]) => ({
        documentType,
        file,
      }));
      setResult(await createSubmission(transaction.transaction_type, documents));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Le dépôt a échoué.");
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !transaction) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="mx-auto max-w-3xl px-5 py-12">
          <ErrorNote>{error}</ErrorNote>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-6xl px-5 py-10">
        <p className="text-xs font-semibold uppercase tracking-widest text-[var(--brand)]">
          Réf. {transaction?.official_reference ?? "…"}
        </p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">
          {transaction?.display_name_fr ?? "Chargement…"}
        </h1>
        {transaction && (
          <p className="ar mt-1 text-lg opacity-70">
            {transaction.display_name_ar}
          </p>
        )}

        {result && (
          <div className="mt-8">
            <StatusTracker status={result.status} />
          </div>
        )}

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.1fr_1fr]">
          {/* ---------------------------------------------- upload checklist */}
          <section>
            <SectionTitle
              hint={
                required.length
                  ? `${required.length - missing.length}/${required.length} jointes`
                  : undefined
              }
            >
              Pièces requises
            </SectionTitle>

            <Card className="divide-y divide-[var(--border)]">
              {required.map((doc) => (
                <DocumentRow
                  key={doc.key}
                  labelFr={doc.label_fr}
                  labelAr={doc.label_ar}
                  file={files[doc.key]}
                  onChange={(file) => attach(doc.key, file)}
                />
              ))}
              {!required.length && (
                <div className="p-6 text-sm opacity-60">Chargement…</div>
              )}
            </Card>

            {missing.length > 0 && (
              <p className="mt-3 text-sm text-[var(--accent)]">
                Il manque encore {missing.length} pièce
                {missing.length > 1 ? "s" : ""} :{" "}
                {missing.map((doc) => doc.label_fr).join(", ")}.
              </p>
            )}

            <div className="mt-5 flex flex-wrap items-center gap-3">
              <Button
                onClick={submit}
                disabled={submitting || Object.keys(files).length === 0}
              >
                {submitting ? "Vérification…" : "Vérifier mon dossier"}
              </Button>
              <span className="text-xs opacity-60">
                Vous pouvez vérifier un dossier incomplet : Sahilli vous dira ce
                qui manque.
              </span>
            </div>

            {error && (
              <div className="mt-4">
                <ErrorNote>{error}</ErrorNote>
              </div>
            )}
          </section>

          {/* ------------------------------------------------------- results */}
          <section>
            <SectionTitle>Résultat de la vérification</SectionTitle>
            {result ? (
              <ResultPanel result={result} />
            ) : (
              <Empty>
                Joignez vos pièces puis lancez la vérification pour voir le
                résultat ici.
              </Empty>
            )}
          </section>
        </div>

        {result && (
          <div className="mt-10">
            <SectionTitle hint="Réponses fondées sur les textes officiels du RNE">
              Poser une question
            </SectionTitle>
            <AssistantPanel submissionId={result.submission_id} />
          </div>
        )}
      </main>
    </div>
  );
}

function DocumentRow({
  labelFr,
  labelAr,
  file,
  onChange,
}: {
  labelFr: string;
  labelAr: string;
  file?: File;
  onChange: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 p-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            aria-hidden
            className={`inline-block size-2 shrink-0 rounded-full ${
              file ? "bg-[var(--success)]" : "bg-[var(--border)]"
            }`}
          />
          <p className="truncate text-sm font-medium">{labelFr}</p>
        </div>
        <p className="ar mt-0.5 truncate pl-4 text-xs opacity-60">{labelAr}</p>
        {file && (
          <p className="mt-1 truncate pl-4 text-xs text-[var(--success)]">
            {file.name}
          </p>
        )}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        <input
          ref={inputRef}
          type="file"
          accept="image/*,application/pdf"
          className="hidden"
          onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        />
        <Button variant="secondary" onClick={() => inputRef.current?.click()}>
          {file ? "Remplacer" : "Joindre"}
        </Button>
        {file && (
          <button
            type="button"
            onClick={() => {
              onChange(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            className="text-xs underline opacity-60 hover:opacity-100"
          >
            Retirer
          </button>
        )}
      </div>
    </div>
  );
}

function ResultPanel({ result }: { result: SubmissionResult }) {
  const { completeness, flags } = result;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <StatusBadge status={completeness.status} />
          <span className="font-mono text-xs opacity-50">
            #{result.submission_id}
          </span>
        </div>

        <dl className="mt-4 grid grid-cols-3 gap-3 text-center">
          <Stat label="Anomalies" value={result.flag_summary.total} />
          <Stat
            label="Bloquantes"
            value={result.flag_summary.errors}
            tone="danger"
          />
          <Stat
            label="À vérifier"
            value={result.flag_summary.warnings}
            tone="accent"
          />
        </dl>
      </Card>

      {completeness.missing_documents.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Pièces manquantes</h3>
          <ul className="mt-3 space-y-2">
            {completeness.missing_documents.map((doc) => (
              <li key={doc.key} className="text-sm">
                <span className="text-[var(--danger)]">•</span> {doc.label_fr}
                <span className="ar block pl-3 text-xs opacity-60">
                  {doc.label_ar}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {flags.length > 0 && (
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Points à corriger</h3>
          <ul className="mt-3 space-y-3">
            {flags.map((flag, index) => (
              <li key={`${flag.code}-${index}`} className="flex gap-2">
                <SeverityDot severity={flag.severity} />
                <div className="min-w-0">
                  <p className="text-sm">{flag.message_fr}</p>
                  <p className="ar mt-0.5 text-xs opacity-60">
                    {flag.message_ar}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {flags.length === 0 && completeness.status === "COMPLETE" && (
        <Card className="bg-[var(--success-soft)] p-5">
          <p className="text-sm font-medium text-[var(--success)]">
            Aucune anomalie détectée. Votre dossier est prêt à être déposé sur le
            portail du RNE.
          </p>
        </Card>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone?: "danger" | "accent";
}) {
  const color =
    tone === "danger"
      ? "text-[var(--danger)]"
      : tone === "accent"
        ? "text-[var(--accent)]"
        : "";
  return (
    <div>
      <dd className={`text-2xl font-bold ${color}`}>{value}</dd>
      <dt className="mt-0.5 text-xs opacity-60">{label}</dt>
    </div>
  );
}
