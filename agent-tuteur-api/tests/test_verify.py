"""Contrôles déterministes sur la réponse générée (porté de NURU `verifier_agent.py`).

Seuls les deux contrôles **factuels** de NURU ont été portés. Les heuristiques
qui notaient la « cohérence » en comptant les mots « donc » et « ainsi » ont été
écartées : elles récompensaient le style, pas la justesse.
"""

from agent_tuteur.agent.verify import verifier_coherence_mathematique

# --- Contrôle 1 : niveau du vocabulaire --------------------------------------


def test_une_reponse_du_niveau_attendu_passe():
    rapport = verifier_coherence_mathematique(
        "La dérivée de $x^2$ est $2x$.", competence="Dérivation"
    )
    assert rapport.est_valide


def test_le_vocabulaire_universitaire_est_signale():
    """Le modèle dérive régulièrement vers l'analyse à plusieurs variables."""
    rapport = verifier_coherence_mathematique(
        "On calcule les dérivées partielles de la fonction.", competence="Dérivation"
    )
    assert not rapport.est_valide
    assert "hors-programme" in rapport.problemes[0]


def test_le_controle_ignore_les_accents():
    rapport = verifier_coherence_mathematique(
        "Utilisons le gradient de f.", competence="Dérivation"
    )
    assert not rapport.est_valide


def test_le_vocabulaire_est_legitime_si_la_competence_le_prevoit():
    """Un cours sur les fonctions à deux variables a le droit d'en parler."""
    rapport = verifier_coherence_mathematique(
        "On calcule les dérivées partielles.",
        competence="Fonctions à plusieurs variables",
    )
    assert rapport.est_valide


def test_sans_competence_connue_le_controle_s_applique_quand_meme():
    rapport = verifier_coherence_mathematique("Voici le gradient.", competence=None)
    assert not rapport.est_valide


# --- Contrôle 2 : fidélité au calcul exact -----------------------------------


def test_le_resultat_calcule_doit_apparaitre_dans_la_reponse():
    rapport = verifier_coherence_mathematique(
        "La solution est $x = 4$.", competence="Équations", resultat_calcule="x = 4"
    )
    assert rapport.est_valide


def test_un_resultat_recalcule_par_le_modele_est_signale():
    """Le contrôle le plus utile : le modèle refait le calcul et se trompe."""
    rapport = verifier_coherence_mathematique(
        "La solution est $x = 5$.", competence="Équations", resultat_calcule="x = 4"
    )
    assert not rapport.est_valide
    assert "n'apparaît pas" in rapport.problemes[0]


def test_sans_calcul_exact_ce_controle_ne_s_applique_pas():
    rapport = verifier_coherence_mathematique(
        "Réfléchissons ensemble.", competence="Équations", resultat_calcule=None
    )
    assert rapport.est_valide


# --- Cumul --------------------------------------------------------------------


def test_les_deux_problemes_sont_rapportes_ensemble():
    rapport = verifier_coherence_mathematique(
        "Le gradient donne $x = 5$.", competence="Équations", resultat_calcule="x = 4"
    )
    assert len(rapport.problemes) == 2
