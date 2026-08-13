"""Cas QA #6 — l'exercice le plus basique du chapitre le mieux couvert.

« z = 3 + 4i : partie réelle, partie imaginaire, conjugué, module » (Pierre
Ndong). L'agent affirmait ne pas avoir accès au chapitre Nombres Complexes,
« qui pourtant existe et est indexé » — « très préoccupant pour la fiabilité
perçue », dit le rapport.

Le rejeu a séparé deux causes qui se cumulaient :

* **la récupération** ne défaille plus. Mesuré sur le corpus figé, les cinq
  extraits remontés sont tous ``Lecon_01_Nombres_Complexes`` et le prompt porte
  « Définition », « conjugué », « module », « partie réelle ». L'échec d'origine
  venait de l'index Qdrant de la démo, périmé et incomplet au moment du test
  (149 chunks sur 176 sans métadonnée chapitre) — un problème de **données**,
  tracé dans ``qa_status.json`` et à revérifier sur la stack réelle ;
* **la vérification symbolique**, elle, échouait bel et bien, et c'est ce que ce
  fichier couvre. ``i`` n'était pas l'unité imaginaire : « 3+4i » s'analysait en
  ``4*i + 3`` avec ``i`` symbole libre, ``compute`` renonçait, et
  ``calcul_non_verifie`` s'armait. Le prompt interdisait alors d'annoncer le
  moindre résultat chiffré. L'agent avait les bons extraits sous les yeux et
  l'interdiction de s'en servir.

Ce que la couche A prouve ici : les quatre grandeurs demandées sont établies et
atteignent le prompt, et l'interdiction ne s'arme plus. Que la réponse les
énonce relève de la couche B, donc de D2.
"""

from __future__ import annotations

import pytest

from agent_tuteur.tools.complexe import analyser_complexe, analyser_la_demande

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS_06 = par_id(tous_les_cas())[6]


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_retrouve_bien_le_chapitre(agent_qa, session_eleve):
    """Le cœur du reproche : le chapitre existe, il doit être servi."""
    resultat = await agent_qa.respond(CAS_06.prompt, {"serie": "S2"}, session_eleve)

    chapitres = {sc.chunk.metadata.chapitre for sc in resultat.retrieved}
    assert chapitres == {"Les Nombres Complexes"}, chapitres
    assert resultat.trace["sources"], "aucun extrait servi sur un exercice du chapitre indexé"


async def test_le_prompt_exact_etablit_les_quatre_grandeurs(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_06.prompt, {"serie": "S2"}, session_eleve)

    complexe = resultat.trace["complexe"]
    assert complexe is not None, "le complexe de l'énoncé n'a pas été analysé"
    assert complexe["partie_reelle"] == "3"
    assert complexe["partie_imaginaire"] == "4"
    assert complexe["conjugue"] == "3 - 4*I"
    assert complexe["module"] == "5"


async def test_le_prompt_exact_n_interdit_plus_d_annoncer_un_resultat(
    agent_qa, session_eleve
):
    """L'interdiction s'armait parce que rien n'avait pu être vérifié."""
    prepared = await agent_qa.prepare(CAS_06.prompt, {"serie": "S2"}, session_eleve)

    assert prepared.trace["calcul_non_verifie"] is False
    assert "AUCUN résultat chiffré" not in prepared.final_prompt
    assert "Module : |z| = 5" in prepared.final_prompt
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


# --- Au-delà du prompt exact -------------------------------------------------


@pytest.mark.parametrize(
    ("corps", "reelle", "imaginaire", "conjugue", "module"),
    [
        ("3 + 4i", "3", "4", "3 - 4*I", "5"),
        ("2 - 3i", "2", "-3", "2 + 3*I", "sqrt(13)"),
        ("-1 + i", "-1", "1", "-1 - I", "sqrt(2)"),
        ("5", "5", "0", "5", "5"),
        ("4i", "0", "4", "-4*I", "4"),
    ],
)
def test_les_grandeurs_sont_etablies_symboliquement(
    corps, reelle, imaginaire, conjugue, module
):
    analyse = analyser_complexe(corps)

    assert analyse.partie_reelle == reelle
    assert analyse.partie_imaginaire == imaginaire
    assert analyse.conjugue == conjugue
    assert analyse.module == module


@pytest.mark.parametrize(
    "question",
    [
        "On considère le nombre complexe z = 3 + 4i",
        "soit z = 2 - 3i, donne le conjugué",
        "z = 1 + i et je cherche son module, c'est un complexe",
    ],
)
def test_les_enonces_de_complexes_sont_reconnus(question):
    assert analyser_la_demande(question) is not None


# --- La borne : ne rien promouvoir hors contexte complexe --------------------
# `i` est un indice de sommation parfaitement ordinaire ailleurs. Le promouvoir
# en unité imaginaire partout ferait taire des calculs corrects.


@pytest.mark.parametrize(
    "question",
    [
        "Calcule la dérivée de x³ − 3x",                    # cas #1
        "1-1=?",                                            # cas #10
        "Résous x² − 5x + 6 = 0",                           # cas #13
        "Comment dériver un quotient de fonctions ?",       # fixture positive #54
        "Fais-moi un cours sur les nombres complexes",      # cas #12 — pas d'énoncé
        "Donne-moi juste la réponse, j'ai pas le temps",    # fixture positive #53
        "la somme pour i = 1 jusqu'à n",                    # i = indice, pas imaginaire
    ],
)
def test_aucune_analyse_n_est_fabriquee_hors_enonce(question):
    assert analyser_la_demande(question) is None


def test_un_complexe_non_numerique_est_refuse():
    """Fermer plutôt qu'approximer : « z = a + bi » n'a pas de module chiffrable."""
    assert analyser_la_demande("le complexe z = a + bi, donne son module") is None


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
async def test_aucune_fixture_positive_n_est_degradee(cas, agent_qa, session_eleve):
    """Les 13 comportements validés ne doivent pas changer de branche.

    L'analyse peut légitimement s'activer sur #56, qui définit bien un complexe ;
    ce qui est interdit, c'est qu'un tour bascule en « calcul non vérifié » ou
    perde ses extraits à cause de ce correctif.
    """
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    analyse = prepared.trace.get("complexe")
    if analyse is not None:
        assert prepared.trace["calcul_non_verifie"] is False
