"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BookOpen } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import { Bouton, Carte, EtatErreur } from "@/components/ui";

function Formulaire() {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);
  const { connexion } = useAuth();
  const router = useRouter();
  const params = useSearchParams();

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setErreur(null);
    setEnvoi(true);
    try {
      const utilisateur = await connexion(email, motDePasse);
      // On retourne là où l'utilisateur voulait aller ; à défaut, un admin
      // arrive sur son tableau de bord, un élève sur le tuteur.
      const demande = params.get("redirect");
      router.push(demande ?? (utilisateur.role === "admin" ? "/admin" : "/"));
    } catch (err) {
      setErreur(err);
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <form onSubmit={soumettre} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="email" className="text-sm font-medium">
          Adresse e-mail
        </label>
        <input
          id="email"
          type="email"
          required
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 dark:border-slate-600 dark:bg-slate-900"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="mdp" className="text-sm font-medium">
          Mot de passe
        </label>
        <input
          id="mdp"
          type="password"
          required
          autoComplete="current-password"
          value={motDePasse}
          onChange={(e) => setMotDePasse(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-emerald-500 dark:border-slate-600 dark:bg-slate-900"
        />
      </div>

      {erreur ? <EtatErreur erreur={erreur} /> : null}

      <Bouton type="submit" disabled={envoi}>
        {envoi ? "Connexion…" : "Se connecter"}
      </Bouton>
    </form>
  );
}

export default function PageConnexion() {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <BookOpen className="text-emerald-600" size={32} />
          <h1 className="text-xl font-semibold">Agent Tuteur Sénégal</h1>
          <p className="text-sm text-slate-500">
            Révise avec un tuteur qui te guide, sans te donner la réponse.
          </p>
        </div>

        <Carte>
          <Suspense fallback={null}>
            <Formulaire />
          </Suspense>
        </Carte>

        <p className="mt-4 text-center text-xs text-slate-500">
          Pas de compte ? Demande-le à ton établissement — les comptes sont créés
          par un administrateur.
        </p>
      </div>
    </div>
  );
}
