"""Nettoyage du texte extrait des PDF (porté de NURU `test_parser_unit.py`)."""

from agent_tuteur.ingestion.loaders.cleaners import (
    clean_newlines,
    clean_text,
    fix_latex,
    remove_headers_footers,
)


def test_les_blocs_de_lignes_vides_sont_resserres():
    assert clean_newlines("Ligne 1\n\n\n\nLigne 2") == "Ligne 1\n\nLigne 2"


def test_les_espaces_en_fin_de_ligne_sont_supprimes():
    assert clean_newlines("Ligne 1   \nLigne 2") == "Ligne 1\nLigne 2"


def test_les_entetes_de_page_sont_supprimes_mais_pas_le_contenu():
    texte = "Page 1\nContenu principal\nPage 2\nSuite du contenu"
    nettoye = remove_headers_footers(texte)
    assert "Page 1" not in nettoye
    assert "Page 2" not in nettoye
    assert "Contenu principal" in nettoye
    assert "Suite du contenu" in nettoye


def test_les_mentions_d_etablissement_et_de_professeur_sont_supprimees():
    texte = "Lycée Blaise Diagne\nProfesseur : M. DJITTE\nDérivée d'une fonction"
    nettoye = remove_headers_footers(texte)
    assert "Lycée" not in nettoye
    assert "Professeur" not in nettoye
    assert "Dérivée d'une fonction" in nettoye


def test_les_lignes_vides_structurantes_sont_conservees():
    """Le découpage en chunks s'appuie sur les lignes vides : ne pas les perdre."""
    assert remove_headers_footers("Titre\n\nCorps") == "Titre\n\nCorps"


def test_les_formules_centrees_passent_en_notation_crochets():
    assert fix_latex(r"$$\frac{1}{2}$$") == r"\[\frac{1}{2}\]"


def test_les_formules_en_ligne_sont_isolees_par_un_espace():
    assert fix_latex("soit$x$un réel") == "soit $x$ un réel"


def test_chaine_complete_de_nettoyage():
    texte = "Page 1\n\n\n\nTexte avec $$formule$$"
    nettoye = clean_text(texte)
    assert "Page 1" not in nettoye
    assert "\n\n\n" not in nettoye
    assert "formule" in nettoye
    assert r"\[" in nettoye
