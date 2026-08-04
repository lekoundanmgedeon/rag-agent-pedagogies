"use client";

/**
 * État d'authentification partagé.
 *
 * **Aucun repli local.** Si l'API ne répond pas, la connexion échoue — point.
 * Le frontend NURU faisait l'inverse : en cas de backend injoignable, il
 * fabriquait un utilisateur et déduisait son rôle de l'adresse e-mail, ce qui
 * ouvrait l'espace d'administration à qui coupait son réseau. Un backend
 * injoignable est une **erreur**, pas une connexion réussie.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, auth, effacerJeton, ecrireJeton, lireJeton, type User } from "@/lib/api";

type EtatAuth = {
  utilisateur: User | null;
  /** Vrai tant qu'on n'a pas fini de restaurer la session au chargement. */
  chargement: boolean;
  connexion: (email: string, motDePasse: string) => Promise<User>;
  deconnexion: () => void;
};

const Contexte = createContext<EtatAuth | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<User | null>(null);
  const [chargement, setChargement] = useState(true);
  const router = useRouter();

  // Restauration de session : le jeton survit à un rechargement, mais on
  // redemande le profil à l'API plutôt que de faire confiance à ce qui traîne
  // dans le navigateur.
  useEffect(() => {
    if (!lireJeton()) {
      setChargement(false);
      return;
    }
    auth
      .moi()
      .then(setUtilisateur)
      .catch(() => effacerJeton())
      .finally(() => setChargement(false));
  }, []);

  const connexion = useCallback(async (email: string, motDePasse: string) => {
    try {
      const jeton = await auth.connexion(email, motDePasse);
      ecrireJeton(jeton.access_token);
      setUtilisateur(jeton.user);
      return jeton.user;
    } catch (err) {
      effacerJeton();
      if (err instanceof ApiError) throw err;
      // Réseau coupé, API arrêtée, DNS… : on le dit, on n'invente pas de session.
      throw new ApiError("Service indisponible, réessayez dans un instant.", 0);
    }
  }, []);

  const deconnexion = useCallback(() => {
    effacerJeton();
    setUtilisateur(null);
    router.push("/login");
  }, [router]);

  const valeur = useMemo(
    () => ({ utilisateur, chargement, connexion, deconnexion }),
    [utilisateur, chargement, connexion, deconnexion],
  );

  return <Contexte.Provider value={valeur}>{children}</Contexte.Provider>;
}

export function useAuth(): EtatAuth {
  const ctx = useContext(Contexte);
  if (!ctx) throw new Error("useAuth doit être utilisé à l'intérieur de <AuthProvider>.");
  return ctx;
}

/** Identifiant élève effectif du compte courant (un admin n'en a pas). */
export function useStudentId(): string | null {
  const { utilisateur } = useAuth();
  return utilisateur?.student_id ?? utilisateur?.id ?? null;
}
