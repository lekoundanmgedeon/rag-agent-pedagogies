"""Lecture des questions d'évaluation dans le corpus — décision D12.

Ce module remplace la génération de quiz par un modèle. Ce qu'il faut protéger
n'est donc pas seulement ce qu'il lit, mais surtout **ce qu'il refuse de
servir** : un QCM sans clé de correction, une section absente, un item mal
formé. Toute tolérance ici ramènerait le défaut mesuré le 2026-08-28 — une
question dont la bonne réponse déclarée était fausse.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from agent_tuteur.agent.quiz_corpus import (
    choisir,
    extraire_les_questions,
    questions_du_chapitre,
)
from agent_tuteur.ingestion.normalize import to_pivot

SECTION = """## 18. Auto-évaluation

### QCM
1. Le module de \\( 3-4i \\) est :
 a) 5 b) 7 c) 1 d) 25

### Vrai/Faux
1. Pour tout complexe \\( z \\), \\( |z|^2 = z^2 \\). (Faux — c'est \\( z\\bar z \\))
2. L'argument d'un nombre complexe est toujours unique. (Faux — défini modulo \\( 2\\pi \\))
3. Le conjugué de \\( re^{i\\theta} \\) est \\( re^{-i\\theta} \\). (Vrai)
"""


def test_les_items_vrai_faux_sont_lus_avec_leur_correction():
    questions = extraire_les_questions(SECTION)
    vrai_faux = [q for q in questions if q.type == "vrai_faux"]
    assert len(vrai_faux) == 3
    assert [q.reponse for q in vrai_faux] == ["B", "B", "A"]
    assert vrai_faux[0].choix == (("A", "Vrai"), ("B", "Faux"))
    assert "z\\bar z" in vrai_faux[0].explication


def test_la_parenthese_du_verdict_n_est_pas_confondue_avec_du_latex():
    """Piège du format : les formules s'écrivent aussi entre parenthèses.

    « (Faux — défini modulo \\( 2\\pi \\)) » contient trois parenthèses ouvrantes.
    Sans la distinction contre-oblique, l'énoncé serait tronqué au milieu d'une
    formule — et l'élève lirait une question amputée.
    """
    item = extraire_les_questions(SECTION)[1]
    assert item.enonce == "L'argument d'un nombre complexe est toujours unique."
    assert item.explication == "défini modulo \\( 2\\pi \\)"


def test_un_qcm_sans_cle_est_ecarte():
    """Le corpus décrit les propositions mais pas la bonne : on ne devine pas."""
    assert [q.type for q in extraire_les_questions(SECTION)] == ["vrai_faux"] * 3


def test_un_qcm_avec_cle_devient_servable():
    """Le jour où une leçon porte la correction, elle suffit — sans toucher au code."""
    avec_cle = SECTION.replace(
        "1. Le module de \\( 3-4i \\) est :", "1. Le module de \\( 3-4i \\) est : (Réponse : a)"
    )
    qcm = [q for q in extraire_les_questions(avec_cle) if q.type == "qcm"]
    assert len(qcm) == 1
    assert qcm[0].reponse == "A"
    assert qcm[0].choix == (("A", "5"), ("B", "7"), ("C", "1"), ("D", "25"))
    assert "(Réponse" not in qcm[0].enonce


def test_la_lecture_survit_a_la_normalisation_des_delimiteurs():
    """Le texte indexé n'est pas le texte source : l'ingestion l'a normalisé.

    Les délimiteurs « \\( … \\) » deviennent « $ … $ » (cas QA #37) : le lecteur
    doit fonctionner sur les deux, sans quoi il ne trouverait rien dans un index
    reconstruit.
    """
    questions = extraire_les_questions(to_pivot(SECTION))
    assert len(questions) == 3
    assert questions[0].enonce.startswith("Pour tout complexe $ z $")


@pytest.mark.parametrize(
    "texte",
    [
        "## 18. Auto-évaluation\n\n### Vrai/Faux\n1. Une affirmation sans verdict.\n",
        "## 18. Auto-évaluation\n\n### Questions ouvertes\n1. Expliquer pourquoi…\n",
        "## 2. Introduction\n\nLa dérivée mesure une vitesse de variation.\n",
        "",
    ],
)
def test_rien_n_est_servi_faute_de_correction_ecrite(texte):
    assert extraire_les_questions(texte) == []


def test_la_section_est_reperee_dans_une_lecon_reellement_ingeree():
    """Le chemin complet : découpage, normalisation, puis lecture des questions.

    Le test passe par l'ingestion réelle et non par un faux morceau de texte —
    c'est elle qui décide de la forme des chunks (titre en tête, délimiteurs
    normalisés), et c'est sur cette forme-là que le lecteur doit tomber juste.
    Les 17 autres sections de la leçon ne doivent, elles, rien produire.
    """
    from agent_tuteur.ingestion.pipeline import process_document

    chemin = Path("tests/qa/corpus_qa/Lecon_01_Nombres_Complexes_TS2S4.md")
    resultat = process_document(chemin.name, chemin.read_bytes(), None)

    class _Extrait:  # même surface que ScoredChunk : seul `.chunk.text` est lu.
        def __init__(self, chunk):
            self.chunk = chunk

    questions = questions_du_chapitre(_Extrait(c) for c in resultat.chunks)
    assert len(questions) == 3
    assert all(q.type == "vrai_faux" for q in questions)
    assert questions[2].reponse == "A"


def test_le_tirage_porte_sur_le_choix_et_respecte_le_type():
    questions = extraire_les_questions(SECTION)
    tire = choisir(questions, "vrai_faux", rng=random.Random(0))
    assert tire in questions
    # Aucun QCM exploitable dans cette section : on ne rabat pas sur un autre type.
    assert choisir(questions, "qcm") is None
    assert choisir([], "vrai_faux") is None
