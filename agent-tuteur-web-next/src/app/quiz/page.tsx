"use client";

/**
 * Écran de quiz — générer, répondre, voir la correction.
 *
 * Deux principes portés du backend jusqu'ici :
 *
 * 1. **Jamais de questionnaire factice.** Quand l'API répond `available: false`,
 *    le modèle n'a rien produit d'exploitable : on l'annonce et on propose de
 *    réessayer. Afficher un QCM aux propositions « Option 1 / Option 2 »
 *    donnerait l'illusion d'un exercice.
 * 2. **La bonne réponse n'est pas ici.** Elle voyage scellée dans `quiz_token`,
 *    que l'on renvoie tel quel à la correction sans jamais chercher à le lire.
 *    C'est ce qui empêche de trouver la réponse dans les outils de développement.
 */

import { useState } from "react";
import { Award, CheckCircle2, RefreshCw, XCircle } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Markdown } from "@/components/Markdown";
import { Bouton, Carte, Chargement, Etiquette, EtatErreur, Info } from "@/components/ui";
import { quiz, type Quiz, type QuizCorrection } from "@/lib/api";

const CHAPITRES = [
  "Dérivation",
  "Limites",
  "Suites numériques",
  "Nombres complexes",
  "Probabilités",
  "Intégration",
  "Fonction exponentielle",
  "Fonction logarithme",
];

export default function PageQuiz() {
  const [competence, setCompetence] = useState(CHAPITRES[0]);
  const [type, setType] = useState<"qcm" | "vrai_faux">("qcm");
  const [enCours, setEnCours] = useState(false);
  const [sujet, setSujet] = useState<Quiz | null>(null);
  const [choix, setChoix] = useState<string | null>(null);
  const [correction, setCorrection] = useState<QuizCorrection | null>(null);
  const [erreur, setErreur] = useState<unknown>(null);

  async function generer() {
    setEnCours(true);
    setErreur(null);
    setSujet(null);
    setChoix(null);
    setCorrection(null);
    try {
      setSujet(await quiz.generer({ competence, quiz_type: type, curriculum_context: {} }));
    } catch (err) {
      setErreur(err);
    } finally {
      setEnCours(false);
    }
  }

  async function repondre() {
    if (!sujet || !choix) return;
    setEnCours(true);
    setErreur(null);
    try {
      setCorrection(
        // `quiz_token` est opaque : on le retransmet sans l'interpréter.
        await quiz.repondre({ quiz_token: sujet.quiz_token, answer: choix }),
      );
    } catch (err) {
      setErreur(err);
    } finally {
      setEnCours(false);
    }
  }

  return (
    <AppShell>
      <div className="flex flex-col gap-4">
        <h1 className="text-xl font-semibold">Teste tes connaissances</h1>

        <Carte className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="chapitre" className="text-sm font-medium">
              Chapitre
            </label>
            <select
              id="chapitre"
              value={competence}
              onChange={(e) => setCompetence(e.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            >
              {CHAPITRES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="type" className="text-sm font-medium">
              Type
            </label>
            <select
              id="type"
              value={type}
              onChange={(e) => setType(e.target.value as "qcm" | "vrai_faux")}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
            >
              <option value="qcm">Choix multiple</option>
              <option value="vrai_faux">Vrai ou faux</option>
            </select>
          </div>

          <Bouton onClick={generer} disabled={enCours}>
            <RefreshCw size={16} className={enCours ? "animate-spin" : undefined} />
            {sujet ? "Nouvelle question" : "Commencer"}
          </Bouton>
        </Carte>

        {erreur ? <EtatErreur erreur={erreur} onReessayer={generer} /> : null}
        {enCours && !sujet ? <Chargement libelle="Préparation de la question…" /> : null}

        {sujet && !sujet.available && (
          <Info>
            {sujet.instructions}
            <div className="mt-3">
              <Bouton variante="secondaire" onClick={generer}>
                Réessayer
              </Bouton>
            </div>
          </Info>
        )}

        {sujet?.available && (
          <Carte className="flex flex-col gap-4">
            <Markdown>{sujet.question}</Markdown>

            <fieldset className="flex flex-col gap-2" disabled={Boolean(correction)}>
              <legend className="sr-only">Propositions</legend>
              {(sujet.choices ?? []).map((prop) => (
                <Proposition
                  key={prop.id}
                  id={prop.id}
                  texte={prop.text}
                  choisi={choix === prop.id}
                  correction={correction}
                  onChoisir={() => setChoix(prop.id)}
                />
              ))}
            </fieldset>

            {!correction && (
              <Bouton onClick={repondre} disabled={!choix || enCours} className="self-start">
                Valider ma réponse
              </Bouton>
            )}

            {correction && <BlocCorrection correction={correction} />}
          </Carte>
        )}
      </div>
    </AppShell>
  );
}

function Proposition({
  id,
  texte,
  choisi,
  correction,
  onChoisir,
}: {
  id: string;
  texte: string;
  choisi: boolean;
  correction: QuizCorrection | null;
  onChoisir: () => void;
}) {
  const estLaBonne = correction?.correct_answer === id;
  const estMonErreur = correction && choisi && !correction.is_correct;

  const style = estLaBonne
    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950"
    : estMonErreur
      ? "border-red-400 bg-red-50 dark:bg-red-950"
      : choisi
        ? "border-emerald-500"
        : "border-slate-200 dark:border-slate-600";

  return (
    <label
      className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition ${style}`}
    >
      <input
        type="radio"
        name="proposition"
        value={id}
        checked={choisi}
        onChange={onChoisir}
        className="mt-1"
      />
      <span className="font-medium">{id}.</span>
      <span className="flex-1">
        <Markdown>{texte}</Markdown>
      </span>
      {estLaBonne && <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-emerald-600" />}
      {estMonErreur && <XCircle size={18} className="mt-0.5 shrink-0 text-red-500" />}
    </label>
  );
}

function BlocCorrection({ correction }: { correction: QuizCorrection }) {
  const badges = correction.badges ?? [];
  return (
    <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 dark:border-slate-700">
      <div className="flex items-center gap-2">
        {correction.is_correct ? (
          <Etiquette ton="vert">Bonne réponse</Etiquette>
        ) : (
          <Etiquette ton="rouge">Réponse incorrecte</Etiquette>
        )}
        {correction.mastery && (
          <span className="text-xs text-slate-500">
            {correction.mastery.competence} — maîtrise{" "}
            {Math.round(correction.mastery.mastery_score * 100)} %
            {" · "}
            {correction.mastery.attempts} tentative
            {correction.mastery.attempts > 1 ? "s" : ""}
          </span>
        )}
      </div>

      <Markdown>{correction.explanation}</Markdown>

      {badges.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg bg-amber-50 p-3 dark:bg-amber-950">
          <Award size={18} className="text-amber-600" />
          <span className="text-sm font-medium">
            Nouveau badge {badges.length > 1 ? "x" + badges.length : ""} :
          </span>
          {badges.map((b) => (
            <Etiquette key={b.code} ton="jaune">
              {b.label}
            </Etiquette>
          ))}
        </div>
      )}
    </div>
  );
}
