"use client";

import { ShieldCheck } from "lucide-react";
import { use, useCallback, useEffect, useMemo, useState } from "react";

import { AssistantPanel } from "@/components/assistant-panel";
import { PortalBar } from "@/components/chrome";
import { SiteFooter } from "@/components/site-footer";
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

  const required = useMemo(
    () => transaction?.required_documents ?? [],
    [transaction],
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
      setResult(await createSubmission(transaction.transaction_type, documents));
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
      <div className="min-h-screen">
        <PortalBar />
        <main className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
          <Notice>{error}</Notice>
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar />

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
          <div>
            <h1 className="t-h1">
              {transaction?.display_name_fr ?? "Chargement du formulaire"}
            </h1>
            {transaction && (
              <p className="ar mt-0.5 text-[1.0625rem] text-[var(--ink-muted)]">
                {transaction.display_name_ar}
              </p>
            )}
          </div>
          {transaction && (
            <p className="t-data text-[var(--ink-muted)]">
              {transaction.official_reference}
            </p>
          )}
        </div>

        {result && (
          <div className="mt-7">
            <StatusTracker status={result.status} />
          </div>
        )}

        <div className="mt-8 grid items-start gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8">
          {/* ------------------------------------------------ upload rail --- */}
          <section>
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
                disabled={checking || attachedCount === 0}
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
              {attachedCount === 0 && (
                <p className="text-[0.8125rem] text-[var(--ink-faint)]">
                  Joignez au moins une pièce pour lancer la vérification.
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
