"use client";

import {
  ArrowLeft,
  ArrowRight,
  FileCheck2,
  MessagesSquare,
  PencilLine,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";

import { PortalBar } from "@/components/chrome";
import { SiteFooter } from "@/components/site-footer";
import { ActionButton } from "@/components/action-button";
import { ContextForm } from "@/components/context-form";
import { DeclarationForm } from "@/components/declaration-form";
import { DocumentRail } from "@/components/document-rail";
import { FilingSteps, type FilingStep } from "@/components/filing-steps";
import { StatusTracker } from "@/components/status-tracker";
import { Notice, Panel, SectionHeading } from "@/components/ui";
import { VerdictPanel } from "@/components/verdict-panel";
import { openAssistant, setActiveSubmission } from "@/lib/active-submission";
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
  const [declaration, setDeclaration] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SubmissionResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [step, setStep] = useState(0);
  // How far the applicant has got. Steps behind this stay clickable, so fixing
  // an answer never means walking forward through the others again.
  const [furthest, setFurthest] = useState(0);

  useEffect(() => {
    listTransactions()
      .then((all) => {
        const match = all.find((t) => t.transaction_type === transactionType);
        if (!match) throw new Error(`Démarche inconnue : ${transactionType}`);
        setTransaction(match);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [transactionType]);

  /**
   * Hand the verdict to the floating assistant, and take it back on the way
   * out: an assistant that still thinks it is looking at a filing you have
   * left would answer about the wrong one.
   */
  useEffect(() => {
    setActiveSubmission(result?.submission_id ?? null);
  }, [result]);

  useEffect(() => () => setActiveSubmission(null), []);

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

  /**
   * The context step only exists for transactions that ask context questions,
   * so the step list is built from what this filing actually needs rather than
   * showing an empty stage.
   */
  const steps = useMemo<FilingStep[]>(() => {
    const list: FilingStep[] = [];
    if (contextFields.length > 0) {
      list.push({ key: "context", label_fr: "Votre situation", label_ar: "وضعيتك" });
    }
    if ((transaction?.declaration_fields.length ?? 0) > 0) {
      list.push({ key: "declaration", label_fr: "Votre déclaration", label_ar: "التصريح" });
    }
    list.push({ key: "documents", label_fr: "Vos pièces", label_ar: "وثائقك" });
    list.push({ key: "result", label_fr: "Résultat", label_ar: "النتيجة" });
    return list;
  }, [contextFields, transaction]);

  const stepKey = steps[Math.min(step, steps.length - 1)]?.key ?? "documents";
  const resultStep = steps.length - 1;

  /** Declaration entries the official form marks obligatory and that are blank. */
  const declarationGaps = useMemo(
    () =>
      (transaction?.declaration_fields ?? []).filter(
        (field) => field.required && !(declaration[field.name] ?? "").trim(),
      ),
    [transaction, declaration],
  );

  const goTo = useCallback((index: number) => {
    setStep(index);
    setFurthest((reached) => Math.max(reached, index));
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

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
          declaration,
        ),
      );
      goTo(resultStep);
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

      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
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

        <div className="mt-7">
          <FilingSteps
            steps={steps}
            current={step}
            furthest={furthest}
            onSelect={goTo}
          />
        </div>

        <div className="mt-8">
          {stepKey === "context" && (
            <ContextForm
              fields={contextFields}
              values={context}
              onChange={(name, value) =>
                setContext((current) => ({ ...current, [name]: value }))
              }
            />
          )}

          {stepKey === "declaration" && transaction && (
            <DeclarationForm
              fields={transaction.declaration_fields}
              values={declaration}
              onChange={(name, value) =>
                setDeclaration((current) => ({ ...current, [name]: value }))
              }
              modificationType={transaction.modification_type_fr}
              modificationTypeAr={transaction.modification_type_ar}
            />
          )}

          {stepKey === "documents" && (
            <>
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
                <DocumentRail documents={required} files={files} onAttach={attach} />
              ) : (
                <Panel className="p-5 text-[0.875rem] text-[var(--ink-muted)]">
                  Chargement de la liste des pièces requises.
                </Panel>
              )}
              <p className="mt-4 text-[0.8125rem] text-[var(--ink-faint)]">
                Rien n&apos;est transmis au registre à cette étape.
              </p>
            </>
          )}

          {stepKey === "result" && result && (
            <>
              <StatusTracker status={result.status} />
              <div className="mt-6">
                <VerdictPanel result={result} />
              </div>
              <div className="mt-6">
                <SectionHeading hint="Réponses fondées sur les textes officiels du RNE">
                  Comprendre le résultat
                </SectionHeading>
                <Panel className="flex flex-wrap items-center justify-between gap-4 p-5">
                  <p className="max-w-prose text-[0.875rem] leading-relaxed text-[var(--ink-muted)]">
                    L&apos;assistant reprend ce résultat et vous explique, pièce
                    par pièce, ce qu&apos;il faut corriger. Chaque réponse cite
                    le texte du RNE sur lequel elle s&apos;appuie ; la décision,
                    elle, vient des règles de vérification et non du modèle.
                  </p>
                  <ActionButton onClick={openAssistant}>
                    <MessagesSquare size={17} strokeWidth={1.9} aria-hidden />
                    Ouvrir l&apos;assistant
                  </ActionButton>
                </Panel>
              </div>
            </>
          )}

          {error && (
            <div className="mt-4">
              <Notice>{error}</Notice>
            </div>
          )}

          {/* ------------------------------------------------- step footer --- */}
          <div className="mt-6 flex flex-wrap items-center justify-between gap-x-4 gap-y-3 border-t border-[var(--line)] pt-5">
            {step > 0 ? (
              <button
                type="button"
                onClick={() => goTo(step - 1)}
                className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]"
              >
                <ArrowLeft size={15} strokeWidth={2} aria-hidden />
                {steps[step - 1].label_fr}
              </button>
            ) : (
              <span />
            )}

            <div className="flex flex-wrap items-center justify-end gap-x-3 gap-y-2">
              {stepKey === "context" && unanswered.length > 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-muted)]">
                  Renseignez{" "}
                  {unanswered.map((field) => field.label_fr.toLowerCase()).join(" et ")}
                  .
                </p>
              )}
              {stepKey === "declaration" && declarationGaps.length > 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-muted)]">
                  {declarationGaps.length} réponse
                  {declarationGaps.length > 1 ? "s" : ""} obligatoire
                  {declarationGaps.length > 1 ? "s" : ""} encore vide
                  {declarationGaps.length > 1 ? "s" : ""}.
                </p>
              )}
              {stepKey === "documents" && missingCount > 0 && attachedCount > 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-muted)]">
                  Il manque {missingCount} pièce{missingCount > 1 ? "s" : ""}.
                  Vérifiez maintenant pour savoir ce qui bloque.
                </p>
              )}
              {stepKey === "documents" && attachedCount === 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-faint)]">
                  Joignez au moins une pièce.
                </p>
              )}

              {stepKey === "result" ? (
                <ActionButton onClick={() => goTo(0)} variant="teal">
                  <PencilLine size={17} strokeWidth={1.9} aria-hidden />
                  Modifier mes réponses
                </ActionButton>
              ) : stepKey === "documents" ? (
                <ActionButton
                  onClick={check}
                  disabled={checking || attachedCount === 0 || unanswered.length > 0}
                >
                  <ShieldCheck size={17} strokeWidth={2} aria-hidden />
                  {checking ? "Vérification en cours" : "Vérifier mes pièces"}
                </ActionButton>
              ) : (
                <ActionButton
                  onClick={() => goTo(step + 1)}
                  disabled={stepKey === "context" && unanswered.length > 0}
                >
                  Continuer
                  <ArrowRight size={17} strokeWidth={2} aria-hidden />
                </ActionButton>
              )}
            </div>
          </div>
        </div>

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
      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <div className="h-5 w-36 animate-pulse rounded bg-[var(--line)]" />

        <div className="mt-5 flex items-end justify-between gap-6 border-b border-[var(--line)] pb-6">
          <div className="w-full max-w-md animate-pulse">
            <div className="h-3 w-40 rounded bg-[var(--teal-wash)]" />
            <div className="mt-4 h-8 w-4/5 rounded bg-[var(--line)]" />
            <div className="mt-2 h-4 w-2/5 rounded bg-[var(--line)]" />
          </div>
          <div className="hidden h-7 w-24 animate-pulse rounded bg-[var(--line)] sm:block" />
        </div>

        <div className="mt-7 flex items-center gap-3" aria-hidden>
          {[0, 1, 2, 3].map((pip) => (
            <div key={pip} className="flex flex-1 items-center gap-2 last:flex-none">
              <div className="size-7 shrink-0 animate-pulse rounded-full bg-[var(--line)]" />
              <div className="hidden h-3 w-24 animate-pulse rounded bg-[var(--line)] sm:block" />
              {pip < 3 && <div className="h-px flex-1 bg-[var(--line)]" />}
            </div>
          ))}
        </div>

        <div className="mt-8 animate-pulse rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-5" aria-hidden>
          <div className="h-4 w-3/5 rounded bg-[var(--line)]" />
          <div className="mt-4 h-3 w-2/5 rounded bg-[var(--line)]" />
          <div className="mt-7 h-12 rounded bg-[var(--canvas)]" />
          <div className="mt-3 h-12 rounded bg-[var(--canvas)]" />
          <div className="mt-3 h-12 rounded bg-[var(--canvas)]" />
        </div>

        <p className="sr-only">Chargement du formulaire</p>
      </main>
      <SiteFooter />
    </div>
  );
}
