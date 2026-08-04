"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, ClipboardCheck, LayoutDashboard, LogOut, MessageSquare, TrendingUp } from "lucide-react";
import { twMerge } from "tailwind-merge";
import { useAuth } from "@/components/AuthProvider";
import { ThemeToggle } from "@/components/ThemeToggle";

const LIENS_ELEVE = [
  { href: "/", libelle: "Tuteur", Icone: MessageSquare },
  { href: "/quiz", libelle: "Quiz", Icone: ClipboardCheck },
  { href: "/progression", libelle: "Progression", Icone: TrendingUp },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const chemin = usePathname();
  const { utilisateur, deconnexion } = useAuth();

  // Le lien vers l'administration n'apparaît que pour un admin. C'est de
  // l'affichage : l'API refuse ces routes aux autres rôles de toute façon.
  const liens = utilisateur?.role === "admin"
    ? [...LIENS_ELEVE, { href: "/admin", libelle: "Administration", Icone: LayoutDashboard }]
    : LIENS_ELEVE;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-700 dark:bg-slate-900/90">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3">
          <Link href="/" className="flex items-center gap-2 font-semibold">
            <BookOpen className="text-emerald-600" size={20} />
            <span>Agent Tuteur</span>
          </Link>

          <nav className="flex flex-1 items-center gap-1 overflow-x-auto">
            {liens.map(({ href, libelle, Icone }) => {
              const actif = href === "/" ? chemin === "/" : chemin.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  aria-current={actif ? "page" : undefined}
                  className={twMerge(
                    "flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm transition",
                    actif
                      ? "bg-emerald-50 font-medium text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                      : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
                  )}
                >
                  <Icone size={16} />
                  {libelle}
                </Link>
              );
            })}
          </nav>

          <ThemeToggle />
          {utilisateur && (
            <button
              onClick={deconnexion}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              title={utilisateur.email}
            >
              <LogOut size={16} />
              <span className="hidden sm:inline">Déconnexion</span>
            </button>
          )}
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
