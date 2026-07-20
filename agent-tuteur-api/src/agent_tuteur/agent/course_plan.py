"""Plan pédagogique du **mode cours** — progression didactique section par section.

Ce module encode la table des matières du **format pilote** des leçons
(``lessons/Lecon_*.md``), qui fixe 18 sections. Pour une conversation avec un
élève, on retient une **progression curée de 8 étapes** — digeste en dialogue —
tirée de ces sections, en écartant les blocs d'*auteur* (Métadonnées RAG,
Découpage pour vectorisation, Contrôle qualité) qui ne concernent pas
l'apprentissage.

Chaque étape porte une **instruction de rédaction** (à la manière de
``HINT_INSTRUCTIONS``) injectée dans le prompt du LLM au moment d'enseigner la
section. Le module ne *génère* rien : il décrit la progression et fournit la
consigne, l'assemblage restant à ``prompt.assemble_course_prompt``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_tuteur.agent.intent import Navigation


@dataclass(frozen=True)
class Section:
    #: Clé stable (persistée dans la trace, indépendante de la langue d'affichage).
    key: str
    #: Titre affiché à l'élève.
    title: str
    #: Consigne de rédaction pour le LLM lorsqu'il enseigne cette section.
    instruction: str


# Progression didactique (8 étapes) — agrège les 18 sections du format pilote.
LESSON_SECTIONS: tuple[Section, ...] = (
    Section(
        "introduction",
        "Introduction",
        "Situe le chapitre : à quoi il sert, d'où il vient, où il intervient au "
        "Baccalauréat, et ses applications concrètes. Reste motivant et bref. "
        "N'entre pas encore dans les définitions formelles.",
    ),
    Section(
        "definitions",
        "Définitions",
        "Énonce les définitions clés une par une, avec la notation exacte, à "
        "partir des extraits. Illustre chaque définition d'un mini-exemple "
        "immédiat. Ne démontre rien ici.",
    ),
    Section(
        "theoremes",
        "Théorèmes et propriétés",
        "Présente les théorèmes et propriétés essentiels : énoncé, conditions "
        "d'application, et une justification courte quand elle éclaire (sans "
        "dérouler toutes les démonstrations). Mets en garde sur les hypothèses.",
    ),
    Section(
        "methodes",
        "Méthodes",
        "Décris les méthodes-types du chapitre sous forme d'étapes numérotées "
        "réutilisables (« pour faire X : 1… 2… 3… »), telles qu'attendues au Bac.",
    ),
    Section(
        "exemples",
        "Exemples résolus",
        "Déroule un ou deux exemples entièrement résolus, étape par étape, en "
        "explicitant le raisonnement à chaque ligne. C'est ici qu'on montre "
        "comment appliquer méthodes et théorèmes.",
    ),
    Section(
        "erreurs",
        "Erreurs fréquentes et astuces",
        "Liste les erreurs classiques à éviter et les astuces de calcul, de "
        "rédaction et de Bac. Formule chaque point de façon actionnable.",
    ),
    Section(
        "exercices",
        "Exercices d'application",
        "Propose des exercices d'application progressifs (facile → difficile) "
        "SANS donner les corrigés d'emblée : invite l'élève à s'y essayer et "
        "à demander une correction ou un indice s'il bloque. Ici la posture "
        "redevient légèrement socratique.",
    ),
    Section(
        "resume",
        "Résumé et fiche de révision",
        "Synthétise l'essentiel du chapitre en une fiche de révision compacte : "
        "formules-clés, résultats à retenir, en quelques puces. Clôture le cours.",
    ),
)

_SECTION_BY_KEY: dict[str, int] = {s.key: i for i, s in enumerate(LESSON_SECTIONS)}

FIRST_INDEX = 0
LAST_INDEX = len(LESSON_SECTIONS) - 1


def plan_titles() -> list[str]:
    """Titres des sections, dans l'ordre — le sommaire annoncé à l'élève."""
    return [s.title for s in LESSON_SECTIONS]


def section_at(index: int) -> Section:
    """Section à l'indice donné, borné à ``[FIRST_INDEX, LAST_INDEX]``."""
    return LESSON_SECTIONS[clamp_index(index)]


def clamp_index(index: int) -> int:
    return max(FIRST_INDEX, min(LAST_INDEX, index))


# Mots-clés → clé de section, pour résoudre un saut (« passe aux exercices »).
_GOTO_KEYWORDS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bintroduction|intro\b", re.IGNORECASE), "introduction"),
    (re.compile(r"\bd[ée]finitions?\b", re.IGNORECASE), "definitions"),
    (re.compile(r"\bth[ée]or[èe]mes?|propri[ée]t[ée]s?\b", re.IGNORECASE), "theoremes"),
    (re.compile(r"\bm[ée]thodes?\b", re.IGNORECASE), "methodes"),
    (re.compile(r"\bexemples?\b", re.IGNORECASE), "exemples"),
    (re.compile(r"\berreurs?|astuces?|pi[èe]ges?\b", re.IGNORECASE), "erreurs"),
    (re.compile(r"\bexercices?\b", re.IGNORECASE), "exercices"),
    (re.compile(r"\br[ée]sum[ée]|r[ée]vision|fiche\b", re.IGNORECASE), "resume"),
)


def resolve_goto(question: str) -> int | None:
    """Indice de la section nommée dans la question, ou ``None`` si aucune.

    « exercices » est testé en dernier via l'ordre de ``_GOTO_KEYWORDS`` : on
    renvoie la **première** section mentionnée dans l'ordre du plan.
    """
    matches = [
        _SECTION_BY_KEY[key] for pattern, key in _GOTO_KEYWORDS if pattern.search(question)
    ]
    return min(matches) if matches else None


@dataclass
class CoursePosition:
    """Où en est l'élève dans le cours d'un chapitre."""

    chapitre: str | None
    section_index: int
    reason: str

    def to_state(self) -> dict:
        """Forme sérialisable persistée dans ``messages.trace['course']``."""
        return {"chapitre": self.chapitre, "section_index": self.section_index}

    @property
    def section(self) -> Section:
        return section_at(self.section_index)


def advance(
    previous: dict | None,
    navigation: Navigation | None,
    question: str,
    *,
    chapitre_fallback: str | None,
) -> CoursePosition:
    """Calcule la position dans le cours pour le tour courant.

    * ``START`` ou absence de cours antérieur → nouveau cours (section 0),
      chapitre déduit du contexte/extraits (``chapitre_fallback``).
    * ``NEXT`` / ``PREV`` → déplacement borné dans le plan du cours en cours.
    * ``GOTO`` → saut à la section nommée (à défaut, on ne bouge pas).
    * poursuite sans marqueur (``None``) → on reste sur la section courante
      (l'élève pose une sous-question sur la section en cours).
    """
    prev_index = (previous or {}).get("section_index", FIRST_INDEX)
    prev_chapitre = (previous or {}).get("chapitre")

    if navigation == Navigation.START or not previous:
        return CoursePosition(chapitre_fallback or prev_chapitre, FIRST_INDEX, "début du cours")

    if navigation == Navigation.NEXT:
        idx = clamp_index(prev_index + 1)
        reason = "section suivante" if idx != prev_index else "déjà à la dernière section"
        return CoursePosition(prev_chapitre, idx, reason)

    if navigation == Navigation.PREV:
        idx = clamp_index(prev_index - 1)
        reason = "section précédente" if idx != prev_index else "déjà à la première section"
        return CoursePosition(prev_chapitre, idx, reason)

    if navigation == Navigation.GOTO:
        target = resolve_goto(question)
        if target is not None:
            return CoursePosition(prev_chapitre, target, f"saut vers « {section_at(target).title} »")
        return CoursePosition(prev_chapitre, prev_index, "saut non résolu, section inchangée")

    return CoursePosition(prev_chapitre, clamp_index(prev_index), "poursuite sur la section courante")
