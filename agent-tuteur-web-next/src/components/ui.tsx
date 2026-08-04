"use client";

/**
 * Briques d'interface partagées.
 *
 * `EtatErreur` mérite une mention : c'est la contrepartie de la règle « aucune
 * donnée inventée » de `lib/api.ts`. Puisqu'une panne d'API lève une erreur au
 * lieu de renvoyer des chiffres plausibles, chaque écran doit savoir afficher
 * cette erreur — et proposer de réessayer.
 */

import { AlertCircle, Loader2 } from "lucide-react";
import { twMerge } from "tailwind-merge";

export function Carte({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={twMerge(
        "rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-700 dark:bg-slate-800",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Bouton({
  variante = "principal",
  className,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variante?: "principal" | "secondaire" }) {
  const styles = {
    principal:
      "bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-emerald-600/50",
    secondaire:
      "border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-200 dark:hover:bg-slate-700",
  }[variante];

  return (
    <button
      {...props}
      className={twMerge(
        "inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed",
        styles,
        className,
      )}
    />
  );
}

export function Chargement({ libelle = "Chargement…" }: { libelle?: string }) {
  return (
    <div className="flex items-center gap-2 p-6 text-sm text-slate-500" role="status">
      <Loader2 className="animate-spin" size={16} />
      {libelle}
    </div>
  );
}

export function EtatErreur({ erreur, onReessayer }: { erreur: unknown; onReessayer?: () => void }) {
  const message = erreur instanceof Error ? erreur.message : "Une erreur est survenue.";
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-xl border border-red-200 bg-red-50 p-5 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200"
    >
      <div className="flex items-start gap-2">
        <AlertCircle size={18} className="mt-0.5 shrink-0" />
        <span>{message}</span>
      </div>
      {onReessayer && (
        <Bouton variante="secondaire" onClick={onReessayer} className="self-start">
          Réessayer
        </Bouton>
      )}
    </div>
  );
}

/** Bandeau d'information neutre — ni erreur, ni succès. */
export function Info({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800/50 dark:text-slate-300">
      {children}
    </div>
  );
}

export function Etiquette({
  ton = "neutre",
  children,
}: {
  ton?: "neutre" | "vert" | "jaune" | "rouge";
  children: React.ReactNode;
}) {
  const styles = {
    neutre: "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-200",
    vert: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200",
    jaune: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
    rouge: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  }[ton];
  return (
    <span className={twMerge("rounded-full px-2.5 py-0.5 text-xs font-medium", styles)}>
      {children}
    </span>
  );
}
