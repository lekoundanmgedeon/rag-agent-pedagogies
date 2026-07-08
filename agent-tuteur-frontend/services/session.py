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
