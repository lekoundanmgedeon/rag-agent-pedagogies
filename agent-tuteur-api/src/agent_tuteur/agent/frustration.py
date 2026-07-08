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

    def add(self, question: str) -> None:
        self.recent_questions.append(question)
        # Ne garde qu'une fenêtre glissante.
        if len(self.recent_questions) > WINDOW * 2:
            self.recent_questions = self.recent_questions[-WINDOW * 2 :]


@dataclass
class FrustrationSignal:
    score: float
    repetitions: int
    markers: int


def count_repetitions(question: str, recent: list[str]) -> int:
    """Nombre de questions récentes très similaires à la question courante."""
    window = recent[-WINDOW:]
    return sum(1 for prev in window if jaccard(question, prev) >= REPETITION_THRESHOLD)


def count_markers(question: str) -> int:
    return sum(1 for pattern in _MARKERS if pattern.search(question))


def detect_frustration(question: str, session: SessionState) -> FrustrationSignal:
    """Calcule le signal de frustration : ``min(1, 0.3*rep + 0.4*marqueurs)``."""
    repetitions = count_repetitions(question, session.recent_questions)
    markers = count_markers(question)
    score = min(1.0, 0.3 * repetitions + 0.4 * markers)
    return FrustrationSignal(score=round(score, 4), repetitions=repetitions, markers=markers)
