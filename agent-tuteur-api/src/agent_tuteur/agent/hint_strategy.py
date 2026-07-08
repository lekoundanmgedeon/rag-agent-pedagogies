"""Stratégie d'indice graduée 0→4 (posture socratique).

Politique de transition (seuils) :
* niveau de base **1** ; **0** si la question est très courte/vague (< 4 tokens) ;
* **+1** si répétitions ≥ 2 ; **+1** si frustration ≥ 0.5 (cumulables) ;
* demande explicite de correction → **saut direct au niveau 4** ;
* niveau borné à ``[0, 4]``.

Le module ne *génère* rien : il décide du niveau et fournit l'instruction
pédagogique correspondante, injectée ensuite dans le prompt du LLM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_tuteur.textutil import tokenize

MIN_LEVEL, MAX_LEVEL = 0, 4
BASE_LEVEL = 1
SHORT_QUESTION_TOKENS = 4
REPETITION_ESCALATION = 2
FRUSTRATION_ESCALATION = 0.5

HINT_LABELS: dict[int, str] = {
    0: "Reformulation",
    1: "Rappel de notion",
    2: "Indice ciblé",
    3: "Solution guidée",
    4: "Solution directe",
}

HINT_INSTRUCTIONS: dict[int, str] = {
    0: (
        "Reformule la question de l'élève avec tes mots pour vérifier sa "
        "compréhension. N'apporte AUCUNE information nouvelle et ne résous rien."
    ),
    1: (
        "Rappelle la règle, la définition ou le théorème utile, SANS l'appliquer "
        "au cas de l'élève. Invite-le à faire le lien lui-même."
    ),
    2: (
        "Donne un indice ciblé qui pointe la PROCHAINE étape à effectuer, sans la "
        "réaliser à sa place. Pose une question qui l'oriente."
    ),
    3: (
        "Décompose la résolution pas à pas, en validant chaque étape, mais laisse "
        "l'élève effectuer les calculs intermédiaires. Ne donne pas le résultat final d'emblée."
    ),
    4: (
        "Donne la solution complète et directe, clairement rédigée et justifiée. "
        "C'est un dernier recours : reste pédagogique."
    ),
}

# Demande explicite de correction -> saut direct au niveau 4.
_EXPLICIT_CORRECTION = re.compile(
    r"donne(?:[\s-]+moi)?\s+(?:la|ta)\s+(?:r[ée]ponse|solution|correction)"
    r"|\bcorrige\b|\bla\s+correction\b|solution\s+compl[èe]te"
    r"|r[ée]ponds?\s+directement|montre[\s-]+moi\s+la\s+solution",
    re.IGNORECASE,
)


@dataclass
class HintDecision:
    level: int
    label: str
    instruction: str
    reason: str


def wants_direct_correction(question: str) -> bool:
    return bool(_EXPLICIT_CORRECTION.search(question))


def diagnose_hint_level(
    question: str,
    frustration_score: float = 0.0,
    repetitions: int = 0,
) -> HintDecision:
    """Décide du niveau d'indice selon la politique de transition."""
    if wants_direct_correction(question):
        return HintDecision(
            level=4,
            label=HINT_LABELS[4],
            instruction=HINT_INSTRUCTIONS[4],
            reason="demande explicite de correction",
        )

    reasons: list[str] = []
    level = BASE_LEVEL
    if len(tokenize(question)) < SHORT_QUESTION_TOKENS:
        level = 0
        reasons.append("question courte/vague")
    if repetitions >= REPETITION_ESCALATION:
        level += 1
        reasons.append(f"répétitions={repetitions}")
    if frustration_score >= FRUSTRATION_ESCALATION:
        level += 1
        reasons.append(f"frustration={frustration_score}")

    level = max(MIN_LEVEL, min(MAX_LEVEL, level))
    if not reasons:
        reasons.append("niveau de base")
    return HintDecision(
        level=level,
        label=HINT_LABELS[level],
        instruction=HINT_INSTRUCTIONS[level],
        reason="; ".join(reasons),
    )
