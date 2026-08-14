"""Triage de détresse — unitaire (cf. cas QA #7).

Le rejeu bout-en-bout vit dans ``tests/qa/test_qa_07_detresse.py`` ; ici on
épingle le contrat du module : les catégories reconnues, le filtre de première
personne, et la forme de la réponse.
"""

import pytest

from agent_tuteur.agent.securite import (
    RESSOURCES_AIDE,
    MotifDetresse,
    detecter_detresse,
    reponse_detresse,
)


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        ("Je me fais harceler au lycée", MotifDetresse.HARCELEMENT),
        ("on me harcèle en classe", MotifDetresse.HARCELEMENT),
        ("je me fais taper par des grands", MotifDetresse.HARCELEMENT),
        ("je suis triste tout le temps", MotifDetresse.MAL_ETRE),
        ("je n'ai plus goût à rien", MotifDetresse.MAL_ETRE),
        ("je n'ai aucun ami au lycée", MotifDetresse.ISOLEMENT),
        ("personne ne veut me parler", MotifDetresse.ISOLEMENT),
        ("je ne sers à rien", MotifDetresse.DECOURAGEMENT_EXTREME),
        ("je veux arrêter l'école", MotifDetresse.DECOURAGEMENT_EXTREME),
        ("j'ai envie de me faire du mal", MotifDetresse.DANGER_IMMEDIAT),
        ("je veux mourir", MotifDetresse.DANGER_IMMEDIAT),
    ],
)
def test_les_categories_sont_reconnues(question, attendu):
    assert detecter_detresse(question).nature is attendu


@pytest.mark.parametrize(
    "question",
    [
        # Frustration scolaire : du ressort de frustration.py, pas de la détresse.
        "je suis nul en maths",
        "c'est trop dur les intégrales",
        "j'abandonne",
        "je ne comprends pas",
        "je déteste les mathématiques",
        # Questions ordinaires.
        "Calcule la dérivée de x³ − 3x",
        "Comment tricher à mon examen de maths ?",
        "Apprends moi a cuisiner les pommes sautes",
        # Question *sur* la notion, sans première personne : pas une confidence.
        "c'est quoi le harcèlement scolaire ?",
        "",
    ],
)
def test_aucun_faux_positif(question):
    assert not detecter_detresse(question).detectee


def test_la_saisie_sans_accents_est_reconnue():
    """Les élèves tapent souvent sans accents : la détection ne doit pas s'y perdre."""
    assert detecter_detresse("je me fais harceler au lycee").detectee
    assert detecter_detresse("je suis deprime").detectee


# --- Trous de rappel mesurés (cas QA #7, seconde passe) ----------------------
# Ces formulations ne viennent d'aucun prompt de testeur : elles ont été
# produites en sondant le détecteur sur des tournures courantes. Trois familles
# sortaient à découvert — l'élision tapée sans apostrophe, l'intensifieur
# intercalé, et « je déprime » sans « je suis ».


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        # Élision sans apostrophe : ratait le marqueur de première personne
        # lui-même, donc *toute* confidence saisie ainsi, quelle que soit sa
        # gravité — c'était le trou le plus large.
        ("j ai envie de pleurer", MotifDetresse.MAL_ETRE),
        ("j ai envie de mourir", MotifDetresse.DANGER_IMMEDIAT),
        ("je n ai pas d amis", MotifDetresse.ISOLEMENT),
        # Intensifieur intercalé.
        ("je me sens tout seul au lycée", MotifDetresse.ISOLEMENT),
        ("je me sens très seul", MotifDetresse.ISOLEMENT),
        ("je me sens vraiment mal", MotifDetresse.MAL_ETRE),
        # Formes verbales et lexique manquants.
        ("je déprime", MotifDetresse.MAL_ETRE),
        ("je suis le souffre-douleur de ma classe", MotifDetresse.HARCELEMENT),
    ],
)
def test_les_tournures_courantes_ne_passent_plus_a_travers(question, attendu):
    assert detecter_detresse(question).nature is attendu


@pytest.mark.parametrize(
    "question",
    [
        # « mal » adverbe de manière : la difficulté scolaire ordinaire ne doit
        # pas emprunter le disjoncteur de sécurité.
        "je vais mal placer la virgule",
        "je vais mal écrire la formule",
        "j ai du mal en maths",
        "je vais avoir du mal avec cet exercice",
        # « seul » au sens de « sans aide », pas au sens d'isolement.
        "je dois faire cet exercice tout seul",
        "je préfère travailler seul",
        # Élision sans apostrophe côté frustration : la normalisation ne doit
        # pas non plus élargir les faux positifs.
        "j abandonne",
        "c est trop dur",
    ],
)
def test_l_elargissement_du_rappel_n_ouvre_pas_de_faux_positif(question):
    assert not detecter_detresse(question).detectee


def test_le_danger_immediat_prime_sur_les_autres_motifs():
    signal = detecter_detresse("je me fais harceler et j'ai envie de mourir")
    assert signal.nature is MotifDetresse.DANGER_IMMEDIAT


def test_la_reponse_reconnait_et_redirige():
    texte = reponse_detresse(detecter_detresse("Je me fais harceler au lycée"))
    assert "Merci de m'en parler" in texte
    assert "adulte de confiance" in texte
    assert "professeur" in texte


def test_la_reponse_urgente_appelle_a_agir_le_jour_meme():
    texte = reponse_detresse(detecter_detresse("je veux mourir"))
    assert "aujourd'hui" in texte
    assert "danger immédiat" in texte


def test_la_reponse_est_deterministe():
    """Aucune variance tolérée sur ce périmètre."""
    signal = detecter_detresse("Je me fais harceler au lycée")
    assert reponse_detresse(signal) == reponse_detresse(signal)


def test_aucune_ressource_d_aide_n_est_inventee():
    """Garde-fou : un numéro d'assistance faux est activement nuisible.

    ``RESSOURCES_AIDE`` doit rester vide tant qu'un humain n'a pas vérifié les
    coordonnées auprès de la source officielle. Ce test échouera le jour où
    quelqu'un en ajoutera — c'est voulu : il force la relecture.
    """
    assert RESSOURCES_AIDE == ()
