import type { Metadata } from "next";

import { MyDossiers } from "@/components/my-dossiers";

export const metadata: Metadata = {
  title: "Mes dossiers — Sahilli",
  description: "Suivez l'état de vos dossiers déposés au Registre National des Entreprises.",
};

export default function DossiersPage() {
  return <MyDossiers />;
}
