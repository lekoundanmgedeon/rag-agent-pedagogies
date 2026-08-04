"""Règles de la maîtrise progressive (porté de NURU `student_profile.py`)."""

import pytest

from agent_tuteur.domain.mastery import (
    SEUIL_MAITRISE,
    badges_merites,
    est_une_reussite,
    maitrise_mise_a_jour,
    score_observe,
    statut_maitrise,
)

# --- Ramener un résultat à une note ------------------------------------------


def test_un_exercice_reussi_vaut_un():
    assert score_observe(is_correct=True) == 1.0


def test_un_exercice_rate_vaut_zero():
    assert score_observe(is_correct=False) == 0.0


def test_la_note_d_un_quiz_prime_sur_le_vrai_faux():
    assert score_observe(is_correct=True, score=0.6) == 0.6


@pytest.mark.parametrize("brut,attendu", [(-0.5, 0.0), (1.7, 1.0)])
def test_une_note_hors_bornes_est_ramenee_dans_l_intervalle(brut, attendu):
    assert score_observe(is_correct=None, score=brut) == attendu


# --- Évolution de la maîtrise ------------------------------------------------


def test_la_premiere_tentative_donne_directement_le_resultat():
    assert maitrise_mise_a_jour(None, 1.0) == 1.0
    assert maitrise_mise_a_jour(None, 0.0) == 0.0


def test_une_reussite_fait_monter_la_maitrise_sans_la_saturer():
    nouvelle = maitrise_mise_a_jour(0.5, 1.0)
    assert 0.5 < nouvelle < 1.0


def test_un_echec_fait_baisser_la_maitrise_sans_l_effondrer():
    nouvelle = maitrise_mise_a_jour(0.8, 0.0)
    assert 0.0 < nouvelle < 0.8


def test_les_resultats_recents_pesent_plus_que_les_anciens():
    """C'est tout l'intérêt de la moyenne mobile.

    Deux élèves ont 5 échecs et 5 réussites. Celui qui a progressé doit avoir
    une meilleure maîtrise que celui qui a régressé — un simple ratio les
    donnerait à égalité.
    """
    progresse = None
    for observe in [0.0] * 5 + [1.0] * 5:
        progresse = maitrise_mise_a_jour(progresse, observe)

    regresse = None
    for observe in [1.0] * 5 + [0.0] * 5:
        regresse = maitrise_mise_a_jour(regresse, observe)

    assert progresse > regresse


def test_la_maitrise_reste_toujours_entre_zero_et_un():
    score = None
    for observe in [1.0, 0.0, 0.7, 0.2, 1.0, 0.0]:
        score = maitrise_mise_a_jour(score, observe)
        assert 0.0 <= score <= 1.0


# --- Statut affiché -----------------------------------------------------------


def test_une_competence_jamais_tentee_est_non_commencee():
    assert statut_maitrise(0.0, attempts=0) == "non_commence"


def test_un_echec_n_est_pas_une_absence_de_donnees():
    """Distinction importante : un élève en difficulté ne doit pas disparaître."""
    assert statut_maitrise(0.0, attempts=3) == "faible"


@pytest.mark.parametrize(
    "score,attendu", [(0.95, "maitrise"), (0.8, "maitrise"), (0.6, "en_cours"), (0.2, "faible")]
)
def test_seuils_de_statut(score, attendu):
    assert statut_maitrise(score, attempts=5) == attendu


def test_reussite_partielle():
    assert est_une_reussite(0.5) is True
    assert est_une_reussite(0.49) is False


# --- Badges -------------------------------------------------------------------


def test_le_premier_resultat_donne_le_premier_badge():
    assert "premier_pas" in badges_merites(total_resultats=1, observe=0.4)


def test_un_score_parfait_donne_le_badge_sans_faute():
    assert "sans_faute" in badges_merites(total_resultats=3, observe=1.0)


def test_un_score_imparfait_ne_donne_pas_le_badge_sans_faute():
    assert "sans_faute" not in badges_merites(total_resultats=3, observe=0.9)


def test_la_maitrise_atteinte_donne_son_badge():
    merites = badges_merites(total_resultats=5, observe=1.0, maitrise=SEUIL_MAITRISE)
    assert "notion_maitrisee" in merites


def test_les_paliers_de_perseverance_s_accumulent():
    merites = badges_merites(total_resultats=50, observe=0.5)
    assert {"premier_pas", "dix_exercices", "cinquante_exercices"} <= set(merites)
