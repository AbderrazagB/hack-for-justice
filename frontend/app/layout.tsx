import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Sans_Arabic, Space_Grotesk } from "next/font/google";

import { FloatingAssistant } from "@/components/floating-assistant";

import "./globals.css";

/**
 * Space Grotesk carries headings and every figure; IBM Plex Sans carries body
 * and form copy; IBM Plex Sans Arabic carries all Arabic text. Plex is chosen
 * specifically because its Arabic member shares the superfamily, so the two
 * halves of a bilingual label match in weight and proportion.
 */
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
});

const plexSans = IBM_Plex_Sans({
  variable: "--font-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  display: "swap",
});

const plexArabic = IBM_Plex_Sans_Arabic({
  variable: "--font-plex-arabic",
  subsets: ["arabic"],
  weight: ["400", "500", "600"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Sahilli — سهّلي",
  description:
    "Pré-validation des dossiers du Registre National des Entreprises pour les PME tunisiennes.",
  icons: {
    icon: "/brand/sahilli-mark.png",
    apple: "/brand/sahilli-mark.png",
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="fr"
      className={`${spaceGrotesk.variable} ${plexSans.variable} ${plexArabic.variable} h-full`}
    >
      <body className="flex min-h-full flex-col">
        {children}
        <FloatingAssistant />
      </body>
    </html>
  );
}
