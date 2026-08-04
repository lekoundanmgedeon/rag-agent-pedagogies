"""Génération de quiz — validation stricte du JSON produit par le modèle.

Porté de ``backend/app/agents/quiz_agent.py`` (NURU), avec trois adaptations :

- **asynchrone** : le modèle est appelé via ``BaseLLM`` du dépôt, qui est async
  et ne bloque donc pas le serveur pendant la génération ;
- **sans fournisseur codé en dur** : le prompt de NURU commençait par « Tu es
  Gemini » ; le dépôt route vers plusieurs fournisseurs, la formulation ne peut
  pas en désigner un ;
- **sans niveau codé en dur** : NURU écrivait « niveau Terminale S1 » dans le
  prompt ; ici le cadre curriculaire est passé en paramètre.

Le principe fort de NURU est conservé tel quel : **jamais de contenu factice
affiché à l'élève**. Si le modèle ne produit pas un quiz valide, on renvoie une
liste vide et l'interface le dit — plutôt qu'un QCM aux propositions
« Option 1 / Option 2 », qui donne l'illusion d'un exercice.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from agent_tuteur.agent.llm.base import BaseLLM, LLMError
from agent_tuteur.observability import get_logger, log_event

_logger = get_logger("agent_tuteur.agent.quiz")

#: Traces des anciens gabarits statiques. Si l'une de ces chaînes apparaît dans
#: un quiz, il n'est jamais montré : c'est du remplissage, pas une question.
MARQUEURS_FACTICES: tuple[str, ...] = (
    "définition correcte",
    "definition correcte",
    "définition incorrecte",
    "definition incorrecte",
    "application 1",
    "application 2",
    "application 3",
    "application 4",
    "option 1",
    "option 2",
    "placeholder",
)

#: Nombre d'essais avant d'abandonner. Au-delà, le modèle ne « trouvera » pas :
#: mieux vaut le dire que d'insister.
MAX_TENTATIVES = 2

TYPES_QUIZ = ("qcm", "vrai_faux")

_BLOC_JSON = re.compile(r"\{.*\}", re.DOTALL)


class QuizInvalide(ValueError):
    """Le modèle n'a pas produit de quiz exploitable."""


@dataclass(frozen=True)
class Quiz:
    """Un quiz validé, prêt à être présenté à l'élève."""

    competence: str
    quiz_type: str
    questions: list[dict]

    @property
    def est_utilisable(self) -> bool:
        return bool(self.questions)

    def to_dict(self) -> dict:
        return {
            "competence": self.competence,
            "quiz_type": self.quiz_type,
            "questions": self.questions,
            "instructions": (
                f"Réponds aux questions sur {self.competence}."
                if self.est_utilisable
                else "Le quiz n'a pas pu être généré pour le moment. Réessaie dans un instant."
            ),
        }


def contient_du_factice(donnees: dict) -> bool:
    """Le quiz contient-il du texte de remplissage plutôt que du contenu ?"""
    serialise = json.dumps(donnees, ensure_ascii=False).lower()
    return any(marqueur in serialise for marqueur in MARQUEURS_FACTICES)


def _explication_coherente(
    bonne_reponse: str, propositions: list[dict], explication_generee: str | None
) -> str:
    """Garantit que l'explication désigne bien la réponse marquée correcte.

    Le modèle produit régulièrement un JSON parfaitement formé dans lequel
    ``correct_answer`` désigne A tandis que l'explication justifie C. L'élève
    voit alors une correction qui se contredit. On construit donc une phrase
    canonique à partir de ``correct_answer``, et on ne garde l'explication du
    modèle que si elle mentionne la bonne proposition **et aucune autre**.
    """
    bonne = next(p for p in propositions if p["id"] == bonne_reponse)
    texte_bon = str(bonne["text"]).strip()
    canonique = f"La bonne réponse est {bonne_reponse} : {texte_bon}."

    generee = str(explication_generee or "").strip()
    if not generee:
        return canonique

    generee_norm = generee.casefold()
    mentionne_la_bonne = bool(texte_bon) and texte_bon.casefold() in generee_norm
    mentionne_une_autre = any(
        (autre := str(p["text"]).strip().casefold()) and autre in generee_norm
        for p in propositions
        if p["id"] != bonne_reponse
    )
    if mentionne_la_bonne and not mentionne_une_autre:
        return f"{canonique} {generee}"
    return canonique


def analyser_reponse_quiz(brut: str) -> dict | None:
    """Extrait et valide le quiz contenu dans la réponse brute du modèle.

    Le modèle entoure souvent son JSON de texte libre ou de balises markdown :
    on récupère le premier bloc entre accolades. Renvoie ``None`` dès qu'une
    règle n'est pas respectée — il n'y a pas de réparation partielle, un quiz
    à moitié valide est un quiz faux.
    """
    if not brut:
        return None
    bloc = _BLOC_JSON.search(brut)
    if not bloc:
        return None
    try:
        donnees = json.loads(bloc.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(donnees, dict):
        return None

    question = donnees.get("question")
    propositions = donnees.get("choices")
    bonne_reponse = donnees.get("correct_answer")

    if not question or not isinstance(propositions, list) or len(propositions) < 2:
        return None
    if not all(isinstance(p, dict) and p.get("id") and p.get("text") for p in propositions):
        return None
    if bonne_reponse not in {p["id"] for p in propositions}:
        return None

    return {
        "question": question,
        "choices": propositions,
        "correct_answer": bonne_reponse,
        "explanation": _explication_coherente(
            bonne_reponse, propositions, donnees.get("explanation")
        ),
    }


def construire_prompt_quiz(
    competence: str, quiz_type: str, contexte_curriculaire: str = "", extraits: str = ""
) -> str:
    """Consigne envoyée au modèle. Volontairement très directive sur le format."""
    if quiz_type == "vrai_faux":
        contrainte = (
            'Exactement 2 propositions : {"id": "A", "text": "Vrai"} et '
            '{"id": "B", "text": "Faux"}.'
        )
    else:
        contrainte = "Exactement 4 propositions distinctes, une seule correcte."

    cadre = f" de niveau {contexte_curriculaire}" if contexte_curriculaire else ""
    parts = [
        f"Génère UNE SEULE question de quiz de type {quiz_type} sur « {competence} »{cadre}.",
        "Utilise la notation LaTeX ($…$) pour les formules mathématiques.",
        "Réponds STRICTEMENT avec un unique objet JSON, sans texte avant ni après, "
        "sans balise markdown, au format exact suivant :",
        '{"question": "...", "choices": [{"id": "A", "text": "..."}, {"id": "B", "text": "..."}, '
        '{"id": "C", "text": "..."}, {"id": "D", "text": "..."}], '
        '"correct_answer": "A", "explanation": "..."}',
        contrainte,
        "Les propositions doivent être des affirmations mathématiques réelles et distinctes, "
        'jamais du texte générique comme "Option 1" ou "Définition incorrecte".',
        "La valeur de correct_answer doit désigner exactement la proposition justifiée "
        "par explanation ; explanation ne doit justifier aucune autre proposition.",
    ]
    if extraits:
        parts.append(f"Extraits de cours pour t'appuyer :\n{extraits}")
    return "\n".join(parts)


async def generer_quiz(
    llm: BaseLLM,
    competence: str,
    *,
    quiz_type: str = "qcm",
    contexte_curriculaire: str = "",
    extraits: str = "",
) -> Quiz:
    """Demande un quiz au modèle et ne renvoie que s'il est valide.

    Un quiz vide (``est_utilisable`` faux) n'est **pas** une erreur : c'est le
    résultat honnête d'un modèle qui n'a pas produit de contenu exploitable.
    L'appelant doit le dire à l'élève, pas afficher un exercice factice.
    """
    if quiz_type not in TYPES_QUIZ:
        raise QuizInvalide(f"Type de quiz inconnu : {quiz_type!r} (attendu : {TYPES_QUIZ}).")

    prompt = construire_prompt_quiz(competence, quiz_type, contexte_curriculaire, extraits)

    for tentative in range(1, MAX_TENTATIVES + 1):
        try:
            brut = await llm.generate(prompt)
        except LLMError as exc:
            log_event(
                _logger, "quiz:echec_llm", log_level=logging.WARNING,
                competence=competence, tentative=tentative, error=str(exc),
            )
            continue

        valide = analyser_reponse_quiz(brut)
        if valide is not None and not contient_du_factice(valide):
            return Quiz(competence=competence, quiz_type=quiz_type, questions=[valide])

        log_event(
            _logger, "quiz:reponse_rejetee", log_level=logging.WARNING,
            competence=competence, tentative=tentative, max_tentatives=MAX_TENTATIVES,
            raison="json_invalide" if valide is None else "contenu_factice",
        )

    return Quiz(competence=competence, quiz_type=quiz_type, questions=[])


def corriger_quiz(quiz_question: dict, reponse_eleve: str) -> dict:
    """Corrige la réponse d'un élève à une question de quiz.

    Correction **déterministe** : on compare deux identifiants, aucun modèle de
    langage n'intervient. Un élève ne doit jamais voir sa réponse jugée
    différemment d'une fois à l'autre.
    """
    bonne = quiz_question.get("correct_answer")
    donnee = (reponse_eleve or "").strip()
    est_correct = bool(donnee) and donnee.casefold() == str(bonne).casefold()
    return {
        "is_correct": est_correct,
        "correct_answer": bonne,
        "given_answer": donnee,
        "explanation": quiz_question.get("explanation", ""),
        "score": 1.0 if est_correct else 0.0,
    }
