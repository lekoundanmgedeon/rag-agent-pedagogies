"""Rendu partagé de la trace d'orchestration agent — Chat et page Logs.

Affiche le détail nœud-par-nœud (retrieve_context → ... → guardrail) produit
par le graphe LangGraph, plus la génération LLM (streamée séparément côté
cœur métier, cf. ADR 0005) — de la question de l'élève jusqu'à la réponse.
"""

from __future__ import annotations

import streamlit as st

_NODE_ICONS = {
    "detect_intent": "🧭",
    "retrieve_context": "🔍",
    "detect_frustration": "😤",
    "diagnose_hint_level": "🎚️",
    "route_tool": "🧮",
    "guardrail": "🛡️",
    "course_planner": "📚",
    "guardrail_course": "🛡️",
    "compose_response": "💬",
}

_NODE_LABELS = {
    "detect_intent": "Détection d'intention (exercice / cours)",
    "retrieve_context": "Recherche RAG",
    "detect_frustration": "Détection de frustration",
    "diagnose_hint_level": "Diagnostic du niveau d'indice",
    "route_tool": "Routage d'outil",
    "guardrail": "Garde-fou + assemblage du prompt",
    "course_planner": "Planification du cours (section)",
    "guardrail_course": "Garde-fou + assemblage du prompt (cours)",
    "compose_response": "Génération LLM",
}

_HIDDEN_DETAIL_KEYS = {"node", "duration_ms", "trace_id"}


def render_node_trace(
    node_trace: list[dict],
    generation: dict | None = None,
    trace_id: str | None = None,
) -> None:
    """Affiche le fil complet d'un tour d'agent : question → orchestration → réponse."""
    if trace_id:
        st.caption(f"trace_id : `{trace_id}`")

    total_ms = sum(entry.get("duration_ms", 0) for entry in node_trace)
    if generation:
        total_ms += generation.get("duration_ms", 0)

    for entry in node_trace:
        node = entry.get("node", "?")
        icon = _NODE_ICONS.get(node, "▫️")
        label = _NODE_LABELS.get(node, node)
        duration = entry.get("duration_ms", 0)
        detail = {k: v for k, v in entry.items() if k not in _HIDDEN_DETAIL_KEYS}
        st.markdown(f"{icon} **{label}** — {duration:.1f} ms")
        if detail:
            st.caption(", ".join(f"{k} = {v}" for k, v in detail.items()))

    if generation:
        st.markdown(
            f"💬 **Génération LLM** (`{generation.get('llm_provider', '?')}`) — "
            f"{generation.get('duration_ms', 0):.1f} ms, {generation.get('token_count', 0)} tokens"
        )

    st.caption(f"⏱️ Durée totale de l'orchestration : {total_ms:.1f} ms")
