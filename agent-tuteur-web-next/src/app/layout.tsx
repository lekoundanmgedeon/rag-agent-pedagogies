import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/AuthProvider";
import { ThemeScript } from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: "Agent Tuteur Sénégal",
  description:
    "Tuteur pédagogique pour le programme scolaire sénégalais — révision guidée, cours et évaluation.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <ThemeScript />
      </head>
      <body>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
