"""Reconnaissance des métadonnées curriculaires (porté de NURU `test_metadata_unit.py`).

Les tests d'origine étaient conditionnels (``if "serie" in metadata: assert…``)
ou enveloppés dans un ``except: pass`` : ils ne pouvaient pratiquement pas
échouer. On garde ici leur *intention* — les cas réels du corpus sénégalais —
avec des assertions qui, elles, échouent quand le comportement change.
"""

from pathlib import Path

import pytest

from agent_tuteur.ingestion.loaders.metadata import extraire_metadonnees
from agent_tuteur.ingestion.loaders.metadata import from_content, from_filename

# --- Depuis le nom de fichier -------------------------------------------------


@pytest.mark.parametrize(
    "nom,serie_attendue",
    [
        ("TD1-Probabilite-TS1.pdf", "TS1"),
        ("S1-Bac-Blanc-LBD-2017.pdf", "S1"),
        ("Fascicule_TS1.pdf", "TS1"),
    ],
)
def test_la_serie_est_reconnue_dans_le_nom(nom, serie_attendue):
    assert from_filename.extraire(Path(nom))["serie"] == serie_attendue


def test_un_td_n_est_pas_pris_pour_la_serie_d1():
    """« TD1 » contient « D1 » : la garde de motif doit l'empêcher de matcher."""
    trouve = from_filename.extraire(Path("TD1-Derivation.pdf"))
    assert trouve.get("serie") != "D1"


@pytest.mark.parametrize(
    "nom,numero",
    [
        ("Chapitre1_Revisions.pdf", "1"),
        ("Chap_2_Derivabilite.pdf", "2"),
        ("Chapitre_3_Limites.pdf", "3"),
    ],
)
def test_le_numero_de_chapitre_est_reconnu(nom, numero):
    assert from_filename.extraire(Path(nom))["chapitre_numero"] == numero


@pytest.mark.parametrize(
    "nom,type_attendu",
    [
        ("cours_derivabilite.pdf", "cours"),
        ("exercices_probabilites.pdf", "exercices"),
        ("Devoir_maison.pdf", "devoir"),
        ("composition_s1.pdf", "composition"),
        ("annales_maths.pdf", "annales"),
    ],
)
def test_la_nature_du_document_est_reconnue(nom, type_attendu):
    assert from_filename.extraire(Path(nom))["type_document"] == type_attendu


def test_la_notion_remplace_le_chapitre_absent():
    """Sans « Chapitre N », le sujet est déduit du nom (cas majoritaire du corpus)."""
    assert from_filename.extraire(Path("TD1-Probabilite-TS1.pdf"))["chapitre"] == "Probabilités"


def test_le_dossier_parent_donne_la_nature_du_document():
    trouve = from_filename.extraire(Path("data/raw/cours/01_Revisions_trigonometrie.pdf"))
    assert trouve["type_document"] == "cours"
    assert trouve["source_document"] == "01_Revisions_trigonometrie.pdf"


def test_l_annee_est_reconnue():
    assert from_filename.extraire(Path("Sujet_2023.pdf"))["annee"] == "2023"


# --- Depuis le contenu --------------------------------------------------------


def test_le_titre_et_le_chapitre_sont_lus_dans_l_entete():
    trouve = from_content.extraire("# Chapitre 1 : Les Nombres Réels\n\nContenu…")
    assert trouve["titre"] == "Chapitre 1 : Les Nombres Réels"
    assert trouve["chapitre"] == "Les Nombres Réels"
    assert trouve["chapitre_numero"] == "1"


def test_la_classe_et_la_serie_sont_lues_dans_l_entete():
    trouve = from_content.extraire("Classe de Terminale S1\nAnnée scolaire 2023-2024")
    assert trouve["classe"] == "Terminale"
    assert trouve["serie"] == "S1"
    assert trouve["annee_scolaire"] == "2023-2024"


def test_l_auteur_est_lu_meme_en_majuscules():
    assert from_content.extraire("Professeur: M. Babacar DJITTE")["auteur"] == "M. Babacar DJITTE"


def test_le_contenu_ne_remplace_jamais_une_valeur_deja_connue():
    """Le nom de fichier est plus fiable que l'en-tête, souvent recopié."""
    trouve = from_content.extraire(
        "# Chapitre 9 : Intégration\n", deja_connu={"chapitre": "Probabilités"}
    )
    assert "chapitre" not in trouve


# --- Fusion et alignement sur la taxonomie ------------------------------------


def test_extraction_complete_sur_un_cas_reel_du_corpus():
    chemin = Path("data/raw/exercices/Chap1_Probabilite/TD1-Probabilite-TS1.pdf")
    contenu = (
        "# Chapitre 1 : Probabilités\n\n"
        "Classe de Terminale S1\n"
        "Année scolaire 2023-2024\n\n"
        "**Exercice 1 :** Calculer la probabilité…\n"
    )
    meta = extraire_metadonnees(chemin, contenu)

    assert meta["classe"] == "Terminale"
    assert meta["serie"] == "S1"          # « TS1 » ramené à sa forme canonique
    assert meta["chapitre"] == "Probabilités"
    assert meta["discipline"] == "mathématiques"
    assert meta["niveau"] == "secondaire"
    assert meta["source_document"] == "TD1-Probabilite-TS1.pdf"


def test_aucune_classe_ni_serie_n_est_inventee():
    """Écart assumé avec NURU : un champ vide vaut mieux qu'un champ faux."""
    meta = extraire_metadonnees(Path("notes.pdf"), "Texte simple sans métadonnées")
    assert "classe" not in meta
    assert "serie" not in meta
    assert meta["discipline"] == "mathématiques"


def test_les_metadonnees_saisies_a_la_main_font_foi():
    meta = extraire_metadonnees(
        Path("data/raw/cours/TD1-Probabilite-TS1.pdf"),
        "# Chapitre 1 : Probabilités",
        saisies={"discipline": "Physique-Chimie", "chapitre": "Mécanique"},
    )
    assert meta["discipline"] == "Physique-Chimie"
    assert meta["chapitre"] == "Mécanique"


def test_les_defauts_de_l_appelant_cedent_devant_ce_qui_est_lu():
    meta = extraire_metadonnees(
        Path("TD1-Probabilite-TS1.pdf"), "", defauts={"serie": "S2", "classe": "Seconde"}
    )
    assert meta["serie"] == "S1"   # lu dans le nom de fichier, prioritaire


def test_la_liste_de_competences_n_alimente_pas_le_champ_competence():
    """« Calculer, Résoudre » sont des verbes, pas une compétence du programme."""
    meta = extraire_metadonnees(Path("cours.pdf"), "Compétences : Calculer, Résoudre\n")
    assert "competence" not in meta
    assert meta["competences"] == ["Calculer, Résoudre"]
