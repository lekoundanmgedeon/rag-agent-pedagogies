"""Détection de frustration / blocage — **état de session éphémère**.

Cet état (questions récentes) n'est *jamais* persisté dans la mémoire élève :
seul le résultat notable (compétence, niveau d'indice atteint) l'est, plus tard,
au nœud de composition. Le score combine deux signaux : la répétition de la même
question et des marqueurs de ton.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from agent_tuteur.textutil import jaccard

# Seuil de similarité au-delà duquel deux questions sont « la même ».
REPETITION_THRESHOLD = 0.8
# Nombre de questions récentes comparées.
WINDOW = 5

_MARKERS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"je\s+(?:ne\s+)?comprends?\s+pas",
        r"j['e]\s*(?:y\s+)?arrive\s+pas",
        r"donne(?:[\s-]+moi)?\s+(?:la|ta)\s+r[ée]ponse",
        r"je\s+bloque",
        r"c['e]est\s+trop\s+dur",
        r"j['e]\s*abandonne",
        r"je\s+(?:ne\s+)?sais\s+pas",
        r"\bchais\s+pas\b",
        r"aide[\s-]+moi",
    )
]


@dataclass
class SessionState:
    """Contexte conversationnel volatile d'un élève (non persisté)."""

    student_id: str = "anonymous"
    tenant_id: str = "default"
    recent_questions: list[str] = field(default_factory=list)
    #: Série **déclarée par l'élève** au cours de la session, forme canonique.
    #: ``None`` tant qu'il n'a rien dit : l'absence est une information, et la
    #: combler par une valeur par défaut est exactement le bug du cas QA #8.
    #: Écrite par le nœud ``profil_eleve``, elle prime sur la série du profil
    #: pour tout le reste de la session (règle non-négociable n°5).
    serie: str | None = None

    def add(self, question: str) -> None:
        self.recent_questions.append(question)
        # Ne garde qu'une fenêtre glissante.
        if len(self.recent_questions) > WINDOW * 2:
            self.recent_questions = self.recent_questions[-WINDOW * 2 :]


#: Blocage que l'élève **déclare** lui-même : il signale que l'explication a
#: déjà été donnée, sans reposer la même question. ``count_repetitions`` ne peut
#: pas le voir — il compare la question courante aux précédentes, or « Ça fait
#: 3 fois que tu m'expliques » ne ressemble à aucune d'elles. C'est pourtant le
#: signal le plus fiable dont on dispose : l'élève l'énonce (cas QA #20).
_BLOCAGE_DECLARE = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"[çc]a\s+fait\s+\w+\s+fois",
        r"\b(?:pour|c['e]est)\s+la\s+\w+\s*(?:i[èe]me|e)\s+fois",
        r"tu\s+(?:m['e]\s*)?(?:as\s+)?d[ée]j[àa]\s+(?:dit|expliqu|r[ée]pondu)",
        r"tu\s+(?:me\s+)?r[ée]p[èe]tes?\s+(?:toujours\s+)?la\s+m[êe]me",
        r"(?:tu\s+dis|c['e]est)\s+(?:toujours\s+)?la\s+m[êe]me\s+chose",
        r"je\s+(?:ne\s+)?comprends?\s+toujours\s+pas",
        r"encore\s+une\s+fois",
    )
]


@dataclass
class FrustrationSignal:
    score: float
    repetitions: int
    markers: int
    #: L'élève signale explicitement qu'on lui a déjà expliqué. Distinct de
    #: ``repetitions``, qui est *observé* : garder les deux séparés permet de
    #: dire dans la trace lequel des deux a déclenché le changement d'approche.
    blocage_declare: bool = False


def count_repetitions(question: str, recent: list[str]) -> int:
    """Nombre de questions récentes très similaires à la question courante."""
    window = recent[-WINDOW:]
    return sum(1 for prev in window if jaccard(question, prev) >= REPETITION_THRESHOLD)


def count_markers(question: str) -> int:
    return sum(1 for pattern in _MARKERS if pattern.search(question))


def detecte_un_blocage_declare(question: str) -> bool:
    """Vrai si l'élève dit lui-même que l'explication a déjà été donnée."""
    return any(pattern.search(question) for pattern in _BLOCAGE_DECLARE)


def detect_frustration(question: str, session: SessionState) -> FrustrationSignal:
    """Score de frustration : ``min(1, 0.3*rep + 0.4*marqueurs + 0.3*blocage)``.

    Le terme de blocage déclaré pèse autant qu'une répétition observée, et pour
    la même raison : dans les deux cas l'élève a déjà reçu l'explication. Sans
    lui, « Ça fait 3 fois que tu m'expliques, je comprends pas » plafonnait à
    0,4 — juste sous le seuil d'escalade de 0,5 — et l'agent repartait sur un
    « Rappel de notion », c'est-à-dire le même registre une fois de plus.
    """
    repetitions = count_repetitions(question, session.recent_questions)
    markers = count_markers(question)
    blocage = detecte_un_blocage_declare(question)
    score = min(1.0, 0.3 * repetitions + 0.4 * markers + 0.3 * blocage)
    return FrustrationSignal(
        score=round(score, 4),
        repetitions=repetitions,
        markers=markers,
        blocage_declare=blocage,
    )
