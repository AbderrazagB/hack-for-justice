import type { Metadata } from "next";

import { SignupPanel } from "@/components/signup-panel";

export const metadata: Metadata = {
  title: "Créer un compte — Sahilli",
  description: "Créez un compte Sahilli pour suivre vos dossiers RNE.",
};

export default function SignupPage() {
  return <SignupPanel />;
}
