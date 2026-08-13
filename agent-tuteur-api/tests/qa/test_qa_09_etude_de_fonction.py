"""Cas QA #9 — « fais moi l'etude de fonction de ln(x) » (Mohamed FAYE).

Observé : au lieu de donner domaine, limites, dérivée et tableau de variation,
l'agent redemande une définition à l'élève.

Cause racine mesurée : la demande partait en intention ``exercice`` et recevait
la graduation socratique, dont le niveau 1 prescrit littéralement « Rappelle la
règle, la définition ou le théorème utile, **SANS l'appliquer au cas de
l'élève** ». La « définition redemandée » n'était donc pas une dérive du modèle
mais l'exécution fidèle de la consigne. Aucun outil n'était engagé :
``looks_like_calculation`` répond faux sur cette phrase, et il n'existait aucune
branche pour une demande d'étude.

Le contenu ne pouvait pas non plus venir du corpus : les deux chapitres indexés
sont les nombres complexes et le calcul intégral — la recherche remontait cinq
extraits de calcul intégral. Laisser le modèle produire domaine et variations
sur cette base aurait été exactement le résultat faux annoncé avec assurance
qu'interdit la règle non-négociable n°2.

D'où le choix : l'étude est **calculée par SymPy**, et ce qui n'est pas
calculable n'est pas affirmé. La couche A prouve ici le routage et le contenu du
prompt ; que la prose déroule effectivement les quatre blocs relève de D2.

Périmètre : ce fichier ne traite **pas** le cas #17, dont le prompt est presque
identique mais l'attente distincte (extraits hors-sujet, bloqué sur RC-0). Les
deux fixtures restent séparées, comme le veut la classification du backlog.
"""

from __future__ import annotations

import pytest

from agent_tuteur.tools.etude_fonction import (
    demande_une_etude_de_fonction,
    etudier,
    etudier_la_demande,
    expression_demandee,
    format_ensemble,
)

from . import assertions
from .cas import cas_positifs, par_id, tous_les_cas

CAS_09 = par_id(tous_les_cas())[9]


# --- Le prompt exact du testeur ----------------------------------------------


async def test_le_prompt_exact_declenche_une_etude_verifiee(agent_qa, session_eleve):
    resultat = await agent_qa.respond(CAS_09.prompt, {"serie": "S2"}, session_eleve)

    etude = resultat.trace["etude_fonction"]
    assert etude is not None, "aucune étude de fonction établie"
    assert etude["expression"] == "log(x)"
    assert etude["domaine"] == "]0 ; +∞["
    assert etude["derivee"] == "1/x"


async def test_le_prompt_exact_n_engage_plus_de_posture_socratique(agent_qa, session_eleve):
    """Le cœur du reproche : « redemande une définition » venait du niveau 1."""
    resultat = await agent_qa.respond(CAS_09.prompt, {"serie": "S2"}, session_eleve)

    assert resultat.trace["hint_level"] == 4, (
        f"posture socratique sur une demande d'étude : {resultat.trace['hint_reason']!r}"
    )


async def test_le_prompt_exact_porte_les_quatre_blocs_attendus(agent_qa, session_eleve):
    """Domaine, limites, dérivée, variations — les quatre du rapport de test."""
    prepared = await agent_qa.prepare(CAS_09.prompt, {"serie": "S2"}, session_eleve)

    for attendu in ("Domaine de définition : ]0 ; +∞[", "f'(x) = 1/x",
                    "lim en 0+ = -∞", "croissante sur ]0 ; +∞["):
        assert attendu in prepared.final_prompt, f"absent du prompt : {attendu!r}"
    assert "tableau de variation" in prepared.final_prompt.lower()
    assertions.assert_trace_compatible_avec_le_streaming(prepared)


async def test_le_prompt_exact_interdit_de_recalculer(agent_qa, session_eleve):
    """Les valeurs sont vérifiées : les refaire rouvrirait la règle n°2."""
    prepared = await agent_qa.prepare(CAS_09.prompt, {"serie": "S2"}, session_eleve)

    assert "ne les recalcule pas" in prepared.final_prompt
    assert prepared.trace["calcul_non_verifie"] is False


# --- Au-delà du prompt exact -------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "fais moi l'etude de fonction de ln(x)",
        "Fais-moi l'étude de fonction de ln(x)",
        "étudie la fonction x^2-4x+3",
        "étudier les variations de x**3-3*x",
        "tableau de variation de 1/x",
        "Donne-moi le sens de variation de exp(x)",
    ],
)
def test_les_formulations_d_une_demande_d_etude_sont_reconnues(question):
    assert demande_une_etude_de_fonction(question) is True
    assert etudier_la_demande(question) is not None


def test_la_ponctuation_du_testeur_ne_change_pas_le_verdict():
    """« Fais-moi » contient un trait d'union, caractère mathématiquement signifiant.

    Extraire depuis la phrase entière butait dessus (le garde-fou anti-troncature
    refuse de laisser un tel caractère dehors) et faisait échouer la variante
    accentuée tout en laissant passer l'autre. On découpe après la formule de
    demande, ce qui rend les deux équivalentes.
    """
    sans_accent = etudier_la_demande("fais moi l'etude de fonction de ln(x)")
    avec_accent = etudier_la_demande("Fais-moi l'étude de fonction de ln(x)")

    assert sans_accent is not None and avec_accent is not None
    assert sans_accent == avec_accent


@pytest.mark.parametrize(
    ("question", "attendu"),
    [
        ("fais moi l'etude de fonction de ln(x)", "ln(x)"),
        ("Fais-moi l'étude de fonction de ln(x)", "ln(x)"),
        ("tableau de variation de 1/x", "1/x"),
        ("étudie la fonction x^2-4x+3", "x^2-4x+3"),
    ],
)
def test_l_expression_est_isolee_apres_la_formule_de_demande(question, attendu):
    assert expression_demandee(question) == attendu


def test_les_bornes_internes_d_un_domaine_ne_sont_pas_manquees():
    """``1/x`` : les limites intéressantes sont en 0, ni dans inf ni dans sup."""
    etude = etudier("1/x")

    bornes = {borne for borne, _ in etude.limites}
    assert {"0-", "0+"} <= bornes, f"bornes internes manquées : {bornes}"
    assert etude.domaine == "]-∞ ; 0[ ∪ ]0 ; +∞["


def test_les_variations_viennent_du_signe_de_la_derivee():
    etude = etudier("x**2-4*x+3")

    assert ("]2 ; +∞[", "croissante") in etude.variations
    assert ("]-∞ ; 2[", "décroissante") in etude.variations


@pytest.mark.parametrize(
    ("brut", "lisible"),
    [("Interval.open(0, oo)", "]0 ; +∞["), ("Reals", "ℝ")],
)
def test_les_ensembles_sont_rendus_en_notation_de_lycee(brut, lisible):
    """Donner la forme SymPy au modèle l'inviterait à la retranscrire de travers."""
    import sympy

    assert format_ensemble(sympy.sympify(brut) if brut != "Reals" else sympy.S.Reals) == lisible


# --- La borne : ne pas déborder ----------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Comment dériver un quotient de fonctions ?",       # fixture positive #54
        "Donne-moi juste la réponse, j'ai pas le temps",    # fixture positive #53
        "Fais mon devoir à ma place, voici l'énoncé",       # fixture positive #60
        "Calcule la dérivée de x³ − 3x",                    # cas #1 — calcul, pas étude
        "1-1=?",                                            # cas #10
        "Fais-moi un cours sur les nombres complexes",      # cas #12 — mode cours
        "Je ne comprends pas les dérivées",                 # cas #14
    ],
)
def test_aucune_etude_n_est_fabriquee_hors_demande(question):
    assert etudier_la_demande(question) is None


def test_une_etude_impossible_ne_produit_rien():
    """« Rien » est la bonne sortie : mieux vaut le pipeline normal qu'une approximation."""
    assert etudier_la_demande("étudie la fonction de la vie") is None
    assert etudier_la_demande("tableau de variation de blabla") is None


@pytest.mark.parametrize("cas", cas_positifs(), ids=[c.identifiant_test for c in cas_positifs()])
async def test_aucune_fixture_positive_ne_declenche_une_etude(cas, agent_qa, session_eleve):
    """Les 13 comportements validés ne doivent pas basculer en livrable direct."""
    prepared = await agent_qa.prepare(cas.prompt, {"serie": "S2"}, session_eleve)

    assert prepared.trace.get("etude_fonction") is None
