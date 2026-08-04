"use client";

/**
 * Progression de l'élève — maîtrise par compétence, badges, historique.
 *
 * Trois appels indépendants (`/api/mastery`, `/api/evaluation`,
 * `/api/progression`). Ils sont lancés ensemble mais affichés séparément : si
 * l'un échoue, les deux autres restent visibles. Un seul bloc en erreur vaut
 * mieux qu'une page blanche.
 */

import { useCallback, useEffect, useState } from "react";
import { Award, History, Target } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { useStudentId } from "@/components/AuthProvider";
import { Carte, Chargement, Etiquette, EtatErreur, Info } from "@/components/ui";
import {
  evaluation,
  maitrise,
  progression,
  type EvaluationHistory,
  type Mastery,
  type MasteryEntry,
  type Progression,
} from "@/lib/api";

/** État d'un chargement : ni « données », ni « erreur » tant qu'on ignore. */
type Etat<T> = { statut: "chargement" } | { statut: "ok"; donnees: T } | { statut: "erreur"; erreur: unknown };

function useChargement<T>(charger: () => Promise<T>, actif: boolean): [Etat<T>, () => void] {
  const [etat, setEtat] = useState<Etat<T>>({ statut: "chargement" });

  const relancer = useCallback(() => {
    if (!actif) return;
    setEtat({ statut: "chargement" });
    charger()
      .then((donnees) => setEtat({ statut: "ok", donnees }))
      .catch((erreur) => setEtat({ statut: "erreur", erreur }));
  }, [charger, actif]);

  useEffect(relancer, [relancer]);
  return [etat, relancer];
}

export default function PageProgression() {
  const studentId = useStudentId();

  const chargerMaitrise = useCallback(() => maitrise.lire(studentId!), [studentId]);
  const chargerHistorique = useCallback(() => evaluation.historique(studentId!), [studentId]);
  const chargerProgression = useCallback(() => progression.lire(studentId!), [studentId]);

  const [etatMaitrise, relancerMaitrise] = useChargement<Mastery>(chargerMaitrise, Boolean(studentId));
  const [etatHistorique, relancerHistorique] = useChargement<EvaluationHistory>(
    chargerHistorique,
    Boolean(studentId),
  );
  const [etatProgression, relancerProgression] = useChargement<Progression>(
    chargerProgression,
    Boolean(studentId),
  );

  if (!studentId) {
    return (
      <AppShell>
        <Info>Ce compte n&apos;est pas rattaché à un parcours élève.</Info>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-6">
        <h1 className="text-xl font-semibold">Ma progression</h1>

        <section className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-sm font-medium text-slate-500">
            <Target size={16} /> Maîtrise par compétence
          </h2>
          {etatMaitrise.statut === "chargement" && <Chargement />}
          {etatMaitrise.statut === "erreur" && (
            <EtatErreur erreur={etatMaitrise.erreur} onReessayer={relancerMaitrise} />
          )}
          {etatMaitrise.statut === "ok" && <BlocMaitrise donnees={etatMaitrise.donnees} />}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="flex items-center gap-2 text-sm font-medium text-slate-500">
            <History size={16} /> Exercices et quiz terminés
          </h2>
          {etatHistorique.statut === "chargement" && <Chargement />}
          {etatHistorique.statut === "erreur" && (
            <EtatErreur erreur={etatHistorique.erreur} onReessayer={relancerHistorique} />
          )}
          {etatHistorique.statut === "ok" && (
            <BlocHistorique donnees={etatHistorique.donnees} />
          )}
        </section>

        <section className="flex flex-col gap-3">
          <h2 className="text-sm font-medium text-slate-500">Difficultés récurrentes</h2>
          {etatProgression.statut === "chargement" && <Chargement />}
          {etatProgression.statut === "erreur" && (
            <EtatErreur erreur={etatProgression.erreur} onReessayer={relancerProgression} />
          )}
          {etatProgression.statut === "ok" &&
            (etatProgression.donnees.recurrent_difficulties.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {etatProgression.donnees.recurrent_difficulties.map((d) => (
                  <Etiquette key={d} ton="jaune">
                    {d}
                  </Etiquette>
                ))}
              </div>
            ) : (
              <Info>
                Aucune difficulté récurrente repérée — ce sont les notions où tu as
                eu besoin des indices les plus poussés, à plusieurs reprises.
              </Info>
            ))}
        </section>
      </div>
    </AppShell>
  );
}

const TON_STATUT = {
  maitrise: "vert",
  en_cours: "jaune",
  faible: "rouge",
  non_commence: "neutre",
} as const;

const LIBELLE_STATUT = {
  maitrise: "Maîtrisé",
  en_cours: "En cours",
  faible: "À retravailler",
  non_commence: "Pas commencé",
} as const;

function BlocMaitrise({ donnees }: { donnees: Mastery }) {
  if (donnees.competences.length === 0) {
    return (
      <Info>
        Rien à afficher pour l&apos;instant. Fais un quiz : ta maîtrise se
        construit à mesure que tu réponds.
      </Info>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {donnees.weakest.length > 0 && (
        <Carte className="bg-amber-50 dark:bg-amber-950/40">
          <p className="mb-2 text-sm font-medium">À retravailler en priorité</p>
          <div className="flex flex-wrap gap-2">
            {donnees.weakest.map((m) => (
              <Etiquette key={m.competence} ton="jaune">
                {m.competence}
              </Etiquette>
            ))}
          </div>
        </Carte>
      )}

      <Carte className="flex flex-col gap-3">
        {donnees.competences.map((m) => (
          <LigneMaitrise key={m.competence} entree={m} />
        ))}
      </Carte>

      {(donnees.badges ?? []).length > 0 && (
        <Carte>
          <p className="mb-2 flex items-center gap-2 text-sm font-medium">
            <Award size={16} className="text-amber-600" /> Badges obtenus
          </p>
          <div className="flex flex-wrap gap-2">
            {donnees.badges.map((b) => (
              <Etiquette key={b.code} ton="jaune">
                {b.label}
              </Etiquette>
            ))}
          </div>
        </Carte>
      )}
    </div>
  );
}

function LigneMaitrise({ entree }: { entree: MasteryEntry }) {
  const pourcent = Math.round(entree.mastery_score * 100);
  const statut = (entree.statut in LIBELLE_STATUT ? entree.statut : "non_commence") as keyof typeof LIBELLE_STATUT;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2 text-sm">
        <span className="font-medium">{entree.competence}</span>
        <div className="flex items-center gap-2">
          <Etiquette ton={TON_STATUT[statut]}>{LIBELLE_STATUT[statut]}</Etiquette>
          <span className="tabular-nums text-slate-500">{pourcent} %</span>
        </div>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700"
        role="progressbar"
        aria-valuenow={pourcent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Maîtrise de ${entree.competence}`}
      >
        <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${pourcent}%` }} />
      </div>
      <p className="text-xs text-slate-500">
        {entree.successes} réussite{entree.successes > 1 ? "s" : ""} sur {entree.attempts}{" "}
        tentative{entree.attempts > 1 ? "s" : ""}
      </p>
    </div>
  );
}

function BlocHistorique({ donnees }: { donnees: EvaluationHistory }) {
  if (donnees.results.length === 0) {
    return <Info>Aucun exercice ni quiz terminé pour l&apos;instant.</Info>;
  }

  return (
    <Carte className="overflow-x-auto p-0">
      <table className="w-full text-sm">
        <thead className="border-b border-slate-200 text-left text-xs uppercase text-slate-500 dark:border-slate-700">
          <tr>
            <th className="px-4 py-2">Compétence</th>
            <th className="px-4 py-2">Type</th>
            <th className="px-4 py-2">Résultat</th>
            <th className="px-4 py-2">Date</th>
          </tr>
        </thead>
        <tbody>
          {donnees.results.map((r) => (
            <tr key={r.id} className="border-b border-slate-100 last:border-0 dark:border-slate-700">
              <td className="px-4 py-2">{r.competence ?? "—"}</td>
              <td className="px-4 py-2">{r.exercise_type}</td>
              <td className="px-4 py-2">
                {r.is_correct === null || r.is_correct === undefined ? (
                  "—"
                ) : r.is_correct ? (
                  <Etiquette ton="vert">Réussi</Etiquette>
                ) : (
                  <Etiquette ton="rouge">Manqué</Etiquette>
                )}
              </td>
              <td className="px-4 py-2 text-slate-500">
                {new Date(r.created_at).toLocaleDateString("fr-FR")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Carte>
  );
}
