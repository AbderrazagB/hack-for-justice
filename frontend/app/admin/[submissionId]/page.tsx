import { SubmissionReview } from "@/components/submission-review";
import { Empty, ErrorNote, Header } from "@/components/ui";
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
        <Header />
        <main className="mx-auto max-w-3xl px-5 py-12">
          {error ? <ErrorNote>{error}</ErrorNote> : <Empty>Introuvable.</Empty>}
        </main>
      </div>
    );
  }

  return <SubmissionReview submission={submission} />;
}
