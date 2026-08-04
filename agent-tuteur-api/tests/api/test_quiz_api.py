"""Routes du domaine pédagogique : quiz, évaluation, maîtrise.

Le point le plus important vérifié ici : **la bonne réponse ne descend jamais
dans le navigateur**. Elle voyage scellée dans un jeton signé, illisible et
non modifiable par le client.
"""

import json
import uuid

import pytest

from agent_tuteur.api.security import create_quiz_token
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import StudentLinkRepository, UserRepository

QUIZ_JSON = json.dumps(
    {
        "question": "Quelle est la dérivée de $x^2$ ?",
        "choices": [
            {"id": "A", "text": "$2x$"},
            {"id": "B", "text": "$x$"},
            {"id": "C", "text": "$x^3$"},
            {"id": "D", "text": "$2$"},
        ],
        "correct_answer": "A",
        "explanation": "La dérivée de $x^2$ vaut $2x$.",
    }
)


@pytest.fixture
def quiz_llm(api_client):
    """Force l'agent de l'application à produire un quiz JSON valide."""

    class _LLM:
        name = "mock-quiz"
        chain = ["mock-quiz"]
        last_used = "mock-quiz"

        def available(self):
            return True

        async def generate(self, prompt, *, system=None):
            return QUIZ_JSON

        async def generate_stream(self, prompt, *, system=None):
            yield QUIZ_JSON

    api_client.app.state.agent._llm = _LLM()
    return api_client


# --- Aucune de ces routes n'est ouverte ---------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/api/quiz"),
        ("POST", "/api/quiz/answer"),
        ("GET", "/api/evaluation/eleve1"),
        ("GET", "/api/mastery/eleve1"),
    ],
)
async def test_les_routes_pedagogiques_exigent_un_jeton(api_client, method, path):
    reponse = await api_client.request(method, path, json={})
    assert reponse.status_code == 401, f"{method} {path} accessible sans authentification"


# --- Génération d'un quiz -----------------------------------------------------


async def test_un_quiz_est_genere(quiz_llm, student_headers):
    reponse = await quiz_llm.post(
        "/api/quiz", json={"competence": "Dérivation"}, headers=student_headers
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["available"] is True
    assert corps["competence"] == "Dérivation"
    assert len(corps["choices"]) == 4


async def test_la_bonne_reponse_ne_descend_jamais_au_client(quiz_llm, student_headers):
    """Sans cela, l'élève lirait la réponse dans les outils de développement."""
    reponse = await quiz_llm.post(
        "/api/quiz", json={"competence": "Dérivation"}, headers=student_headers
    )
    corps = reponse.json()

    assert "correct_answer" not in corps
    assert "explanation" not in corps
    # Le jeton est opaque : la réponse « A » n'y est pas lisible en clair.
    assert corps["quiz_token"]
    assert "correct_answer" not in corps["quiz_token"]


async def test_la_competence_est_deduite_du_cadre_curriculaire(quiz_llm, student_headers):
    reponse = await quiz_llm.post(
        "/api/quiz",
        json={"curriculum_context": {"chapitre": "Probabilités", "serie": "S1"}},
        headers=student_headers,
    )
    assert reponse.json()["competence"] == "Probabilités"


async def test_sans_aucune_indication_le_quiz_est_refuse(quiz_llm, student_headers):
    """On préfère refuser qu'interroger l'élève au hasard."""
    reponse = await quiz_llm.post("/api/quiz", json={}, headers=student_headers)
    assert reponse.status_code == 422


async def test_un_modele_defaillant_ne_produit_pas_de_quiz_factice(api_client, student_headers):
    """Le mock par défaut ne renvoie pas de JSON : le quiz doit être annoncé absent."""
    reponse = await api_client.post(
        "/api/quiz", json={"competence": "Dérivation"}, headers=student_headers
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["available"] is False
    assert corps["choices"] == []
    assert "n'a pas pu être généré" in corps["instructions"]


# --- Correction ---------------------------------------------------------------


def _jeton_quiz() -> str:
    return create_quiz_token(
        competence="Dérivation", correct_answer="A", explanation="Car $2x$."
    )


async def test_une_bonne_reponse_est_corrigee_et_enregistree(api_client, student_headers):
    reponse = await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": _jeton_quiz(), "answer": "A"},
        headers=student_headers,
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["is_correct"] is True
    assert corps["score"] == 1.0
    assert corps["mastery"]["competence"] == "Dérivation"
    assert corps["mastery"]["mastery_score"] == 1.0
    assert corps["mastery"]["statut"] == "maitrise"


async def test_une_mauvaise_reponse_revele_la_correction(api_client, student_headers):
    reponse = await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": _jeton_quiz(), "answer": "C"},
        headers=student_headers,
    )
    corps = reponse.json()
    assert corps["is_correct"] is False
    assert corps["correct_answer"] == "A"
    assert corps["explanation"] == "Car $2x$."


async def test_un_jeton_de_quiz_falsifie_est_rejete(api_client, student_headers):
    """Un élève qui bricole le jeton pour se déclarer bon ne passe pas."""
    reponse = await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": "jeton.bricole.parlelevе", "answer": "A"},
        headers=student_headers,
    )
    assert reponse.status_code == 400


async def test_le_premier_resultat_debloque_un_badge(api_client, student_headers):
    reponse = await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": _jeton_quiz(), "answer": "A"},
        headers=student_headers,
    )
    codes = [b["code"] for b in reponse.json()["badges"]]
    assert "premier_pas" in codes


async def test_un_badge_n_est_pas_redonne_deux_fois(api_client, student_headers):
    for _ in range(2):
        reponse = await api_client.post(
            "/api/quiz/answer",
            json={"quiz_token": _jeton_quiz(), "answer": "A"},
            headers=student_headers,
        )
    codes = [b["code"] for b in reponse.json()["badges"]]
    assert "premier_pas" not in codes


# --- Historique et maîtrise ---------------------------------------------------


async def test_l_historique_reflete_les_quiz_repondus(api_client, student_headers):
    await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": _jeton_quiz(), "answer": "A"},
        headers=student_headers,
    )
    reponse = await api_client.get("/api/evaluation/eleve1", headers=student_headers)
    assert reponse.status_code == 200
    resultats = reponse.json()["results"]
    assert len(resultats) == 1
    assert resultats[0]["exercise_type"] == "quiz"
    assert resultats[0]["is_correct"] is True


async def test_la_maitrise_est_consultable(api_client, student_headers):
    await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": _jeton_quiz(), "answer": "A"},
        headers=student_headers,
    )
    reponse = await api_client.get("/api/mastery/eleve1", headers=student_headers)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["competences"][0]["competence"] == "Dérivation"
    assert corps["competences"][0]["statut"] == "maitrise"
    # Une réussite parfaite du premier coup en mérite trois : le premier pas, le
    # sans-faute (score de 1,0), et la notion maîtrisée (seuil de 0,8 atteint).
    assert {b["code"] for b in corps["badges"]} == {
        "premier_pas",
        "sans_faute",
        "notion_maitrisee",
    }


async def test_une_competence_jamais_tentee_n_est_pas_proposee_en_revision(
    api_client, student_headers
):
    reponse = await api_client.get("/api/mastery/eleve1", headers=student_headers)
    assert reponse.json()["weakest"] == []


# --- Contrôle d'accès sur les nouvelles routes --------------------------------


@pytest.mark.parametrize("chemin", ["/api/evaluation/{s}", "/api/mastery/{s}"])
async def test_un_eleve_ne_consulte_pas_un_autre_eleve(api_client, student_headers, chemin):
    reponse = await api_client.get(chemin.format(s="eleve2"), headers=student_headers)
    assert reponse.status_code == 403


@pytest.mark.parametrize("chemin", ["/api/evaluation/{s}", "/api/mastery/{s}"])
async def test_un_parent_non_rattache_est_refuse(
    api_client, tenant_id, make_headers, chemin
):
    async with session_scope(None) as session:
        user = await UserRepository(session).create(
            tenant_id=tenant_id,
            email=f"parent-{uuid.uuid4().hex[:8]}@ecole.sn",
            password_hash="x",
            role="parent",
        )
    headers = make_headers(tenant_id=tenant_id, role="parent", user_id=user.id)
    reponse = await api_client.get(chemin.format(s="eleve-inconnu"), headers=headers)
    assert reponse.status_code == 403


async def test_un_parent_rattache_consulte_la_maitrise_de_son_enfant(
    api_client, tenant_id, make_headers
):
    async with session_scope(None) as session:
        user = await UserRepository(session).create(
            tenant_id=tenant_id,
            email=f"parent-{uuid.uuid4().hex[:8]}@ecole.sn",
            password_hash="x",
            role="parent",
        )
    async with session_scope(tenant_id) as session:
        await StudentLinkRepository(session).link(
            user_id=user.id, student_id="mon-enfant", tenant_id=tenant_id
        )

    headers = make_headers(tenant_id=tenant_id, role="parent", user_id=user.id)
    reponse = await api_client.get("/api/mastery/mon-enfant", headers=headers)
    assert reponse.status_code == 200


async def test_un_eleve_ne_peut_pas_enregistrer_un_resultat_pour_un_autre(
    api_client, student_headers
):
    """L'identifiant fourni dans le corps de la requête ne vaut pas autorisation."""
    reponse = await api_client.post(
        "/api/quiz/answer",
        json={"quiz_token": _jeton_quiz(), "answer": "A", "student_id": "eleve2"},
        headers=student_headers,
    )
    assert reponse.status_code == 403
