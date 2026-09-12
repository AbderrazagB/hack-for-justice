import {
  CircleAlert,
  CircleCheck,
  CircleX,
  Inbox,
  Landmark,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";

import type { CompletenessStatus, Severity, SubmissionStatus } from "@/lib/types";

/**
 * The status system. One definition per state, consumed identically by the MSME
 * tracker, the officer queue and the review screen, so a colour always means the
 * same thing wherever it appears. See docs/DESIGN.md section 1.
 */

export type StatusStyle = {
  /** French label shown to users. */
  fr: string;
  /** Arabic label, set in the Arabic face. */
  ar: string;
  /** CSS var name for text/icon colour. */
  ink: string;
  /** CSS var name for the background wash. */
  wash: string;
  icon: LucideIcon;
};

export const SUBMISSION_STATUS: Record<SubmissionStatus, StatusStyle> = {
  SUBMITTED: {
    fr: "Déposé",
    ar: "تم الإيداع",
    ink: "var(--st-submitted-ink)",
    wash: "var(--st-submitted-wash)",
    icon: Inbox,
  },
  PRE_VALIDATED: {
    fr: "Pré-validé",
    ar: "تحقق أولي",
    ink: "var(--st-prevalidated-ink)",
    wash: "var(--st-prevalidated-wash)",
    icon: ShieldCheck,
  },
  UNDER_INSTITUTIONAL_REVIEW: {
    fr: "Examen RNE",
    ar: "قيد الدرس",
    ink: "var(--st-review-ink)",
    wash: "var(--st-review-wash)",
    icon: Landmark,
  },
  APPROVED: {
    fr: "Approuvé",
    ar: "مقبول",
    ink: "var(--st-approved-ink)",
    wash: "var(--st-approved-wash)",
    icon: CircleCheck,
  },
  REJECTED: {
    fr: "Rejeté",
    ar: "مرفوض",
    ink: "var(--st-rejected-ink)",
    wash: "var(--st-rejected-wash)",
    icon: CircleX,
  },
  NEEDS_CORRECTION: {
    fr: "À corriger",
    ar: "يتطلب تصحيحاً",
    ink: "var(--st-correction-ink)",
    wash: "var(--st-correction-wash)",
    icon: CircleAlert,
  },
};

/** Completeness reuses the same three semantics as the terminal statuses. */
export const COMPLETENESS_STATUS: Record<CompletenessStatus, StatusStyle> = {
  COMPLETE: {
    fr: "Dossier complet",
    ar: "ملف كامل",
    ink: "var(--st-approved-ink)",
    wash: "var(--st-approved-wash)",
    icon: CircleCheck,
  },
  INCOMPLETE: {
    fr: "Pièces manquantes",
    ar: "وثائق ناقصة",
    ink: "var(--st-rejected-ink)",
    wash: "var(--st-rejected-wash)",
    icon: CircleX,
  },
  NEEDS_REVIEW: {
    fr: "Points à corriger",
    ar: "نقاط تتطلب تصحيحاً",
    ink: "var(--st-correction-ink)",
    wash: "var(--st-correction-wash)",
    icon: CircleAlert,
  },
};

export const SEVERITY: Record<Severity, { ink: string; wash: string; fr: string }> = {
  ERROR: {
    ink: "var(--st-rejected-ink)",
    wash: "var(--st-rejected-wash)",
    fr: "Bloquant",
  },
  WARNING: {
    ink: "var(--st-correction-ink)",
    wash: "var(--st-correction-wash)",
    fr: "À vérifier",
  },
  INFO: {
    ink: "var(--teal-ink)",
    wash: "var(--teal-wash)",
    fr: "Information",
  },
};

export function statusStyle(
  status: SubmissionStatus | CompletenessStatus | string,
): StatusStyle {
  return (
    SUBMISSION_STATUS[status as SubmissionStatus] ??
    COMPLETENESS_STATUS[status as CompletenessStatus] ??
    SUBMISSION_STATUS.SUBMITTED
  );
}

/** Human-readable French names for the required documents, keyed as the API returns them. */
export const DOCUMENT_SHORT_FR: Record<string, string> = {
  id_new_representative: "Carte d'identité nationale",
  company_statutes: "Statuts de la société",
  rne_extract: "Extrait RNE",
  tax_registration_card: "Carte d'identification fiscale",
  general_assembly_pv: "Procès-verbal",
  financial_statements_signed: "États financiers",
  general_assembly_pv_approval: "Procès-verbal de l'AGO",
  auditor_report: "Rapport du commissaire aux comptes",
  updated_shareholder_list: "Liste des associés",
};
