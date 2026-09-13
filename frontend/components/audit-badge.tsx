"use client";

import { ShieldCheck, ShieldAlert, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { verifyAuditTrail } from "@/lib/api";
import type { AuditVerification } from "@/lib/types";

/**
 * Whether the decision record still matches itself.
 *
 * Each officer decision carries the hash of the one before it, across every
 * dossier. This recomputes the chain on demand. It cannot stop someone editing
 * the stored record -- it makes the edit visible, and names the decision where
 * the record stopped being true.
 *
 * Shown in the officer's chrome because that is who the guarantee is for: it
 * is their decisions, and their signature on them, that the chain protects.
 */
export function AuditBadge() {
  const [result, setResult] = useState<AuditVerification | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    verifyAuditTrail()
      .then((found) => live && setResult(found))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  if (failed) return null;

  if (!result) {
    return (
      <span className="inline-flex items-center gap-1.5 text-[0.75rem] text-white/50">
        <Loader2 size={12} strokeWidth={2} className="animate-spin" aria-hidden />
        Registre des décisions
      </span>
    );
  }

  const label = result.intact
    ? `Registre des décisions intact — ${result.entries} décision${result.entries === 1 ? "" : "s"}`
    : "Registre des décisions altéré";

  return (
    <span
      title={
        result.intact
          ? `Chaîne vérifiée. Empreinte courante ${result.head.slice(0, 12)}…`
          : `Rupture à la décision ${result.broken_at?.position} (${result.broken_at?.reason})`
      }
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.75rem] font-medium ${
        result.intact
          ? "bg-white/10 text-white/80"
          : "bg-[var(--st-rejected-wash)] text-[var(--st-rejected-ink)]"
      }`}
    >
      {result.intact ? (
        <ShieldCheck size={13} strokeWidth={2.1} aria-hidden />
      ) : (
        <ShieldAlert size={13} strokeWidth={2.1} aria-hidden />
      )}
      {label}
    </span>
  );
}
