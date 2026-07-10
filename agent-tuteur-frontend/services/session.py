"""État de session partagé entre les pages (tenant/élève courants)."""

from __future__ import annotations

import os

import streamlit as st

DEFAULT_TENANT = os.environ.get("DEFAULT_TENANT", "default")


def init_session_defaults() -> None:
    st.session_state.setdefault("tenant_id", DEFAULT_TENANT)
    st.session_state.setdefault("student_id", "eleve_demo")
    st.session_state.setdefault("conversation_id", None)
    st.session_state.setdefault("niveau", "secondaire")
    st.session_state.setdefault("serie", "S1")
    st.session_state.setdefault("discipline", "Mathématiques")


def render_identity_sidebar() -> None:
    """Champs communs (tenant/élève/contexte curriculaire) affichés dans la sidebar."""
    init_session_defaults()
    with st.sidebar:
        st.subheader("Identité")
        st.session_state["tenant_id"] = st.text_input("Tenant (X-Tenant-Id)", st.session_state["tenant_id"])
        st.session_state["student_id"] = st.text_input("Identifiant élève", st.session_state["student_id"])
        st.divider()
        st.subheader("Contexte curriculaire")
        st.session_state["niveau"] = st.selectbox(
            "Niveau",
            ["préscolaire", "élémentaire", "moyen", "secondaire", "EBJA"],
            index=["préscolaire", "élémentaire", "moyen", "secondaire", "EBJA"].index(
                st.session_state["niveau"]
            ),
        )
        st.session_state["serie"] = st.text_input("Série (secondaire, optionnel)", st.session_state["serie"])
        st.session_state["discipline"] = st.text_input("Discipline", st.session_state["discipline"])


def curriculum_context() -> dict[str, str]:
    ctx = {"niveau": st.session_state.get("niveau", "")}
    if st.session_state.get("serie"):
        ctx["serie"] = st.session_state["serie"]
    if st.session_state.get("discipline"):
        ctx["discipline"] = st.session_state["discipline"]
    return {k: v for k, v in ctx.items() if v}


def _history_to_messages(rows: list[dict]) -> list[dict]:
    """Convertit l'historique persisté (``GET .../messages``) au format attendu
    par ``streamlit_app.py`` (même forme que les messages ajoutés en direct
    pendant le streaming) : ``generation`` en clé sœur de ``trace``, extraite
    de la trace persistée où elle est imbriquée (cf. ``routes/chat.py``)."""
    messages: list[dict] = []
    for row in rows:
        if row["role"] == "user":
            messages.append({"role": "user", "content": row["content"]})
        else:
            trace = row.get("trace") or {}
            messages.append(
                {
                    "role": "assistant",
                    "content": row["content"],
                    "trace": trace,
                    "message_id": row["id"],
                    "generation": trace.get("generation"),
                }
            )
    return messages


def render_conversation_sidebar() -> None:
    """Sessions de chat de l'élève courant : reprise, nouvelle session, suppression."""
    from services import api_client

    with st.sidebar:
        st.divider()
        st.subheader("Sessions de chat")
        if st.button("➕ Nouvelle conversation", use_container_width=True):
            st.session_state["conversation_id"] = None
            st.session_state["messages"] = []
            st.rerun()

        try:
            conversations = api_client.list_conversations(
                st.session_state["student_id"], st.session_state["tenant_id"]
            )
        except Exception as exc:  # noqa: BLE001 — affichage best-effort du statut.
            st.caption(f"🔴 Sessions injoignables ({exc})")
            conversations = []

        current_id = st.session_state.get("conversation_id")
        for conv in conversations:
            is_current = conv["id"] == current_id
            label = (conv["title"] or "Sans titre").strip()
            col_select, col_delete = st.columns([5, 1])
            with col_select:
                if st.button(
                    ("📍 " if is_current else "") + label,
                    key=f"conv_select_{conv['id']}",
                    use_container_width=True,
                    disabled=is_current,
                ):
                    rows = api_client.get_conversation_messages(conv["id"], st.session_state["tenant_id"])
                    st.session_state["conversation_id"] = conv["id"]
                    st.session_state["messages"] = _history_to_messages(rows)
                    st.rerun()
            with col_delete:
                if st.button("🗑", key=f"conv_delete_{conv['id']}"):
                    api_client.delete_conversation(conv["id"], st.session_state["tenant_id"])
                    if is_current:
                        st.session_state["conversation_id"] = None
                        st.session_state["messages"] = []
                    st.rerun()
