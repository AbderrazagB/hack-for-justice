import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginPanel } from "@/components/login-panel";

export const metadata: Metadata = {
  title: "Connexion — Sahilli",
  description: "Accédez à votre espace Sahilli pour suivre vos dossiers RNE.",
};

export default function LoginPage() {
  // The panel reads ?next= to finish the journey a session check interrupted,
  // and useSearchParams needs a boundary for the page to prerender at all.
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--surface)]" />}>
      <LoginPanel />
    </Suspense>
  );
}
