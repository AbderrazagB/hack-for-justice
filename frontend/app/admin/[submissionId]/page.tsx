import { SubmissionReview } from "@/components/submission-review";
import { AdminBar } from "@/components/chrome";
import { EmptyState, Notice } from "@/components/ui";
import { getSubmission } from "@/lib/api";
import type { Submission } from "@/lib/types";

/**
 * Fetched on the server so the first paint already carries the dossier; the
 * interactive parts (document switcher, review actions) live in a client island.
 */
export default async function SubmissionDetail({
  params,
}: {
  params: Promise<{ submissionId: string }>;
}) {
  const { submissionId } = await params;

  let submission: Submission | null = null;
  let error = "";

  try {
    submission = await getSubmission(submissionId);
  } catch (requestError) {
    error =
      requestError instanceof Error
        ? requestError.message
        : "Chargement impossible.";
  }

  if (!submission) {
    return (
      <div className="min-h-screen">
        <AdminBar />
        <main className="mx-auto max-w-3xl px-5 py-12">
          {error ? (
            <Notice>{error}</Notice>
          ) : (
            <EmptyState title="Dossier introuvable">
              Aucun dossier ne porte cette référence. Revenez à la file pour le
              retrouver.
            </EmptyState>
          )}
        </main>
      </div>
    );
  }

  return <SubmissionReview submission={submission} />;
}
