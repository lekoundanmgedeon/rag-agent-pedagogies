"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { twMerge } from "tailwind-merge";
import { AppShell } from "@/components/AppShell";

const ONGLETS = [
  { href: "/admin", libelle: "Tableau de bord" },
  { href: "/admin/documents", libelle: "Documents" },
  { href: "/admin/utilisateurs", libelle: "Utilisateurs" },
  { href: "/admin/recherche", libelle: "Recherche" },
  { href: "/admin/journaux", libelle: "Journaux" },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const chemin = usePathname();

  return (
    <AppShell>
      <div className="flex flex-col gap-5">
        <nav className="flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-slate-700">
          {ONGLETS.map(({ href, libelle }) => {
            const actif = href === "/admin" ? chemin === "/admin" : chemin.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={actif ? "page" : undefined}
                className={twMerge(
                  "whitespace-nowrap border-b-2 px-3 py-2 text-sm transition",
                  actif
                    ? "border-emerald-600 font-medium text-emerald-700 dark:text-emerald-300"
                    : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200",
                )}
              >
                {libelle}
              </Link>
            );
          })}
        </nav>
        {children}
      </div>
    </AppShell>
  );
}
