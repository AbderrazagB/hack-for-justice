"use client";

import { ArrowLeft, ArrowRight, FolderOpen, Loader2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { PortalBar } from "@/components/chrome";
import { DossierCard } from "@/components/dossier-card";
import { Notice } from "@/components/ui";
import { mySubmissions } from "@/lib/api";
import type { SubmissionSummary } from "@/lib/types";

/**
 * Your dossiers, and where each one has got to.
 *
 * A filing used to exist only in the tab that created it: close it and the id
 * was gone, along with any way of telling whether the registry had looked. A
 * dossier carries your identity documents and has a legal deadline attached to
 * it -- it should be something you own, not something you did once.
 */
export function MyDossiers() {
  const [submissions, setSubmissions] = useState<SubmissionSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    mySubmissions()
      .then((body) => live && setSubmissions(body.submissions))
      .catch(
        (e) =>
          live &&
          setError(e instanceof Error ? e.message : "Vos dossiers n'ont pas pu être chargés."),
      );
    return () => {
      live = false;
    };
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-[var(--canvas)]">
      <PortalBar />

      <main className="mx-auto w-full max-w-4xl flex-1 px-4 py-6 sm:px-6">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-[var(--line)] pb-4">
          <Link
            href="/msme"
            className="inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
          >
            <ArrowLeft size={15} strokeWidth={2} aria-hidden />
            Démarches
          </Link>
          <h1 className="t-h2 text-[var(--navy)]">Mes dossiers</h1>
          <p className="ar text-[0.9375rem] text-[var(--ink-muted)]">ملفاتي</p>
        </div>

        {error && (
          <div className="mt-6">
            <Notice>{error}</Notice>
          </div>
        )}

        {!submissions && !error && (
          <p className="mt-6 flex items-center gap-2 text-[0.875rem] text-[var(--ink-muted)]">
            <Loader2 size={15} strokeWidth={2} className="animate-spin" aria-hidden />
            Chargement
          </p>
        )}

        {submissions?.length === 0 && (
          <div className="mt-6 rounded-[var(--r-panel)] border border-[var(--line)] bg-[var(--surface)] p-8 text-center">
            <FolderOpen
              size={22}
              strokeWidth={1.6}
              aria-hidden
              className="mx-auto text-[var(--ink-faint)]"
            />
            <p className="mt-3 text-[0.9375rem] text-[var(--ink)]">
              Vous n&apos;avez pas encore de dossier.
            </p>
            <p className="mt-1 text-[0.8125rem] text-[var(--ink-muted)]">
              Lancez une démarche pour vérifier vos pièces avant le dépôt.
            </p>
            <Link
              href="/msme"
              className="mt-4 inline-flex items-center gap-1.5 text-[0.8125rem] font-medium text-[var(--teal-ink)] hover:underline"
            >
              Voir les démarches
              <ArrowRight size={14} strokeWidth={2} aria-hidden />
            </Link>
          </div>
        )}

        {submissions && submissions.length > 0 && (
          <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {submissions.map((submission) => (
              <li key={submission.id}>
                <DossierCard
                  submission={submission}
                  href={`/msme/dossiers/${submission.id}`}
                />
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  );
}
