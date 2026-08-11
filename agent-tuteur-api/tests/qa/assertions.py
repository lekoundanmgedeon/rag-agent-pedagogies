"""Vocabulaire d'assertion partagé par le rejeu QA.

Regrouper les assertions ici a deux effets : les tests se lisent tous de la même
façon, et la définition de « ce qui est attendu » n'existe qu'à un seul endroit
(un seuil, un nom de nœud) plutôt que recopiée dans vingt fichiers.

Aucune assertion ne porte sur une correspondance de texte exacte : le modèle ne
répond jamais deux fois pareil. Les seules assertions textuelles autorisées
portent sur des réponses **court-circuitées**, produites de façon déterministe
par le code et non par le modèle.
"""

from __future__ import annotations

import json

from agent_tuteur.textutil import strip_accents

# Nœud de recherche RAG : son absence du parcours prouve le court-circuit.
NOEUD_RETRIEVAL = "retrieve_context"


def _noeuds(resultat) -> list[str]:
    return [entree["node"] for entree in resultat.node_trace]


def _aplatir(texte: str) -> str:
    """Minuscules, sans accents, apostrophes typographiques ramenées à ``'``."""
    return strip_accents(texte.replace("’", "'")).lower()


def assert_intention(resultat, attendue: str) -> None:
    """L'intention décidée par ``detect_intent``, lue dans le ``node_trace``."""
    entree = next((e for e in resultat.node_trace if e["node"] == "detect_intent"), None)
    assert entree is not None, "le nœud detect_intent n'a pas été traversé"
    assert entree["intent"] == attendue, (
        f"intention attendue {attendue!r}, obtenue {entree['intent']!r}"
    )


def assert_trace_compatible_avec_le_streaming(prepared) -> None:
    """La trace porte les clés que la route SSE lit sans garde.

    ``api/routes/chat.py`` accède directement à ``trace["sources"]``,
    ``["scores"]``, ``["tool_used"]``, ``["frustration_score"]`` et aux
    propriétés ``hint_level``/``hint_label``. Un tour dont la trace serait
    minimale ferait donc tomber l'API réelle en 500 alors que tous les tests
    unitaires passent — c'est ce test qui l'empêche.
    """
    for cle in ("sources", "scores", "tool_used", "frustration_score", "hint_level", "hint_label"):
        assert cle in prepared.trace, f"clé de trace manquante pour le streaming : {cle!r}"
    # ``hint_level`` vaut légitimement None hors branche exercice (cf. mode
    # cours) : ce qui compte est que l'accès ne lève pas et que la charge parte
    # en JSON — c'est exactement ce que fait la route SSE.
    json.dumps(
        {
            "hint_level": prepared.hint_level,
            "hint_label": prepared.hint_label,
            "sources": prepared.trace["sources"],
            "scores": prepared.trace["scores"],
            "tool_used": prepared.trace["tool_used"],
            "frustration_score": prepared.trace["frustration_score"],
            "course": prepared.trace.get("course"),
            "trace_id": prepared.trace_id,
            "node_trace": prepared.node_trace,
        }
    )
