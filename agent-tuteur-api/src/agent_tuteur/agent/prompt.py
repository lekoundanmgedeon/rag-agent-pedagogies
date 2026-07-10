"""Assemblage du prompt final (persona socratique + contexte RAG + indice).

Ce module produit le couple ``(system, user)`` que le LLM reçoit. Il matérialise
la frontière préparation/génération : une fois ce prompt assemblé (fin des nœuds
a→e), l'API n'a plus qu'à streamer ``generate_stream`` — aucune décision
pédagogique ne reste à prendre côté génération.

Le prompt inclut une ligne machine-lisible « Niveau d'indice : N (Label) » que le
LLM mock (et la traçabilité) peuvent relire.
"""

from __future__ import annotations

from agent_tuteur.agent.hint_strategy import HintDecision
from agent_tuteur.domain.models import ScoredChunk

SYSTEM_PERSONA = (
    "Tu es un tuteur pédagogique bienveillant pour le programme scolaire "
    "sénégalais (de l'élémentaire au Baccalauréat). Ta posture est socratique : "
    "tu guides l'élève vers la réponse par des indices progressifs plutôt que de "
    "la donner directement. Tu t'appuies STRICTEMENT sur les extraits de cours "
    "fournis ; si l'information manque, tu le dis honnêtement. Tu t'exprimes en "
    "français clair, avec des formules en LaTeX. Utilise EXCLUSIVEMENT les "
    "délimiteurs $...$ (inline) et $$...$$ (bloc) ; n'utilise JAMAIS \\(...\\) ni "
    "\\[...\\], qui ne s'affichent pas correctement ici. "
    "Tu ne dépasses jamais le niveau d'indice demandé."
)

_MAX_EXCERPT = 600
#: Nombre de messages (élève + tuteur confondus) réinjectés dans le prompt.
_MAX_HISTORY_MESSAGES = 6

_SPEAKER_LABELS = {"user": "Élève", "assistant": "Tuteur"}


def build_context_block(retrieved: list[ScoredChunk]) -> str:
    """Formate les extraits RAG avec attribution, pour ancrer la réponse."""
    if not retrieved:
        return "(Aucun extrait de cours pertinent trouvé.)"
    lines: list[str] = []
    for i, sc in enumerate(retrieved, start=1):
        excerpt = sc.chunk.text.strip()
        if len(excerpt) > _MAX_EXCERPT:
            excerpt = excerpt[:_MAX_EXCERPT].rstrip() + " […]"
        lines.append(f"[Source {i} — {sc.source_label}]\n{excerpt}")
    return "\n\n".join(lines)


def build_history_block(history: list[dict[str, str]] | None) -> str | None:
    """Formate les derniers tours de la conversation, ou ``None`` s'il n'y en a pas.

    Sans ce rappel, une relance courte de l'élève ("un autre indice ?") arrive
    seule dans le prompt : le LLM ne sait plus de quel énoncé il est question
    et improvise hors-sujet. On réinjecte donc le fil récent pour ancrer la
    réponse dans l'exercice réellement discuté.
    """
    if not history:
        return None
    recent = history[-_MAX_HISTORY_MESSAGES:]
    lines = [
        f"{_SPEAKER_LABELS.get(m['role'], m['role'])} : {m['content'].strip()}" for m in recent
    ]
    return "\n".join(lines)


def assemble_prompt(
    question: str,
    hint: HintDecision,
    retrieved: list[ScoredChunk],
    tool_result: str | None = None,
    curriculum_context: dict | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    """Retourne ``(system_prompt, user_prompt)`` assemblés.

    Le ``user_prompt`` agrège : contexte curriculaire, historique récent,
    extraits RAG, résultat de l'outil de calcul éventuel, la consigne
    d'indice, puis la question élève.
    """
    ctx = curriculum_context or {}
    scope = ", ".join(
        f"{k}={v}" for k in ("niveau", "classe", "serie", "discipline") if (v := ctx.get(k))
    )

    parts: list[str] = []
    if scope:
        parts.append(f"Cadre curriculaire : {scope}.")
    history_block = build_history_block(conversation_history)
    if history_block:
        parts.append(f"Historique récent de la conversation :\n{history_block}")
    parts.append("Extraits de cours disponibles :\n" + build_context_block(retrieved))
    if tool_result:
        parts.append(f"Résultat vérifié par l'outil de calcul : {tool_result}")
    parts.append(
        f"Niveau d'indice : {hint.level} ({hint.label}).\nConsigne : {hint.instruction}"
    )
    parts.append(f"Question de l'élève : {question}")

    return SYSTEM_PERSONA, "\n\n".join(parts)
