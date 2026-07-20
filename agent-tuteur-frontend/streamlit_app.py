"""Agent Tuteur Sénégal — Chat (page d'accueil Streamlit).

Client pur de l'API : aucune logique pédagogique ici. Chaque question est
envoyée à ``/api/chat`` et la réponse est affichée au fur et à mesure du
streaming SSE, avec le niveau d'indice, les sources RAG et le détail complet
de l'orchestration agent (nœud par nœud, jusqu'à la génération) en méta-information.
"""

from __future__ import annotations

import streamlit as st

from services import api_client
from services.formatting import normalize_latex_delimiters
from services.session import curriculum_context, render_conversation_sidebar, render_identity_sidebar
from services.trace_view import render_node_trace

st.set_page_config(page_title="Agent Tuteur Sénégal — Chat", page_icon="🎓", layout="wide")


def _status_label(trace: dict) -> str:
    """Bandeau de statut du tour : progression du cours, ou niveau d'indice.

    En mode cours, ``hint_level`` vaut ``None`` (pas d'indice socratique) et un
    bloc ``course`` porte la position dans le plan — on affiche « Cours — Section
    n/N : Titre » plutôt qu'un « Niveau d'indice : None » trompeur.
    """
    course = trace.get("course")
    if course:
        idx = course.get("section_index", 0)
        total = len(course.get("plan", [])) or 1
        title = course.get("section_title", "")
        chapitre = course.get("chapitre")
        head = f"📚 Cours — Section {idx + 1}/{total} : {title}"
        return f"{head} — {chapitre}" if chapitre else head
    return f"Niveau d'indice : {trace.get('hint_level')} ({trace.get('hint_label')})"

render_identity_sidebar()
render_conversation_sidebar()

with st.sidebar:
    st.divider()
    try:
        h = api_client.health()
        icon = "🟢" if h["status"] == "ok" else "🟠"
        st.caption(f"{icon} API {h['status']} — LLM: {' → '.join(h['llm'])}")
        if h.get("documents_orphaned"):
            st.caption(
                f"⚠️ {h['documents_orphaned']} document(s) orphelin(s) détecté(s) "
                "— voir la page Upload pour les ré-uploader."
            )
    except Exception as exc:  # noqa: BLE001 — affichage best-effort du statut.
        st.caption(f"🔴 API injoignable ({exc})")

st.title("🎓 Agent Tuteur Sénégal")
st.caption(
    "Pose une question sur le programme scolaire. Le tuteur guide par indices "
    "progressifs plutôt que de donner la réponse directement."
)

st.session_state.setdefault("messages", [])

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        content = msg["content"]
        st.markdown(normalize_latex_delimiters(content) if msg["role"] == "assistant" else content)
        if msg["role"] == "assistant" and msg.get("trace"):
            trace = msg["trace"]
            with st.expander(_status_label(trace)):
                if trace.get("tool_used"):
                    st.caption(f"🧮 Outil utilisé : {trace['tool_used']}")
                st.caption(f"Frustration détectée : {trace['frustration_score']}")
                st.write("**Sources RAG :**")
                for s in trace.get("sources", []):
                    st.write(f"- [{s['score']:.4f}] {s['label']} ({s['type_chunk']})")
                st.divider()
                st.write("**Orchestration (question → réponse) :**")
                render_node_trace(
                    trace.get("node_trace", []), msg.get("generation"), trace.get("trace_id")
                )
            if msg.get("message_id"):
                col1, col2 = st.columns([1, 12])
                with col1:
                    if st.button("👍", key=f"up_{msg['message_id']}"):
                        api_client.submit_feedback(msg["message_id"], st.session_state["tenant_id"], 1)
                        st.toast("Merci pour ton retour !")
                with col2:
                    if st.button("👎", key=f"down_{msg['message_id']}"):
                        api_client.submit_feedback(msg["message_id"], st.session_state["tenant_id"], -1)
                        st.toast("Merci, c'est noté.")

question = st.chat_input("Ta question...")
if question:
    st.session_state["messages"].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        meta_box = st.empty()
        text_box = st.empty()
        answer_parts: list[str] = []
        trace: dict = {}
        message_id: str | None = None
        conversation_id: str | None = None
        generation: dict | None = None

        try:
            for event in api_client.chat_stream(
                question,
                st.session_state["student_id"],
                st.session_state["tenant_id"],
                curriculum_context(),
                st.session_state.get("conversation_id"),
            ):
                if "meta" in event:
                    trace = event["meta"]
                    meta_box.caption(_status_label(trace))
                elif "token" in event:
                    answer_parts.append(event["token"])
                    text_box.markdown(normalize_latex_delimiters("".join(answer_parts)))
                elif "done" in event:
                    message_id = event["done"]["message_id"]
                    conversation_id = event["done"]["conversation_id"]
                    generation = event["done"].get("generation")
                elif "error" in event:
                    st.error(event["error"])
        except api_client.ApiError as exc:
            if exc.status_code == 400:
                st.error("Question rejetée (tentative de détournement d'instructions détectée).")
            else:
                st.error(f"Erreur API : {exc}")
            answer_parts = []

        if answer_parts:
            st.session_state["conversation_id"] = conversation_id
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": "".join(answer_parts),
                    "trace": trace,
                    "message_id": message_id,
                    "generation": generation,
                }
            )
            st.rerun()
