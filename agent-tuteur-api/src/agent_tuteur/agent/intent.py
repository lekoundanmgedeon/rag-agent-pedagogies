"""Détection d'intention — aiguille un tour vers le pipeline **exercice** ou **cours**.

Deux comportements coexistent :

* ``EXERCICE`` (défaut) — posture socratique à indices gradués (cf.
  ``hint_strategy.py``) : l'agent *retient* volontairement le contenu.
* ``COURS`` — posture didactique : l'agent *expose* un chapitre, section par
  section (cf. ``course_plan.py``).

La détection est **heuristique regex-first**, dans l'esprit de ``frustration.py``
et ``hint_strategy.py`` : rapide, déterministe, sans appel LLM. Le principe de
sûreté est que **le défaut reste ``EXERCICE``** — en cas d'ambiguïté on ne dérive
jamais vers le mode cours, pour ne pas casser le comportement historique.

La détection tient compte de la **continuité de session** (``in_course``) : une
relance courte de navigation (« continue », « passe aux exercices ») n'a de sens
que si l'élève est déjà dans un cours ; hors cours, elle retombe sur ``EXERCICE``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    EXERCICE = "exercice"
    COURS = "cours"


class Navigation(str, Enum):
    #: Démarrage explicite d'un cours (« explique-moi les nombres complexes »).
    START = "start"
    #: Avancer à la section suivante (« continue »).
    NEXT = "next"
    #: Revenir à la section précédente.
    PREV = "prev"
    #: Sauter à une section nommée (« passe aux exercices »). La cible est
    #: résolue par ``course_plan.resolve_goto`` à partir de la question brute.
    GOTO = "goto"


# --- Déclencheurs de démarrage d'un cours ------------------------------------
# Formulations par lesquelles un élève demande explicitement un enseignement.
_COURSE_START = re.compile(
    r"\b(?:"
    r"fais(?:[\s-]+moi)?\s+un\s+cours"
    r"|donne(?:[\s-]+moi)?\s+un\s+cours"
    r"|un\s+cours\s+sur"
    r"|cours\s+(?:sur|de|complet)"
    r"|explique(?:[\s-]+moi|[\s-]+nous)?\b"
    r"|expliqu[ez]-?(?:moi|nous)"
    r"|pr[ée]sente(?:[\s-]+moi)?\b"
    r"|enseigne(?:[\s-]+moi)?\b"
    r"|apprends(?:[\s-]+moi)?\b"
    r"|je\s+veux\s+(?:apprendre|comprendre|r[ée]viser|[ée]tudier)"
    r"|j['e]\s*aimerais\s+(?:apprendre|comprendre|r[ée]viser)"
    r"|initie(?:[\s-]+moi)?\b"
    r"|c['e]est\s+quoi\b"
    r"|qu['e]est[\s-]?ce\s+que\b"
    r")",
    re.IGNORECASE,
)

# --- Navigation à l'intérieur d'un cours en cours ----------------------------
_NAV_NEXT = re.compile(
    r"\b(?:continue[rz]?|suite|section\s+suivante|au?\s+suivant|"
    r"la\s+suite|poursuis|encha[îi]ne|passe\s+[àa]\s+la\s+suite|ok\s*,?\s*suite)\b",
    re.IGNORECASE,
)
_NAV_PREV = re.compile(
    r"\b(?:pr[ée]c[ée]dent[e]?|section\s+pr[ée]c[ée]dente|reviens|retour[\s-]+en[\s-]+arri[èe]re|"
    r"reviens\s+en\s+arri[èe]re)\b",
    re.IGNORECASE,
)
# Saut vers une section nommée : « passe aux exercices », « montre les exemples »,
# « et les définitions ? ». On matche le verbe/tournure + un mot de section
# reconnu par course_plan (la résolution fine du numéro de section y est faite).
_NAV_GOTO = re.compile(
    r"\b(?:passe[rz]?|va|aller|montre[\s-]?moi|donne[\s-]?moi|voir|"
    r"saute[rz]?|directement|plut[ôo]t)\b.*\b(?:"
    r"exercices?|exemples?|d[ée]finitions?|th[ée]or[èe]mes?|propri[ée]t[ée]s?|"
    r"m[ée]thodes?|erreurs?|astuces?|r[ée]sum[ée]|r[ée]vision|introduction|intro)\b",
    re.IGNORECASE,
)
# Mots de section employés seuls (« les exercices », « des exemples ? ») — utile
# uniquement en mode cours, où la référence est sans ambiguïté.
_SECTION_MENTION = re.compile(
    r"\b(?:exercices?|exemples?|d[ée]finitions?|th[ée]or[èe]mes?|propri[ée]t[ée]s?|"
    r"m[ée]thodes?|astuces?|r[ée]sum[ée]|r[ée]vision)\b",
    re.IGNORECASE,
)

# --- Sortie de secours du mode cours -----------------------------------------
# Un signal d'exercice FORT (demande de résolution/calcul) rompt la « collance »
# du mode cours : sans ça, un élève en plein cours qui tape « calcule … » resterait
# piégé en posture didactique au lieu de repartir sur le pipeline socratique
# (avec routage outil SymPy). Verbes impératifs de résolution uniquement — les
# tournures de difficulté (« je ne trouve pas », « je n'ai pas compris ») ne
# doivent PAS déclencher la sortie et rester dans le cours.
_EXERCISE_BREAKOUT = re.compile(
    r"\b(?:"
    r"calcule[rz]?|r[ée]sous|r[ée]soudre|resous|corrige[rz]?|factorise[rz]?|"
    r"d[ée]veloppe[rz]?|simplifie[rz]?|d[ée]montre[rz]?|d[ée]termine[rz]?|"
    r"montre\s+que|donne(?:[\s-]+moi)?\s+(?:la|ta)\s+(?:r[ée]ponse|solution|correction)"
    r")\b",
    re.IGNORECASE,
)


def is_exercise_breakout(question: str) -> bool:
    """Vrai si la question est une demande de résolution qui doit sortir du cours."""
    return bool(_EXERCISE_BREAKOUT.search(question))


@dataclass
class IntentDecision:
    intent: Intent
    reason: str
    #: Non ``None`` uniquement quand ``intent == COURS``.
    navigation: Navigation | None = None


def _detect_navigation(question: str, *, in_course: bool) -> Navigation | None:
    """Type de navigation cours détecté, ou ``None``.

    ``START`` est reconnu partout (un élève peut ouvrir un cours à tout moment) ;
    ``NEXT``/``PREV``/``GOTO`` ne sont interprétés **que** si l'on est déjà dans
    un cours — sinon un simple « continue » n'a pas de section à faire avancer.
    """
    if _COURSE_START.search(question):
        return Navigation.START
    if not in_course:
        return None
    if _NAV_NEXT.search(question):
        return Navigation.NEXT
    if _NAV_PREV.search(question):
        return Navigation.PREV
    # Saut *explicite* (verbe + section) uniquement ; la simple mention d'un mot
    # de section (« et les exercices ? ») est traitée à part dans classify_intent,
    # APRÈS la sortie de secours, pour ne pas capturer « corrige mon exercice ».
    if _NAV_GOTO.search(question):
        return Navigation.GOTO
    return None


def classify_intent(question: str, *, in_course: bool = False) -> IntentDecision:
    """Décide entre ``EXERCICE`` (défaut sûr) et ``COURS``.

    ``in_course`` indique que le dernier tour de la conversation était déjà en
    mode cours (reconstruit par l'appelant depuis la trace persistée). Dans ce
    cas, une relance sans marqueur explicite reste dans le cours (poursuite du
    fil), sur la section courante.
    """
    nav = _detect_navigation(question, in_course=in_course)

    if nav == Navigation.START:
        return IntentDecision(Intent.COURS, "demande explicite de cours", Navigation.START)

    if in_course:
        # Navigation explicite (suite / saut avec verbe) → on avance dans le cours.
        if nav is not None:
            return IntentDecision(Intent.COURS, f"poursuite du cours ({nav.value})", nav)
        # Une demande de résolution explicite rompt le mode cours — prioritaire sur
        # une simple mention de section (« corrige mon exercice » n'est pas un saut).
        if is_exercise_breakout(question):
            return IntentDecision(Intent.EXERCICE, "sortie du cours (demande de résolution)", None)
        # Mention seule d'une section (« et les définitions ? ») → saut implicite.
        if _SECTION_MENTION.search(question):
            return IntentDecision(Intent.COURS, "poursuite du cours (goto)", Navigation.GOTO)
        return IntentDecision(Intent.COURS, "poursuite du cours", None)

    return IntentDecision(Intent.EXERCICE, "défaut (résolution d'exercice)", None)
