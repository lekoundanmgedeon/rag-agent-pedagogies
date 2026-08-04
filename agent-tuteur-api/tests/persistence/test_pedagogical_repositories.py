"""Repositories du domaine pédagogique : maîtrise, résultats, badges, liaisons.

Ces tests tournent sur SQLite en mémoire (fixture ``session``) : ils valident la
logique — isolation par tenant, unicité, règle d'accès — sans infrastructure.
"""

import pytest

from agent_tuteur.persistence.repositories import (
    BadgeRepository,
    ExerciseResultRepository,
    MasteryRepository,
    RecommendationRepository,
    StudentLinkRepository,
    UserRepository,
)

# --- Maîtrise ----------------------------------------------------------------


async def test_la_premiere_tentative_cree_la_ligne(session):
    repo = MasteryRepository(session)
    resultat = await repo.record_attempt(
        student_id="eleve-1", competence="Dérivation", is_correct=True
    )
    assert resultat["attempts"] == 1
    assert resultat["successes"] == 1
    assert resultat["mastery_score"] == 1.0


async def test_les_tentatives_s_accumulent_sur_la_meme_ligne(session):
    repo = MasteryRepository(session)
    for correct in (True, False, True):
        await repo.record_attempt(
            student_id="eleve-1", competence="Dérivation", is_correct=correct
        )
    lignes = await repo.list_for_student("eleve-1")
    assert len(lignes) == 1
    assert lignes[0]["attempts"] == 3
    assert lignes[0]["successes"] == 2


async def test_un_quiz_note_alimente_la_maitrise(session):
    repo = MasteryRepository(session)
    resultat = await repo.record_attempt(
        student_id="eleve-1", competence="Limites", score=0.75
    )
    assert resultat["mastery_score"] == 0.75
    assert resultat["successes"] == 1  # 0.75 dépasse le seuil de réussite


async def test_les_competences_les_plus_faibles_viennent_en_premier(session):
    repo = MasteryRepository(session)
    await repo.record_attempt(student_id="eleve-1", competence="Solide", is_correct=True)
    await repo.record_attempt(student_id="eleve-1", competence="Fragile", is_correct=False)

    faibles = await repo.weakest("eleve-1", limit=1)
    assert [m["competence"] for m in faibles] == ["Fragile"]


async def test_une_competence_jamais_tentee_n_est_pas_dite_faible(session):
    """Un score de 0 sans tentative veut dire « inconnu », pas « non maîtrisé »."""
    repo = MasteryRepository(session)
    assert await repo.weakest("eleve-inconnu") == []


async def test_les_tenants_ne_se_voient_pas(session):
    repo = MasteryRepository(session)
    await repo.record_attempt(
        student_id="eleve-1", competence="Dérivation", is_correct=True, tenant_id="ecole-a"
    )
    assert await repo.list_for_student("eleve-1", tenant_id="ecole-b") == []
    assert len(await repo.list_for_student("eleve-1", tenant_id="ecole-a")) == 1


# --- Résultats d'exercices ----------------------------------------------------


async def test_un_resultat_est_enregistre_avec_son_detail(session):
    repo = ExerciseResultRepository(session)
    enregistre = await repo.record(
        {
            "student_id": "eleve-1",
            "competence": "Dérivation",
            "exercise_type": "quiz",
            "score": 0.8,
            "details": {"reponses": [1, 0, 1]},
        }
    )
    assert enregistre["exercise_type"] == "quiz"
    assert enregistre["details"] == {"reponses": [1, 0, 1]}


async def test_les_resultats_reviennent_du_plus_recent_au_plus_ancien(session):
    repo = ExerciseResultRepository(session)
    for i in range(3):
        await repo.record({"student_id": "eleve-1", "competence": f"c{i}"})
    resultats = await repo.list_for_student("eleve-1")
    assert len(resultats) == 3


# --- Badges -------------------------------------------------------------------


async def test_un_badge_n_est_attribue_qu_une_fois(session):
    repo = BadgeRepository(session)
    premier = await repo.award(student_id="eleve-1", code="premier_pas", label="🌱")
    second = await repo.award(student_id="eleve-1", code="premier_pas", label="🌱")

    assert premier is not None
    assert second is None
    assert len(await repo.list_for_student("eleve-1")) == 1


# --- Liaisons parent/enseignant → élève --------------------------------------


async def _compte(session, role: str, email: str) -> str:
    user = await UserRepository(session).create(
        tenant_id="default", email=email, password_hash="x", role=role
    )
    return user.id


async def test_un_parent_ne_voit_que_les_eleves_qui_lui_sont_lies(session):
    """La règle d'accès la plus importante du projet."""
    repo = StudentLinkRepository(session)
    parent = await _compte(session, "parent", "parent@ecole.sn")
    await repo.link(user_id=parent, student_id="mon-enfant")

    assert await repo.can_access(user_id=parent, student_id="mon-enfant") is True
    assert await repo.can_access(user_id=parent, student_id="enfant-des-voisins") is False
    assert await repo.list_students_for(parent) == ["mon-enfant"]


async def test_une_liaison_ne_traverse_pas_les_tenants(session):
    repo = StudentLinkRepository(session)
    parent = await _compte(session, "parent", "parent@ecole.sn")
    await repo.link(user_id=parent, student_id="eleve-1", tenant_id="ecole-a")

    assert await repo.can_access(
        user_id=parent, student_id="eleve-1", tenant_id="ecole-b"
    ) is False


async def test_un_compte_sans_liaison_ne_voit_aucun_eleve(session):
    repo = StudentLinkRepository(session)
    enseignant = await _compte(session, "teacher", "prof@ecole.sn")
    assert await repo.list_students_for(enseignant) == []


# --- Recommandations ----------------------------------------------------------


async def test_une_recommandation_peut_etre_anonyme(session):
    """Cas d'une recommandation produite automatiquement, sans enseignant."""
    repo = RecommendationRepository(session)
    reco = await repo.create(student_id="eleve-1", competence="Limites", message="À revoir")
    assert reco["author_user_id"] is None
    assert (await repo.list_for_student("eleve-1"))[0]["competence"] == "Limites"


async def test_une_recommandation_porte_son_auteur(session):
    enseignant = await _compte(session, "teacher", "prof@ecole.sn")
    repo = RecommendationRepository(session)
    reco = await repo.create(
        student_id="eleve-1", competence="Limites", author_user_id=enseignant
    )
    assert reco["author_user_id"] == enseignant


# --- Rôles étendus ------------------------------------------------------------


@pytest.mark.parametrize("role", ["admin", "teacher", "parent", "student"])
async def test_les_quatre_roles_sont_acceptes(session, role):
    user = await UserRepository(session).create(
        tenant_id="default", email=f"{role}@ecole.sn", password_hash="x", role=role
    )
    assert user.role == role
