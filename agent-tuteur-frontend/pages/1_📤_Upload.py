"""Upload de documents curriculaires + suivi de l'indexation."""

from __future__ import annotations

import streamlit as st

from services import api_client
from services.session import render_identity_sidebar

st.set_page_config(page_title="Upload — Agent Tuteur Sénégal", page_icon="📤", layout="wide")
render_identity_sidebar()

st.title("📤 Upload de documents")
st.caption("Formats supportés : PDF, DOCX, TXT, MD. L'ingestion est asynchrone (file ARQ).")

with st.form("upload_form", clear_on_submit=True):
    uploaded = st.file_uploader(
        "Fichiers à indexer", accept_multiple_files=True, type=["pdf", "docx", "txt", "md", "markdown"]
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        classe = st.text_input("Classe (optionnel)")
        serie = st.text_input("Série (optionnel)")
    with col2:
        discipline = st.text_input("Discipline (optionnel)")
        chapitre = st.text_input("Chapitre (optionnel)")
    with col3:
        competence = st.text_input("Compétence (optionnel)")
        examen_associe = st.text_input("Examen associé (optionnel)")
    niveau = st.selectbox("Niveau", ["préscolaire", "élémentaire", "moyen", "secondaire", "EBJA"], index=3)
    submitted = st.form_submit_button("Uploader")

if submitted:
    if not uploaded:
        st.warning("Sélectionne au moins un fichier.")
    else:
        files = [(f.name, f.getvalue()) for f in uploaded]
        metadata = {
            "niveau": niveau,
            "classe": classe,
            "serie": serie,
            "discipline": discipline,
            "chapitre": chapitre,
            "competence": competence,
            "examen_associe": examen_associe,
        }
        try:
            results = api_client.upload_documents(files, st.session_state["tenant_id"], metadata)
            st.success(f"{len(results)} fichier(s) envoyé(s), indexation en cours.")
        except api_client.ApiError as exc:
            st.error(f"Échec de l'upload : {exc}")

st.divider()
st.subheader("Documents du tenant")

if st.button("🔄 Actualiser"):
    st.rerun()

try:
    docs = api_client.list_documents(st.session_state["tenant_id"])
except api_client.ApiError as exc:
    st.error(f"Impossible de lister les documents : {exc}")
    docs = []

status_icons = {"pending": "🟡", "indexed": "🟢", "failed": "🔴"}

for doc in docs:
    icon = status_icons.get(doc["status"], "⚪")
    with st.expander(f"{icon} {doc['filename']} — {doc['status']}"):
        st.json(doc.get("metadata") or {})
        if doc.get("error"):
            st.error(doc["error"])
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Supprimer", key=f"del_{doc['id']}"):
                api_client.delete_document(doc["id"], st.session_state["tenant_id"])
                st.rerun()
        with col2:
            new_file = st.file_uploader(
                "Remplacer et ré-indexer", key=f"reindex_{doc['id']}", type=["pdf", "docx", "txt", "md"]
            )
            if new_file is not None and st.button("♻️ Ré-indexer", key=f"reindex_btn_{doc['id']}"):
                api_client.reindex_document(
                    doc["id"], st.session_state["tenant_id"], new_file.name, new_file.getvalue()
                )
                st.success("Ré-indexation lancée.")
                st.rerun()

if not docs:
    st.info("Aucun document pour ce tenant.")
