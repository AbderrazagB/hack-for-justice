import type { Metadata } from "next";

import { LoginPanel } from "@/components/login-panel";

export const metadata: Metadata = {
  title: "Connexion — Sahilli",
  description: "Accédez à votre espace Sahilli pour suivre vos dossiers RNE.",
};

export default function LoginPage() {
  return <LoginPanel />;
}
