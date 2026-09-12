/** Shared shapes returned by the Sahilli API. */

export type BilingualLabel = {
  key: string;
  label_fr: string;
  label_ar: string;
};

export type ContextFieldOption = {
  value: string;
  label_fr: string;
  label_ar: string;
};

/** A question asked before upload, described by the backend so the form is data. */
export type ContextField = {
  name: string;
  label_fr: string;
  label_ar: string;
  type: "select" | "date" | "checkbox";
  required: boolean;
  options: ContextFieldOption[];
  help_fr: string | null;
};

export type TransactionInfo = {
  transaction_type: string;
  display_name_fr: string;
  display_name_ar: string;
  official_reference: string;
  required_documents: BilingualLabel[];
  conditional_documents: string[];
  checks: string[];
  context_fields: ContextField[];
};

export type CheckOutcome = "PASS" | "FAIL" | "INDETERMINATE";

export type CheckResult = {
  name: string;
  outcome: CheckOutcome;
  label_fr: string;
  label_ar: string;
  reason_fr: string;
  reason_ar: string;
  evidence: Record<string, unknown>;
};

export type CompletenessStatus = "COMPLETE" | "INCOMPLETE" | "NEEDS_REVIEW";

export type Completeness = {
  transaction_type: string;
  display_name_fr: string;
  display_name_ar: string;
  official_reference: string;
  status: CompletenessStatus;
  missing_documents: BilingualLabel[];
  present_documents: string[];
  checks: CheckResult[];
};

export type Severity = "ERROR" | "WARNING" | "INFO";

export type Flag = {
  code: string;
  severity: Severity;
  message_fr: string;
  message_ar: string;
  documents: BilingualLabel[];
  evidence: Record<string, unknown>;
};

export type ExtractedDocument = {
  filename: string;
  stored_path: string;
  content_type: string | null;
  size_bytes: number;
  document_type: string;
  fields: Record<string, unknown>;
  full_text: string;
  engine: string;
  degraded: boolean;
  error: string | null;
  page_count: number;
};

export type SubmissionStatus =
  | "SUBMITTED"
  | "PRE_VALIDATED"
  | "UNDER_INSTITUTIONAL_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "NEEDS_CORRECTION";

export type ReviewEvent = {
  action: string;
  status: string;
  note: string;
  officer: string;
  at: string;
};

export type Submission = {
  id: string;
  transaction_type: string;
  status: SubmissionStatus;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  documents: Record<string, ExtractedDocument>;
  completeness: Completeness;
  flags: Flag[];
  reviews: ReviewEvent[];
  flag_count: number;
  error_flag_count: number;
};

export type SubmissionSummary = {
  id: string;
  transaction_type: string;
  display_name_fr: string;
  display_name_ar: string;
  status: SubmissionStatus;
  created_at: string;
  updated_at: string;
  flag_count: number;
  error_flag_count: number;
  document_count: number;
  completeness_status: CompletenessStatus | null;
};

export type FlagSummary = {
  total: number;
  errors: number;
  warnings: number;
  info: number;
};

export type SubmissionResult = {
  submission_id: string;
  status: SubmissionStatus;
  required_documents: string[];
  completeness: Completeness;
  flags: Flag[];
  flag_summary: FlagSummary;
};

export type Stats = {
  total: number;
  by_status: Record<string, number>;
  reviewed: number;
  flagged: number;
  flag_rate: number;
  average_review_seconds: number | null;
  average_flags_per_submission: number;
};

export type Citation = {
  entry_id: string;
  official_reference: string;
  title: string;
  score: number;
};

export type ExplainResponse = {
  submission_id: string;
  answer: string;
  lang: "fr" | "ar";
  citations: Citation[];
  grounded: boolean;
};

export type ReviewAction = "approve" | "reject" | "request_correction";

export type UserRole = "applicant" | "officer";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  company_name: string | null;
  role: UserRole;
  created_at: string | null;
  last_login_at: string | null;
};

export type SessionResponse = {
  user: AuthUser;
  expires_at: string;
};
