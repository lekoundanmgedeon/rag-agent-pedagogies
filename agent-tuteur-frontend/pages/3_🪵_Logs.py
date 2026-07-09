"""Logs — vue d'ensemble du workflow de l'application (tous élèves confondus).

Deux sections : l'orchestration agent (question → réponse, nœud par nœud,
tous les tours de chat récents du tenant) et l'ingestion de documents (étape
par étape, tous les uploads récents). Complète les vues par-conversation/par-
document déjà présentes dans le Chat et l'Upload.
"""

from __future__ import annotations

import streamlit as st

from services import api_client
from services.session import render_identity_sidebar
from services.trace_view import render_node_trace

st.set_page_config(page_title="Logs — Agent Tuteur Sénégal", page_icon="🪵", layout="wide")
render_identity_sidebar()

st.title("🪵 Logs — vue d'ensemble du workflow")
st.caption(
    "Reconstitue le fil complet de chaque tour de chat (orchestration agent) et "
    "de chaque ingestion de document, tous élèves confondus, pour ce tenant."
)

tab_chat, tab_docs = st.tabs(["💬 Orchestration agent", "📤 Ingestion de documents"])

with tab_chat:
    limit = st.slider("Nombre de tours récents à afficher", min_value=5, max_value=200, value=30, step=5)
    if st.button("🔄 Actualiser", key="refresh_chat_logs"):
        st.rerun()

    try:
        entries = api_client.get_chat_logs(st.session_state["tenant_id"], limit=limit)
    except api_client.ApiError as exc:
        st.error(f"Impossible de charger les logs de chat : {exc}")
        entries = []

    if not entries:
        st.info("Aucun tour de chat enregistré pour ce tenant.")

    for entry in entries:
        trace = entry.get("trace") or {}
        question = trace.get("question", "(question indisponible)")
        hint_label = trace.get("hint_label", "?")
        student_id = entry.get("student_id", "?")
        created_at = entry.get("created_at", "")
        with st.expander(f"🧑‍🎓 {student_id} — « {question} » — indice : {hint_label} — {created_at}"):
            st.caption(f"message_id : `{entry.get('message_id')}` · conversation_id : `{entry.get('conversation_id')}`")
            if trace.get("tool_used"):
                st.caption(f"🧮 Outil utilisé : {trace['tool_used']}")
            st.caption(f"Frustration détectée : {trace.get('frustration_score', 0)}")
            if trace.get("sources"):
                st.write("**Sources RAG :**")
                for s in trace["sources"]:
                    st.write(f"- [{s['score']:.4f}] {s['label']} ({s['type_chunk']})")
            st.divider()
            st.write("**Orchestration :**")
            render_node_trace(
                trace.get("node_trace", []), trace.get("generation"), trace.get("trace_id")
            )

with tab_docs:
    if st.button("🔄 Actualiser", key="refresh_doc_logs"):
        st.rerun()

    try:
        docs = api_client.list_documents(st.session_state["tenant_id"])
    except api_client.ApiError as exc:
        st.error(f"Impossible de charger les documents : {exc}")
        docs = []

    if not docs:
        st.info("Aucun document pour ce tenant.")

    status_icons = {"pending": "🟡", "indexed": "🟢", "failed": "🔴", "orphaned": "⚠️"}
    for doc in docs:
        icon = status_icons.get(doc["status"], "⚪")
        with st.expander(f"{icon} {doc['filename']} — {doc['status']} — {doc.get('created_at', '')}"):
            if doc.get("error"):
                st.error(doc["error"])
            log_steps = doc.get("log") or []
            if log_steps:
                for step in log_steps:
                    name = step.get("step", "?")
                    duration = step.get("duration_ms", 0)
                    detail = {k: v for k, v in step.items() if k not in ("step", "duration_ms")}
                    line = f"- `{name}` — {duration:.1f} ms"
                    if detail:
                        line += " (" + ", ".join(f"{k}={v}" for k, v in detail.items()) + ")"
                    st.markdown(line)
                total = sum(s.get("duration_ms", 0) for s in log_steps)
                st.caption(f"⏱️ Durée totale : {total:.1f} ms")
            else:
                st.caption("Aucune étape enregistrée (ingestion pas encore terminée ou document ancien).")
