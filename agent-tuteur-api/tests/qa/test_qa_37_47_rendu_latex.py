"""Cas QA #37 et #47 — rendu des expressions mathématiques.

- **#37** « Peux-tu m'expliquer le principe du raisonnement par récurrence avec
  un exemple simple ? » (Pierre Ndong) : refus correct, mais « formatage des
  expressions mathématiques à revoir ».
- **#47** (priorité Basse, même famille) : rendu LaTeX d'une suite.

Cause racine mesurée, et elle n'est pas dans le modèle : les 12 leçons du corpus
écrivent leurs formules en ``\\( … \\)`` (120 occurrences dans la seule leçon 01),
alors que le format pivot du projet — et la consigne envoyée au modèle — est
``$ … $``. Ces extraits partaient tels quels dans le prompt ; le modèle recopiait
la typographie qu'on lui montrait, en contradiction avec sa propre consigne.
Vérifié sur la stack réelle avant correctif : la réponse à « Expliques moi les
dérivées » sortait en ``\\( f'(a) \\)``.

Le correctif est en amont (``ingestion.normalize.delimiteurs_latex``), appliqué à
l'ingestion **et** à l'assemblage du prompt : un index déjà construit garde ses
délimiteurs d'origine, et le réindexer est une opération sur données qu'aucun
correctif de code ne déclenche tout seul.
"""

from __future__ import annotations

import pytest

DELIMITEURS_PROSCRITS = (r"\(", r"\)", r"\[", r"\]")


@pytest.mark.parametrize(
    "question",
    [
        "Fais-moi un cours sur les nombres complexes",  # branche cours
        "Donne moi un exercice sur le calcul d integral",  # branche entraînement
        "z = 3 + 4i : quelle est sa partie réelle ?",  # branche exercice
    ],
)
async def test_aucun_delimiteur_hors_format_pivot_ne_part_au_modele(
    question, agent_qa, session_eleve
):
    """Les trois branches servent des extraits : les trois sont concernées."""
    prepared = await agent_qa.prepare(question, {"serie": "S2"}, session_eleve)
    for delimiteur in DELIMITEURS_PROSCRITS:
        assert delimiteur not in prepared.final_prompt, (
            f"délimiteur {delimiteur!r} envoyé au modèle : il le recopiera "
            f"(question : {question!r})"
        )


async def test_le_contenu_mathematique_survit_a_la_normalisation(agent_qa, session_eleve):
    """La transformation ne doit toucher QUE les délimiteurs.

    Sans ce contrôle, une normalisation trop gourmande passerait le test
    précédent en supprimant les formules — le rendu serait « corrigé » et le
    cours vidé de sa substance.
    """
    prepared = await agent_qa.prepare(
        "Donne moi un exercice sur le calcul d integral", {"serie": "S2"}, session_eleve
    )
    assert "int_1^2" in prepared.final_prompt, "les énoncés ont perdu leurs intégrales"
    assert "$" in prepared.final_prompt
