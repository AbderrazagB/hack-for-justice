"use client";

import { ArrowLeft, FileCheck2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";

import { AssistantPanel } from "@/components/assistant-panel";
import { PortalBar } from "@/components/chrome";
import { SiteFooter } from "@/components/site-footer";
import { ContextForm } from "@/components/context-form";
import { DocumentRail } from "@/components/document-rail";
import { StatusTracker } from "@/components/status-tracker";
import { Button, Notice, Panel, SectionHeading } from "@/components/ui";
import { VerdictPanel } from "@/components/verdict-panel";
import { createSubmission, listTransactions } from "@/lib/api";
import type { SubmissionResult, TransactionInfo } from "@/lib/types";

export default function FilingFlow({
  params,
}: {
  params: Promise<{ transactionType: string }>;
}) {
  const { transactionType } = use(params);

  const [transaction, setTransaction] = useState<TransactionInfo | null>(null);
  const [files, setFiles] = useState<Record<string, File>>({});
  const [context, setContext] = useState<Record<string, string | boolean>>({});
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [checking, setChecking] = useState(false);
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

  const contextFields = useMemo(
    () => transaction?.context_fields ?? [],
    [transaction],
  );

  /**
   * Documents actually owed for this filing. The auditor report is only
   * required for some legal forms, so the checklist has to follow the answers
   * given above it rather than the transaction's full static list.
   */
  const required = useMemo(() => {
    const all = transaction?.required_documents ?? [];
    const conditional = transaction?.conditional_documents ?? [];
    if (conditional.length === 0) return all;

    const auditorOwed =
      context.company_type === "SA" ||
      context.company_type === "SCA" ||
      context.auditor_required === true;

    return all.filter(
      (document) =>
        !conditional.includes(document.key) ||
        (document.key === "auditor_report" && auditorOwed),
    );
  }, [transaction, context]);

  /** Context questions that still need an answer before a check is meaningful. */
  const unanswered = useMemo(
    () =>
      contextFields.filter(
        (field) => field.required && !context[field.name],
      ),
    [contextFields, context],
  );
  const attachedCount = required.filter((d) => files[d.key]).length;
  const missingCount = required.length - attachedCount;

  const attach = useCallback((key: string, file: File | null) => {
    setFiles((current) => {
      const next = { ...current };
      if (file) next[key] = file;
      else delete next[key];
      return next;
    });
  }, []);

  async function check() {
    if (!transaction) return;
    setChecking(true);
    setError("");
    try {
      const documents = Object.entries(files).map(([documentType, file]) => ({
        documentType,
        file,
      }));
      setResult(
        await createSubmission(
          transaction.transaction_type,
          documents,
          context,
        ),
      );
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "La vérification n'a pas abouti. Réessayez dans un instant.",
      );
    } finally {
      setChecking(false);
    }
  }

  if (error && !transaction) {
    return (
      <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
        <PortalBar />
        <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-12 sm:px-6">
          <Link
            href="/msme"
            className="mb-6 inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
          >
            <ArrowLeft size={15} strokeWidth={2} aria-hidden />
            Retour aux démarches
          </Link>
          <Notice>{error}</Notice>
        </main>
        <SiteFooter />
      </div>
    );
  }

  if (!transaction) {
    return <FilingSkeleton />;
  }

  return (
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar />

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <Link
          href="/msme"
          className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
        >
          <ArrowLeft size={15} strokeWidth={2} aria-hidden />
          Toutes les démarches
        </Link>

        <div className="mt-5 flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-[var(--line)] pb-6">
          <div>
            <p className="mb-2 inline-flex items-center gap-2 text-[0.6875rem] font-semibold tracking-[0.14em] text-[var(--teal-ink)] uppercase">
              <FileCheck2 size={14} strokeWidth={2} aria-hidden />
              Pré-validation du dossier
            </p>
            <h1 className="t-h1">{transaction.display_name_fr}</h1>
            <p className="ar mt-0.5 text-[1.0625rem] text-[var(--ink-muted)]">
              {transaction.display_name_ar}
            </p>
          </div>
          <p className="t-data rounded-[var(--r-control)] border border-[var(--line)] bg-[var(--surface)] px-2.5 py-1 text-[var(--ink-muted)]">
            {transaction.official_reference}
          </p>
        </div>

        {result && (
          <div className="mt-7">
            <StatusTracker status={result.status} />
          </div>
        )}

        <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8">
          {/* ------------------------------------------------ upload rail --- */}
          <section>
            {contextFields.length > 0 && (
              <div className="mb-8">
                <ContextForm
                  fields={contextFields}
                  values={context}
                  onChange={(name, value) =>
                    setContext((current) => ({ ...current, [name]: value }))
                  }
                />
              </div>
            )}

            <SectionHeading
              hint={
                required.length
                  ? `${attachedCount} sur ${required.length}`
                  : undefined
              }
            >
              Vos pièces
            </SectionHeading>

            {required.length ? (
              <DocumentRail
                documents={required}
                files={files}
                onAttach={attach}
              />
            ) : (
              <Panel className="p-5 text-[0.875rem] text-[var(--ink-muted)]">
                Chargement de la liste des pièces requises.
              </Panel>
            )}

            <div className="mt-6 flex flex-wrap items-center gap-3">
              <Button
                onClick={check}
                disabled={checking || attachedCount === 0 || unanswered.length > 0}
                icon={ShieldCheck}
              >
                {checking ? "Vérification en cours" : "Vérifier mes pièces"}
              </Button>
              {missingCount > 0 && attachedCount > 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-muted)]">
                  Il manque {missingCount} pièce{missingCount > 1 ? "s" : ""}.
                  Vous pouvez vérifier maintenant pour savoir ce qui bloque.
                </p>
              )}
              {attachedCount === 0 && unanswered.length === 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-faint)]">
                  Joignez au moins une pièce pour lancer la vérification.
                </p>
              )}
              {unanswered.length > 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-muted)]">
                  Renseignez d&apos;abord{" "}
                  {unanswered.map((field) => field.label_fr.toLowerCase()).join(" et ")}
                  .
                </p>
              )}
            </div>

            {error && (
              <div className="mt-4">
                <Notice>{error}</Notice>
              </div>
            )}
          </section>

          {/* --------------------------------------------- verdict panel --- */}
          <section className="lg:sticky lg:top-6">
            <SectionHeading>Résultat</SectionHeading>
            {result ? (
              <VerdictPanel result={result} />
            ) : (
              <Panel className="p-6">
                <p className="text-[0.875rem] leading-relaxed text-[var(--ink-muted)]">
                  Le résultat s&apos;affichera ici : pièces manquantes,
                  informations qui ne concordent pas entre vos documents, et
                  respect du délai légal de 30 jours.
                </p>
                <p className="mt-3 text-[0.8125rem] text-[var(--ink-faint)]">
                  Rien n&apos;est transmis au registre à cette étape.
                </p>
              </Panel>
            )}
          </section>
        </div>

        {result && (
          <section className="mt-12">
            <SectionHeading hint="Réponses fondées sur les textes officiels du RNE">
              Comprendre le résultat
            </SectionHeading>
            <AssistantPanel submissionId={result.submission_id} />
          </section>
        )}
      </main>

      <SiteFooter />
    </div>
  );
}

function FilingSkeleton() {
  return (
    <div
      className="flex min-h-screen flex-col bg-[var(--canvas)]"
      aria-busy="true"
    >
      <PortalBar />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <div className="h-5 w-36 animate-pulse rounded bg-[var(--line)]" />

        <div className="mt-5 flex items-end justify-between gap-6 border-b border-[var(--line)] pb-6">
          <div className="w-full max-w-md animate-pulse">
            <div className="h-3 w-40 rounded bg-[var(--teal-wash)]" />
            <div className="mt-4 h-8 w-4/5 rounded bg-[var(--line)]" />
            <div className="mt-2 h-4 w-2/5 rounded bg-[var(--line)]" />
          </div>
          <div className="hidden h-7 w-24 animate-pulse rounded bg-[var(--line)] sm:block" />
        </div>

        <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8">
          {[0, 1].map((column) => (
            <section key={column} className="animate-pulse" aria-hidden>
              <div className="mb-3 h-6 w-28 rounded bg-[var(--line)]" />
              <div className="rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-5">
                <div className="h-4 w-3/4 rounded bg-[var(--line)]" />
                <div className="mt-4 h-4 w-1/2 rounded bg-[var(--line)]" />
                <div className="mt-7 h-12 rounded bg-[var(--canvas)]" />
                <div className="mt-3 h-12 rounded bg-[var(--canvas)]" />
              </div>
            </section>
          ))}
        </div>
        <p className="sr-only">Chargement du formulaire</p>
      </main>
      <SiteFooter />
    </div>
  );
}
