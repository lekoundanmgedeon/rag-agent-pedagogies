"""Garde-fous d'entrée et pédagogiques.

Trois responsabilités distinctes :

1. ``sanitize`` — **anti-injection de prompt**. Détecte les tentatives de
   détournement d'instructions et lève ``PromptInjectionError`` (l'API la
   traduit en HTTP 400, *avant* tout appel LLM).
2. ``moderate`` — **modération** adaptée à un public mineur (signale un contenu
   inapproprié pour déclencher une réponse de déviation bienveillante).
3. ``clamp_hint_level`` — **garde-fou pédagogique** : borne défensive du niveau
   d'indice réellement appliqué.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from agent_tuteur.agent.hint_strategy import MAX_LEVEL, MIN_LEVEL


class PromptInjectionError(ValueError):
    """Levée quand une tentative d'injection de prompt est détectée."""

    def __init__(self, pattern: str) -> None:
        super().__init__("Tentative d'injection de prompt détectée.")
        self.pattern = pattern


_INJECTION_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(?:les\s+|toutes?\s+les\s+)?(?:instructions?|consignes?|r[èe]gles?)",
        r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions?",
        r"oublie\s+(?:tes|les)\s+(?:instructions?|consignes?)",
        r"disregard\s+(?:the\s+)?(?:previous|above|prior)",
        r"tu\s+es\s+(?:maintenant|d[ée]sormais)\b",
        r"you\s+are\s+now\b",
        r"(?:affiche|montre|r[ée]v[èe]le|reveal|print)\s+(?:ton|le|your|the)\s+"
        r"(?:system\s+)?(?:prompt|instructions?|consignes?)",
        r"system\s+prompt",
        r"\bjailbreak\b|\bmode\s+dan\b|\bdan\s+mode\b",
        r"agis\s+comme\s+si\s+tu\s+n['e]avais\s+aucune\s+r[èe]gle",
    )
]


@dataclass
class ModerationResult:
    flagged: bool
    category: str | None = None


# Catégories inappropriées pour un public scolaire mineur (liste conservatrice).
_MODERATION_PATTERNS: dict[str, re.Pattern] = {
    "violence": re.compile(r"\b(?:tuer|fabriquer\s+une\s+bombe|arme\s+[àa]\s+feu|explosif)\b", re.IGNORECASE),
    "contenu_sexuel": re.compile(r"\b(?:pornograph\w*|contenu\s+sexuel\s+explicite)\b", re.IGNORECASE),
    "automutilation": re.compile(r"\b(?:me\s+suicider|automutilation|me\s+faire\s+du\s+mal)\b", re.IGNORECASE),
    "haine": re.compile(r"\b(?:insulte\s+raciste|propos\s+haineux)\b", re.IGNORECASE),
}


def sanitize(text: str) -> str:
    """Valide une entrée élève. Lève ``PromptInjectionError`` si détournement.

    Retourne le texte inchangé (nettoyé des espaces superflus) s'il est sain.
    """
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise PromptInjectionError(pattern.pattern)
    return text.strip()


def moderate(text: str) -> ModerationResult:
    """Signale un contenu inapproprié pour un public mineur."""
    for category, pattern in _MODERATION_PATTERNS.items():
        if pattern.search(text):
            return ModerationResult(flagged=True, category=category)
    return ModerationResult(flagged=False)


def clamp_hint_level(level: int) -> int:
    """Garde-fou pédagogique : borne le niveau d'indice à [0, 4]."""
    return max(MIN_LEVEL, min(MAX_LEVEL, level))
