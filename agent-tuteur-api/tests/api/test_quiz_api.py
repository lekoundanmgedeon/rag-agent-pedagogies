"""Routes du domaine pédagogique : quiz, évaluation, maîtrise.

Deux propriétés tenues ici, et la seconde a changé de nature le 2026-08-28 :

* **la bonne réponse ne descend jamais dans le navigateur** — elle voyage
  scellée dans un jeton signé, illisible et non modifiable par le client ;
* **les questions viennent du corpus, jamais du modèle** (décision D12). Le
  modèle produisait des questions dont la réponse déclarée pouvait être fausse ;
  les sections « Auto-évaluation » des leçons portent des items corrigés par
  l'auteur. Un chapitre qui n'en a pas ne reçoit **aucune** question inventée.
"""

import uuid

import pytest

from agent_tuteur.api.security import create_quiz_token
from agent_tuteur.persistence.db import session_scope
from agent_tuteur.persistence.repositories import StudentLinkRepository, UserRepository

#: Leçon minimale au format pilote, avec la seule section qui intéresse le quiz.
#: Les items vrai/faux y portent leur correction, comme dans les 12 leçons.
LECON_AVEC_EVALUATION = """# Leçon — Dérivation (Terminale S1)

## 1. Métadonnées
- Niveau : secondaire
- Série : S1
- Discipline : Mathématiques
- Chapitre : Dérivation

## 2. Introduction

La dérivée mesure la vitesse de variation d'une fonction.

## 18. Auto-évaluation

### QCM
1. La dérivée de $x^2$ est :
 a) $2x$ b) $x$ c) $x^3$ d) $2$

### Vrai/Faux
1. La dérivée d'une constante est nulle. (Vrai)
2. La dérivée de $x^2$ vaut $x$. (Faux — elle vaut $2x$)
"""


@pytest.fixture
def corpus_avec_evaluation(api_client):
    """Indexe une leçon qui porte une section d'auto-évaluation corrigée.

    On passe par l'``Indexer`` de l'application plutôt que par l'API d'upload :
    ce qui est testé ici est la lecture des questions, pas l'ingestion, déjà
    couverte ailleurs.
    """
    from agent_tuteur.ingestion.pipeline import ingest_and_index

    ingest_and_index(
        "lecon_derivation_s1.md",
        LECON_AVEC_EVALUATION.encode("utf-8"),
        api_client.app.state.indexer,
    )
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


async def test_une_question_du_corpus_est_servie(corpus_avec_evaluation, student_headers):
    reponse = await corpus_avec_evaluation.post(
        "/api/quiz",
        json={"competence": "Dérivation", "quiz_type": "vrai_faux"},
        headers=student_headers,
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["available"] is True
    assert corps["competence"] == "Dérivation"
    assert [c["text"] for c in corps["choices"]] == ["Vrai", "Faux"]
    # L'énoncé est celui de la leçon, au mot près : rien n'a été reformulé.
    assert corps["question"] in {
        "La dérivée d'une constante est nulle.",
        "La dérivée de $x^2$ vaut $x$.",
    }


async def test_la_bonne_reponse_ne_descend_jamais_au_client(
    corpus_avec_evaluation, student_headers
):
    """Sans cela, l'élève lirait la réponse dans les outils de développement."""
    reponse = await corpus_avec_evaluation.post(
        "/api/quiz",
        json={"competence": "Dérivation", "quiz_type": "vrai_faux"},
        headers=student_headers,
    )
    corps = reponse.json()

    assert "correct_answer" not in corps
    assert "explanation" not in corps
    # Le jeton est opaque : la réponse « A » n'y est pas lisible en clair.
    assert corps["quiz_token"]
    assert "correct_answer" not in corps["quiz_token"]


async def test_la_competence_est_deduite_du_cadre_curriculaire(api_client, student_headers):
    reponse = await api_client.post(
        "/api/quiz",
        json={"curriculum_context": {"chapitre": "Probabilités", "serie": "S1"}},
        headers=student_headers,
    )
    assert reponse.json()["competence"] == "Probabilités"


async def test_sans_aucune_indication_le_quiz_est_refuse(api_client, student_headers):
    """On préfère refuser qu'interroger l'élève au hasard."""
    reponse = await api_client.post("/api/quiz", json={}, headers=student_headers)
    assert reponse.status_code == 422


async def test_un_chapitre_sans_evaluation_n_invente_aucune_question(
    api_client, student_headers
):
    """Le corpus d'exemple ne porte aucune section d'auto-évaluation.

    C'est le cœur de la décision D12 : plutôt qu'une question fabriquée dont la
    réponse pourrait être fausse, l'élève reçoit un aveu. Aucun modèle n'est
    sollicité sur ce chemin — il n'y a plus de génération du tout.
    """
    reponse = await api_client.post(
        "/api/quiz", json={"competence": "Dérivation"}, headers=student_headers
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["available"] is False
    assert corps["choices"] == []
    assert corps["quiz_token"] == ""
    assert "pas encore de question d'évaluation corrigée" in corps["instructions"]


async def test_un_qcm_sans_cle_de_correction_n_est_pas_servi(
    corpus_avec_evaluation, student_headers
):
    """La leçon contient un QCM, mais sans clé : il est écarté, pas complété.

    C'est la borne qui empêche le défaut de revenir : deviner la bonne réponse
    d'un QCM qui n'en déclare pas, c'est exactement ce que faisait le modèle.
    """
    reponse = await corpus_avec_evaluation.post(
        "/api/quiz",
        json={"competence": "Dérivation", "quiz_type": "qcm"},
        headers=student_headers,
    )
    assert reponse.json()["available"] is False


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
