import type {
  AuthUser,
  ExplainResponse,
  FlagEvidence,
  UploadProgress,
  ReviewAction,
  Stats,
  SessionResponse,
  Submission,
  SubmissionResult,
  SubmissionSummary,
  TransactionInfo,
} from "@/lib/types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Forward the caller's session cookie from a Server Component.
 *
 * `credentials: "include"` only means anything in the browser. A server-side
 * fetch has no cookie jar, so the officer pages have to read the incoming
 * request's cookies and pass them on explicitly.
 */
export async function serverAuthHeaders(): Promise<HeadersInit> {
  const { cookies } = await import("next/headers");
  const jar = await cookies();
  const header = jar.toString();
  return header ? { Cookie: header } : {};
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<TResponse>(
  path: string,
  options: RequestInit = {},
): Promise<TResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      cache: "no-store",
      // The session lives in an httpOnly cookie, so every request has to carry
      // credentials for the backend to recognise the caller.
      credentials: "include",
      ...options,
    });
  } catch {
    // A network-level failure means the API isn't reachable at all, which is
    // worth saying plainly rather than surfacing "Failed to fetch".
    throw new ApiError(
      `Impossible de joindre l'API Sahilli (${API_URL}). Est-elle démarrée ?`,
      0,
    );
  }

  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      /* response had no JSON body; keep the status-based message */
    }
    throw new ApiError(detail, response.status);
  }

  return response.json() as Promise<TResponse>;
}

function json<TResponse>(
  path: string,
  method: string,
  body: unknown,
): Promise<TResponse> {
  return request<TResponse>(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function listTransactions(): Promise<TransactionInfo[]> {
  return request<TransactionInfo[]>("/transactions");
}

export function createSubmission(
  transactionType: string,
  documents: { documentType: string; file: File }[],
  /** Answers to the transaction's context_fields, keyed by field name. */
  context: Record<string, string | boolean> = {},
  /** Answers to the RNE-F-005 declaration, keyed by field name. */
  declaration: Record<string, string> = {},
  submittedAt?: string,
  /** Poll /uploads/{id}/progress with this to follow the read. */
  uploadId?: string,
): Promise<SubmissionResult> {
  const form = new FormData();
  if (uploadId) form.append("upload_id", uploadId);
  for (const { documentType, file } of documents) {
    form.append("files", file);
    form.append("document_types", documentType);
  }
  for (const [name, value] of Object.entries(context)) {
    if (value === "" || value === false) continue;
    form.append(name, String(value));
  }
  const declared = Object.fromEntries(
    Object.entries(declaration).filter(([, value]) => value.trim() !== ""),
  );
  if (Object.keys(declared).length > 0) {
    // A multipart form cannot carry a nested object, so the declaration travels
    // as one JSON field.
    form.append("declaration", JSON.stringify(declared));
  }
  if (submittedAt) form.append("submitted_at", submittedAt);

  return request<SubmissionResult>(
    `/transactions/${transactionType}/submissions`,
    { method: "POST", body: form },
  );
}

export function getSubmission(
  id: string,
  headers: HeadersInit = {},
): Promise<Submission> {
  return request<Submission>(`/submissions/${id}`, { headers });
}

export function listSubmissions(
  filters: { status?: string; transactionType?: string } = {},
  headers: HeadersInit = {},
): Promise<{ count: number; submissions: SubmissionSummary[] }> {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.transactionType)
    params.set("transaction_type", filters.transactionType);
  const query = params.toString();
  return request(`/submissions${query ? `?${query}` : ""}`, { headers });
}

export function getStats(headers: HeadersInit = {}): Promise<Stats> {
  return request<Stats>("/submissions/stats", { headers });
}

export function reviewSubmission(
  id: string,
  action: ReviewAction,
  note = "",
  officer = "officer",
): Promise<{ submission_id: string; status: string }> {
  return json(`/submissions/${id}/review`, "POST", { action, note, officer });
}

/**
 * `submissionId` is null when the assistant is asked something before any
 * filing exists -- the backend then answers from the RNE corpus alone and
 * says nothing about documents it has not seen.
 */
export function explainSubmission(
  submissionId: string | null,
  question = "",
  lang: "fr" | "ar" = "fr",
): Promise<ExplainResponse> {
  return json("/assistant/explain", "POST", {
    submission_id: submissionId,
    question,
    lang,
  });
}

/* ----------------------------------------------------------------- auth --- */

export function signup(input: {
  email: string;
  password: string;
  full_name: string;
  company_name?: string;
}): Promise<SessionResponse> {
  return json<SessionResponse>("/auth/signup", "POST", input);
}

export function login(
  email: string,
  password: string,
): Promise<SessionResponse> {
  return json<SessionResponse>("/auth/login", "POST", { email, password });
}

export function logout(): Promise<{ detail: string }> {
  return json("/auth/logout", "POST", {});
}

/** Resolve the signed-in user, or null when there is no valid session. */
export async function currentUser(): Promise<AuthUser | null> {
  try {
    return await request<AuthUser>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

/** How far the server has got reading an upload it is still working on. */
export function uploadProgress(uploadId: string): Promise<UploadProgress> {
  return request<UploadProgress>(`/uploads/${encodeURIComponent(uploadId)}/progress`);
}

/** Where a flag's disputed values sit on the pages they came from. */
export function flagEvidence(
  submissionId: string,
  code: string,
): Promise<FlagEvidence> {
  return request<FlagEvidence>(
    `/submissions/${submissionId}/evidence/${encodeURIComponent(code)}`,
  );
}

/** URL of the submission's RNE-F-005 preparation sheet. */
export function preparationSheetUrl(submissionId: string): string {
  return `${API_URL}/submissions/${submissionId}/declaration.pdf`;
}
