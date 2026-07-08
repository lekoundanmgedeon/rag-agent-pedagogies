"""Progression élève : historique et difficultés récurrentes."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from services import api_client
from services.session import render_identity_sidebar

st.set_page_config(page_title="Progression — Agent Tuteur Sénégal", page_icon="📈", layout="wide")
render_identity_sidebar()

st.title("📈 Progression de l'élève")

student_id = st.text_input("Identifiant élève", st.session_state["student_id"])

if st.button("Charger la progression") or student_id:
    try:
        data = api_client.get_progression(student_id, st.session_state["tenant_id"])
    except api_client.ApiError as exc:
        st.error(f"Erreur : {exc}")
        data = None

    if data:
        st.subheader("Difficultés récurrentes")
        if data["recurrent_difficulties"]:
            for comp in data["recurrent_difficulties"]:
                st.warning(f"⚠️ {comp}")
        else:
            st.info("Aucune difficulté récurrente détectée (niveau d'indice ≥ 3 répété).")

        st.subheader("Historique")
        if data["history"]:
            df = pd.DataFrame(data["history"])
            st.dataframe(
                df[["created_at", "question", "competence", "hint_level"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Aucun historique pour cet élève.")
