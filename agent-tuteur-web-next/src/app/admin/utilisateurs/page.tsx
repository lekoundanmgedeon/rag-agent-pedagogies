"use client";

/**
 * Gestion des comptes.
 *
 * Les quatre rôles de la migration `0007_extend_roles` sont proposés. Rappel
 * utile à l'administrateur : donner le rôle `teacher` ou `parent` n'ouvre
 * l'accès à **aucun** élève tant qu'aucune liaison n'existe en base — c'est la
 * table `student_links` qui décide, pas le rôle.
 */

import { useCallback, useEffect, useState } from "react";
import { UserPlus } from "lucide-react";
import { Bouton, Carte, Chargement, Etiquette, EtatErreur, Info } from "@/components/ui";
import { auth, type User } from "@/lib/api";

const ROLES = ["student", "teacher", "parent", "admin"] as const;
type Role = (typeof ROLES)[number];

const LIBELLE_ROLE: Record<Role, string> = {
  student: "Élève",
  teacher: "Enseignant",
  parent: "Parent",
  admin: "Administrateur",
};

export default function PageUtilisateurs() {
  const [liste, setListe] = useState<User[] | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);
  const [ouvert, setOuvert] = useState(false);

  const charger = useCallback(() => {
    setErreur(null);
    auth.listerComptes().then(setListe).catch(setErreur);
  }, []);

  useEffect(charger, [charger]);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">Comptes</h1>
        <Bouton onClick={() => setOuvert((o) => !o)}>
          <UserPlus size={16} /> Nouveau compte
        </Bouton>
      </div>

      {ouvert && (
        <FormulaireCompte
          onCree={() => {
            setOuvert(false);
            charger();
          }}
        />
      )}

      {erreur ? <EtatErreur erreur={erreur} onReessayer={charger} /> : null}
      {liste === null && !erreur ? <Chargement /> : null}
      {liste?.length === 0 && <Info>Aucun compte dans cet établissement.</Info>}

      {liste && liste.length > 0 && (
        <Carte className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-200 text-left text-xs uppercase text-slate-500 dark:border-slate-700">
              <tr>
                <th className="px-4 py-2">E-mail</th>
                <th className="px-4 py-2">Rôle</th>
                <th className="px-4 py-2">Identifiant élève</th>
              </tr>
            </thead>
            <tbody>
              {liste.map((u) => (
                <tr key={u.id} className="border-b border-slate-100 last:border-0 dark:border-slate-700">
                  <td className="px-4 py-2">
                    {u.email}
                    {u.display_name && (
                      <span className="ml-2 text-xs text-slate-500">{u.display_name}</span>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <Etiquette ton={u.role === "admin" ? "jaune" : "neutre"}>
                      {LIBELLE_ROLE[u.role as Role] ?? u.role}
                    </Etiquette>
                  </td>
                  <td className="px-4 py-2 text-slate-500">{u.student_id ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Carte>
      )}
    </div>
  );
}

function FormulaireCompte({ onCree }: { onCree: () => void }) {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [role, setRole] = useState<Role>("student");
  const [studentId, setStudentId] = useState("");
  const [erreur, setErreur] = useState<unknown>(null);
  const [envoi, setEnvoi] = useState(false);

  async function soumettre(e: React.FormEvent) {
    e.preventDefault();
    setEnvoi(true);
    setErreur(null);
    try {
      await auth.creerCompte({
        email,
        password: motDePasse,
        role,
        student_id: role === "student" ? studentId || null : null,
      });
      onCree();
    } catch (err) {
      setErreur(err);
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <Carte>
      <form onSubmit={soumettre} className="flex flex-col gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            Adresse e-mail
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-900"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            Mot de passe
            <input
              type="password"
              required
              minLength={6}
              value={motDePasse}
              onChange={(e) => setMotDePasse(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-900"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            Rôle
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-900"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {LIBELLE_ROLE[r]}
                </option>
              ))}
            </select>
          </label>

          {role === "student" && (
            <label className="flex flex-col gap-1 text-sm">
              Identifiant élève
              <input
                value={studentId}
                onChange={(e) => setStudentId(e.target.value)}
                placeholder="ex. eleve-042"
                className="rounded-lg border border-slate-300 px-3 py-2 dark:border-slate-600 dark:bg-slate-900"
              />
            </label>
          )}
        </div>

        {(role === "teacher" || role === "parent") && (
          <Info>
            Ce rôle ne donne accès à aucun élève tant qu&apos;aucune liaison
            n&apos;a été créée. Les écrans de rattachement arrivent en v1.1.
          </Info>
        )}

        {erreur ? <EtatErreur erreur={erreur} /> : null}

        <Bouton type="submit" disabled={envoi} className="self-start">
          {envoi ? "Création…" : "Créer le compte"}
        </Bouton>
      </form>
    </Carte>
  );
}
