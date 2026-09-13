import type { Metadata } from "next";

import { DossierDetail } from "@/components/dossier-detail";

export const metadata: Metadata = {
  title: "Mon dossier — Sahilli",
  description: "Suivez et corrigez votre dossier avant le dépôt au RNE.",
};

export default async function DossierPage({
  params,
}: {
  params: Promise<{ submissionId: string }>;
}) {
  const { submissionId } = await params;
  return <DossierDetail submissionId={submissionId} />;
}
