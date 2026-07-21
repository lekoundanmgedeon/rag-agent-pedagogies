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
from collections.abc import Iterable
from dataclasses import dataclass

from agent_tuteur.agent.intent import Navigation
from agent_tuteur.textutil import tokenize


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


# --- Liaison du chapitre à la demande de l'élève -----------------------------
# Mots outils d'une demande de cours (« explique-moi les… », « c'est quoi… ») :
# ils encadrent le sujet sans jamais l'identifier. On les retire pour ne garder
# que les termes qui nomment réellement le chapitre voulu.
_TOPIC_STOPWORDS = frozenset(
    tokenize(
        "explique expliquer expliques moi nous presente presenter enseigne enseigner "
        "apprends apprendre initie initier fais faire donne donner cours chapitre "
        "lecon veux voudrais aimerais comprendre reviser reviser etudier revoir "
        "est quoi ce que qui les le la des du de un une aux au sur pour dans avec "
        "par en et ou mais plus tout tous toute toutes mon ma mes ton ta tes stp "
        "svp merci peux peut tu je il elle on nous vous ils elles"
    )
)

#: Longueur minimale d'un terme retenu comme identifiant de sujet (écarte « ai », « on »…).
_MIN_TOPIC_TERM_LEN = 3


def _stem(token: str) -> str:
    """Forme comparable d'un terme : pluriel français retiré.

    « dérivées » et « dérivée », « nombres » et « nombre » désignent le même
    chapitre ; sans cette normalisation, la liaison échouerait sur un simple
    accord entre la question de l'élève et le titre du chapitre.
    """
    return token[:-1] if len(token) > 3 and token.endswith(("s", "x")) else token


def topic_terms(question: str) -> list[str]:
    """Termes de la question qui **nomment le sujet** demandé.

    « Explique-moi les nombres complexes » → ``["nombres", "complexes"]``. C'est
    ce qui permet de vérifier que le chapitre lié correspond bien à la demande,
    au lieu de faire aveuglément confiance au meilleur extrait remonté.
    """
    return [
        t
        for t in tokenize(question)
        if t not in _TOPIC_STOPWORDS and len(t) >= _MIN_TOPIC_TERM_LEN
    ]


_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def topic_label(question: str) -> str:
    """Sujet demandé, dans la graphie de l'élève (« équations différentielles »).

    ``topic_terms`` sert à *comparer* (donc minuscule et sans accents) ; ce label
    sert à *citer* le sujet dans le prompt, et le LLM peut le répéter à l'élève —
    on garde donc accents et casse d'origine.
    """
    wanted = set(topic_terms(question))
    return " ".join(w for w in _WORD_RE.findall(question) if tokenize(w) and tokenize(w)[0] in wanted)


@dataclass(frozen=True)
class ChapitreBinding:
    """Chapitre retenu pour le cours, et degré de confiance de cette liaison."""

    #: Chapitre retenu, ou ``None`` si aucun candidat ne correspond à la demande.
    chapitre: str | None
    #: Vrai si le titre du chapitre recoupe réellement les termes de la question.
    confirmed: bool
    #: Chapitres présents dans les extraits — proposés à l'élève quand la
    #: liaison échoue, pour qu'il redirige lui-même vers ce qui existe.
    alternatives: tuple[str, ...] = ()


def resolve_chapitre(question: str, candidates: Iterable[str | None]) -> ChapitreBinding:
    """Lie un chapitre à la demande de l'élève, ou déclare l'échec.

    Le seul signal fiable mesuré sur le corpus réel est le **recouvrement entre
    les termes du sujet et le titre du chapitre** : il vaut 1.0 pour « explique-moi
    les nombres complexes » → « Les Nombres Complexes » et 0.0 pour tout chapitre
    hors sujet. Les scores de récupération, eux, ne discriminent rien (la fusion
    RRF est fondée sur les rangs : le meilleur extrait score ~0.83 même pour une
    question sans aucun rapport avec le corpus).

    Quand aucun titre ne recoupe la demande, on renvoie ``chapitre=None`` plutôt
    que de retomber sur le meilleur extrait : c'est précisément cette substitution
    silencieuse qui faisait enseigner « Suites Numériques » à un élève ayant
    demandé les nombres complexes. Le prompt prend alors le relais en demandant
    au LLM de vérifier la couverture et d'être honnête (cf. ``prompt.py``).
    """
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)

    terms = {_stem(t) for t in topic_terms(question)}
    if terms:
        for candidate in unique:
            if terms & {_stem(t) for t in tokenize(candidate)}:
                return ChapitreBinding(candidate, True, tuple(unique))

    return ChapitreBinding(None, False, tuple(unique))


@dataclass
class CoursePosition:
    """Où en est l'élève dans le cours d'un chapitre."""

    chapitre: str | None
    section_index: int
    reason: str
    #: Faux quand le chapitre n'a pas pu être lié à la demande de l'élève : le
    #: prompt bascule alors en posture prudente (vérifier, puis dire honnêtement).
    chapitre_confirmed: bool = True
    #: Chapitres réellement disponibles dans les extraits, à proposer en repli.
    alternatives: tuple[str, ...] = ()
    #: Sujet demandé par l'élève, rappelé au LLM quand la liaison a échoué.
    topic: str = ""

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
    chapitre_fallback: str | None = None,
    binding: ChapitreBinding | None = None,
) -> CoursePosition:
    """Calcule la position dans le cours pour le tour courant.

    * ``START`` ou absence de cours antérieur → nouveau cours (section 0),
      chapitre issu de ``binding`` (liaison à la demande de l'élève) ou, à
      défaut, de ``chapitre_fallback`` (contexte curriculaire explicite).
    * ``NEXT`` / ``PREV`` → déplacement borné dans le plan du cours en cours.
    * ``GOTO`` → saut à la section nommée (à défaut, on ne bouge pas).
    * poursuite sans marqueur (``None``) → on reste sur la section courante
      (l'élève pose une sous-question sur la section en cours).

    La liaison du chapitre n'est (re)calculée qu'au **démarrage** : une fois le
    cours engagé, le chapitre voyage dans ``previous`` et une relance de
    navigation (« continue ») ne doit jamais le redéfinir — sinon le cours
    dériverait de chapitre en cours de route.
    """
    prev_index = (previous or {}).get("section_index", FIRST_INDEX)
    prev_chapitre = (previous or {}).get("chapitre")

    if navigation == Navigation.START or not previous:
        binding = binding or ChapitreBinding(chapitre_fallback, chapitre_fallback is not None)
        return CoursePosition(
            binding.chapitre or chapitre_fallback or prev_chapitre,
            FIRST_INDEX,
            "début du cours",
            chapitre_confirmed=binding.confirmed or bool(chapitre_fallback),
            alternatives=binding.alternatives,
            topic=topic_label(question),
        )

    def carry_on(index: int, reason: str) -> CoursePosition:
        """Poursuite d'un cours engagé : le chapitre est celui déjà retenu.

        Un cours démarré sans chapitre identifié le reste tant que l'élève n'a pas
        reformulé sa demande — la posture prudente du prompt doit donc persister
        d'un tour à l'autre, pas seulement au premier.
        """
        return CoursePosition(
            prev_chapitre,
            index,
            reason,
            chapitre_confirmed=prev_chapitre is not None,
            topic=topic_label(question),
        )

    if navigation == Navigation.NEXT:
        idx = clamp_index(prev_index + 1)
        return carry_on(
            idx, "section suivante" if idx != prev_index else "déjà à la dernière section"
        )

    if navigation == Navigation.PREV:
        idx = clamp_index(prev_index - 1)
        return carry_on(
            idx, "section précédente" if idx != prev_index else "déjà à la première section"
        )

    if navigation == Navigation.GOTO:
        target = resolve_goto(question)
        if target is not None:
            return carry_on(target, f"saut vers « {section_at(target).title} »")
        return carry_on(prev_index, "saut non résolu, section inchangée")

    return carry_on(clamp_index(prev_index), "poursuite sur la section courante")
